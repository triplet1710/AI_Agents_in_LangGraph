# Bài 3 — Các thành phần của LangGraph

⏱️ ~3 ngày · 🎬 Video: *LangGraph Components*

## 🎯 Mục tiêu
- Nắm chắc 4 khối: **State, Node, Edge, Reducer** + luồng message khi gọi tool.
- Viết lại agent bài 2 bằng LangGraph theo 3 mức: tự viết hết → dùng prebuilt → một dòng `create_agent`.
- Biết khi nào dùng mức nào.

---

## 📖 Lý thuyết

### 3.1 State
State là "bộ nhớ làm việc" của graph. Khai báo bằng `TypedDict` (phổ biến nhất), `pydantic.BaseModel` (có validate) hoặc `dataclass`.

```python
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]   # channel có reducer
    turns: int                                            # channel ghi đè
```
Mỗi key là một **channel**. `Annotated[type, reducer]` gắn reducer cho channel.

### 3.2 Reducer — 3 loại hay gặp

| Reducer | Hành vi | Dùng khi |
|--------|--------|---------|
| *(không có)* | Ghi đè | Giá trị đơn: `plan`, `draft`, `count` |
| `operator.add` | Nối list | Log, list kết quả |
| `add_messages` | Nối list **+ thay thế message trùng `id`** + xóa bằng `RemoveMessage` | **Luôn dùng cho messages** |

`MessagesState` = `TypedDict` có sẵn `messages: Annotated[list[AnyMessage], add_messages]`. Kế thừa nó để thêm field:
```python
class MyState(MessagesState):
    user_name: str
```

> ⚠️ Khóa học dùng `operator.add` cho messages, sang bài 6 lại phải tự viết reducer thay thế theo id. `add_messages` làm sẵn việc đó → dùng nó từ đầu.

### 3.3 Node
Bất kỳ hàm Python nào: `(state) -> dict update`. Có thể là gọi LLM, gọi tool, code thuần, hay cả một graph khác (subgraph — bài 8). Có thể là `async def`.

### 3.4 Edge
- `add_edge("a", "b")` — luôn đi a → b.
- `add_edge(START, "a")` — điểm vào.
- `add_conditional_edges("a", route_fn, path_map)` — `route_fn(state)` trả về tên node / `END` (hoặc key để tra `path_map`).
- Nhiều edge từ 1 node → các node đích chạy **song song** trong super-step kế.

### 3.5 Luồng message khi gọi tool ⭐

```
HumanMessage("Thời tiết SF?")
      │
      ▼  model.bind_tools(tools).invoke(messages)
AIMessage(content="", tool_calls=[{"name":"tavily_search","args":{"query":"weather SF"},"id":"call_1"}])
      │
      ▼  code chạy tool
ToolMessage(content="...kết quả...", tool_call_id="call_1", name="tavily_search")
      │
      ▼  gọi model lần nữa với toàn bộ messages
AIMessage(content="Ở SF hiện 18°C...")   ← không còn tool_calls → kết thúc
```

`model.bind_tools(tools)` chuyển docstring + type hints của tool thành JSON schema (chính là `tools_schema` mày tự viết tay ở Lab 2.4).

### 3.6 Compile
`builder.compile(checkpointer=..., interrupt_before=[...], store=...)` → kiểm tra graph hợp lệ (node mồ côi, edge sai tên) và trả về `CompiledStateGraph` — một **Runnable**: có `invoke`, `stream`, `ainvoke`, `astream`, `batch`.

### 3.7 Ba mức trừu tượng

| Mức | Code | Khi nào |
|----|------|--------|
| 1. Tự viết node | `StateGraph` + node `llm` + node `action` | Học bản chất; cần logic tool tùy biến |
| 2. Prebuilt | `ToolNode` + `tools_condition` | Đa số agent tùy biến luồng |
| 3. One-liner | `create_agent(model, tools, system_prompt=...)` | Agent ReAct chuẩn, không cần sửa luồng |

---

## 🛠️ Thực hành

### Lab 3.1 — Agent class của khóa học (bản cập nhật)

```python
import os, operator
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END

load_dotenv()
tool = TavilySearch(max_results=4)
print(tool.name)           # "tavily_search"

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

class Agent:
    def __init__(self, model, tools, system=""):
        self.system = system
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_llm)
        graph.add_node("action", self.take_action)
        graph.add_conditional_edges("llm", self.exists_action, {True: "action", False: END})
        graph.add_edge("action", "llm")
        graph.add_edge(START, "llm")
        self.graph = graph.compile()
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools)

    def exists_action(self, state: AgentState) -> bool:
        return len(state["messages"][-1].tool_calls) > 0

    def call_llm(self, state: AgentState):
        messages = state["messages"]
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        return {"messages": [self.model.invoke(messages)]}

    def take_action(self, state: AgentState):
        results = []
        for t in state["messages"][-1].tool_calls:
            print(f"Calling: {t}")
            if t["name"] not in self.tools:
                result = "bad tool name, retry"
            else:
                result = self.tools[t["name"]].invoke(t["args"])
            results.append(ToolMessage(tool_call_id=t["id"], name=t["name"], content=str(result)))
        print("Back to the model!")
        return {"messages": results}

prompt = """You are a smart research assistant. Use the search engine to look up information. \
You are allowed to make multiple calls (either together or in sequence). \
Only look up information when you are sure of what you want. \
If you need to look up some information before asking a follow up question, you are allowed to do that!"""

model = init_chat_model("ollama:qwen3:8b", temperature=0, reasoning=False, num_ctx=8192)
abot = Agent(model, [tool], system=prompt)

result = abot.graph.invoke({"messages": [HumanMessage("What is the weather in sf?")]})
print(result["messages"][-1].content)
```

Thử 3 câu hỏi của khóa học, **đọc kỹ `result["messages"]`** sau mỗi câu:
1. `"What is the weather in sf?"` → 1 tool call
2. `"What is the weather in SF and LA?"` → **2 tool call song song** trong 1 `AIMessage`
3. `"Who won the super bowl in 2024? In what state is the winning team headquarters located? What is the GDP of that state? Answer each question."` → tool call **tuần tự** (câu sau phụ thuộc câu trước)

### Lab 3.2 — Cùng agent, dùng prebuilt

```python
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

tools = [tool]
model_with_tools = model.bind_tools(tools)

def call_model(state: MessagesState):
    return {"messages": [model_with_tools.invoke([SystemMessage(prompt)] + state["messages"])]}

builder = StateGraph(MessagesState)
builder.add_node("llm", call_model)
builder.add_node("tools", ToolNode(tools))        # tên node phải là "tools" để khớp tools_condition
builder.add_edge(START, "llm")
builder.add_conditional_edges("llm", tools_condition)   # → "tools" hoặc END
builder.add_edge("tools", "llm")
graph = builder.compile()
```

### Lab 3.3 — Một dòng

```python
from langchain.agents import create_agent

agent = create_agent(model, tools=[tool], system_prompt=prompt)   # nhận cả object model lẫn chuỗi "provider:model"
agent.invoke({"messages": [HumanMessage("What is the weather in Hanoi?")]})
```
👉 Vẽ graph của cả 3 bản (`.get_graph().draw_mermaid()`) và so sánh.

### Lab 3.4 — Tự viết tool
```python
from langchain_core.tools import tool

@tool
def vnd_to_usd(amount_vnd: float) -> str:
    """Convert Vietnamese Dong to US Dollar using a fixed rate."""
    return f"{amount_vnd / 25_000:.2f} USD"

print(vnd_to_usd.name, vnd_to_usd.args)   # schema sinh từ type hints + docstring
```
👉 Docstring **chính là prompt** mô tả tool cho LLM. Viết tệ → LLM gọi sai.

---

## 🏋️ Bài tập

- 🟢 **3.1** Thêm `vnd_to_usd` vào agent Lab 3.2. Hỏi: *"Giá iPhone mới nhất ở Việt Nam là bao nhiêu, đổi ra USD?"*
- 🟢 **3.2** Đổi `operator.add` → `add_messages` trong Lab 3.1. Sau đó trả về một `AIMessage` có cùng `id` với message cuối → quan sát nó **thay thế** thay vì nối thêm.
- 🟡 **3.3** Thêm field `turns: int` vào state. Nếu LLM gọi tool quá 3 lượt → route sang node `give_up` trả lời "Câu hỏi quá phức tạp".
- 🟡 **3.4** Tool lỗi thì sao? Viết tool cố tình `raise ValueError`. So sánh hành vi giữa Lab 3.1 (tự viết) và `ToolNode` (xem `handle_tool_errors`).
- 🔴 **3.5** Viết node `guardrail` chạy **trước** `llm`: nếu câu hỏi chứa chủ đề bị cấm (tự định nghĩa) thì trả lời từ chối và đi thẳng tới `END`, không gọi LLM chính.

---

## ❓ Quiz tự kiểm tra

1. Vì sao `AIMessage` có `tool_calls` lại thường có `content` rỗng?
2. Thiếu `ToolMessage` cho một `tool_call_id` rồi gọi LLM tiếp thì sao?
3. `tools_condition` route dựa vào cái gì?
4. Khác biệt giữa `operator.add` và `add_messages`?
5. Khi nào chọn `create_agent` thay vì tự build graph?

<details><summary>Đáp án</summary>

1. Model quyết định gọi tool thay vì trả lời; nội dung nằm ở `tool_calls`.
2. Hầu hết provider báo lỗi: mỗi tool call phải có tool result tương ứng ngay sau.
3. Message cuối có `tool_calls` không rỗng → `"tools"`, ngược lại → `END`.
4. `operator.add` chỉ nối; `add_messages` nối + thay thế theo `id` + xóa bằng `RemoveMessage` + nhận cả dict/tuple và tự chuyển thành message.
5. Khi luồng đúng là ReAct chuẩn (LLM ↔ tools). Cần node khác (plan, review, route, HITL tùy biến…) thì tự build.
</details>

---

## 🚀 Milestone dự án: **M1**
Agent CLI đầu tiên của dự án theo kiểu Lab 3.2, với các tool đã thiết kế ở bài 2 (được phép dùng dữ liệu giả). Xem Definition of Done trong [PROJECT.md](../project/PROJECT.md).
