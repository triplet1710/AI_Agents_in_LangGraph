# Bài 2 — Build agent từ con số 0

⏱️ ~2 ngày · 🎬 Video: *Build an Agent from Scratch*

## 🎯 Mục tiêu
- Tự viết một ReAct agent chỉ bằng Python + SDK của LLM.
- Chỉ ra được chính xác **những phần "đau"** mà framework sẽ giải quyết.
- Bước từ ReAct dạng text → **native tool calling** (cách LangChain/LangGraph làm thật).

> 🔗 Cầu nối: HF Course Unit 1 cũng có "dummy agent library". Bài này đi xa hơn một bước — cuối bài mày sẽ tự "phát minh lại" LangGraph.

---

## 📖 Lý thuyết

### 2.1 ReAct = Reasoning + Acting (Yao et al., 2022)

```
Question ─► Thought ─► Action ─► PAUSE
                                   │  (code của MÀY chạy tool)
              ┌────────────────────┘
              ▼
         Observation ─► Thought ─► ... ─► Answer
```

Ý chính: LLM **không tự chạy tool**. Nó chỉ *viết ra* ý định ("Action: calculate: 4*7"). Code của mày:
1. **Parse** ý định đó,
2. **Chạy** hàm tương ứng,
3. **Đưa kết quả** lại cho LLM dưới dạng `Observation`,
4. **Lặp** tới khi LLM ra `Answer` hoặc hết lượt.

### 2.2 Giải phẫu agent tối giản

| Thành phần | Trong code | Sau này trong LangGraph |
|-----------|-----------|------------------------|
| System prompt mô tả tool + format | chuỗi `prompt` | `bind_tools()` tự sinh schema |
| Bộ nhớ hội thoại | `self.messages` (list) | `state["messages"]` + reducer |
| Gọi LLM | `Agent.__call__` | node `llm` |
| Parse action | regex | `AIMessage.tool_calls` (provider parse sẵn) |
| Chạy tool | `known_actions[action](input)` | node `action` / `ToolNode` |
| Vòng lặp + điều kiện dừng | `while i < max_turns` | conditional edge + `recursion_limit` |

### 2.3 Text-based ReAct vs Native tool calling

| | Text ReAct (bài này) | Native tool calling |
|--|---------------------|---------------------|
| LLM xuất | Văn bản tự do theo format | JSON có cấu trúc trong field `tool_calls` |
| Parse | Regex — dễ vỡ | Provider đảm bảo đúng schema |
| Nhiều tool 1 lúc | Khó | Hỗ trợ **parallel tool calls** |
| Dùng khi | Model không hỗ trợ tools, học bản chất | Gần như mọi lúc trong thực tế |

### 2.4 Những cái "đau" khi tự làm (ghi lại, bài 3 sẽ giải)
1. Parse regex dễ vỡ khi LLM lệch format.
2. Không lưu được trạng thái giữa chừng → crash là mất hết.
3. Không có chỗ "chen" người duyệt trước khi chạy tool.
4. Muốn thêm bước (vd: kiểm duyệt output) → sửa vòng `while`, code rối dần.
5. Không stream, không trace, không debug từng bước.

---

## 🛠️ Thực hành

### Lab 2.1 — Agent class (bám code khóa học)

```python
import os, re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
# Ollama có endpoint tương thích OpenAI → dùng luôn SDK của OpenAI, không tốn đồng nào
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "qwen3:8b"
EXTRA = {"reasoning_effort": "none"}   # tắt chế độ "thinking" của qwen3 (dùng OpenAI thật thì để {})

class Agent:
    def __init__(self, system: str = ""):
        self.system = system
        self.messages = []
        if system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message: str) -> str:
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self) -> str:
        completion = client.chat.completions.create(
            model=MODEL, temperature=0, messages=self.messages, **EXTRA
        )
        return completion.choices[0].message.content
```

### Lab 2.2 — Prompt ReAct + tools

```python
prompt = """
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer.
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

calculate:
e.g. calculate: 4 * 7 / 3
Runs a calculation and returns the number - uses Python so be sure to use floating point syntax if necessary

average_dog_weight:
e.g. average_dog_weight: Collie
returns average weight of a dog when given the breed

Example session:

Question: How much does a Bulldog weigh?
Thought: I should look the dogs weight using average_dog_weight
Action: average_dog_weight: Bulldog
PAUSE

You will be called again with this:

Observation: A Bulldog weights 51 lbs

You then output:

Answer: A bulldog weights 51 lbs
""".strip()

def calculate(what: str):
    return eval(what)        # ⚠️ NGUY HIỂM — bài tập 2.2 sẽ sửa

def average_dog_weight(name: str):
    weights = {"Scottish Terrier": 20, "Border Collie": 37, "Toy Poodle": 7}
    return f"a {name} average weight is {weights.get(name, 50)} lbs"

known_actions = {"calculate": calculate, "average_dog_weight": average_dog_weight}
```

**Chạy tay từng bước** (làm cái này trước — để thấy *mày* chính là vòng lặp):
```python
bot = Agent(prompt)
print(bot("How much does a toy poodle weigh?"))
# Đọc Action trong output, tự gọi hàm, rồi:
print(bot(f"Observation: {average_dog_weight('Toy Poodle')}"))
```

### Lab 2.3 — Tự động hóa vòng lặp

```python
action_re = re.compile(r"^Action: (\w+): (.*)$")

def query(question: str, max_turns: int = 5):
    bot = Agent(prompt)
    next_prompt = question
    for i in range(max_turns):
        result = bot(next_prompt)
        print(f"--- turn {i + 1} ---\n{result}")
        actions = [m for line in result.split("\n") if (m := action_re.match(line))]
        if not actions:
            return result                       # không còn Action → đã có Answer
        action, action_input = actions[0].groups()
        if action not in known_actions:
            raise Exception(f"Unknown action: {action}: {action_input}")
        print(f" -- running {action} {action_input}")
        observation = known_actions[action](action_input)
        next_prompt = f"Observation: {observation}"

query("I have 2 dogs, a border collie and a scottish terrier. What is their combined weight?")
```

### Lab 2.4 — Native tool calling (chưa có framework)

```python
import json

tools_schema = [{
    "type": "function",
    "function": {
        "name": "average_dog_weight",
        "description": "Returns average weight of a dog breed",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Breed name"}},
            "required": ["name"],
        },
    },
}]

messages = [{"role": "user", "content": "Combined weight of a border collie and a toy poodle?"}]
while True:
    msg = client.chat.completions.create(model=MODEL, messages=messages, tools=tools_schema, **EXTRA).choices[0].message
    messages.append(msg)
    if not msg.tool_calls:
        print(msg.content); break
    for tc in msg.tool_calls:                       # có thể nhiều tool call song song!
        args = json.loads(tc.function.arguments)
        result = known_actions[tc.function.name](**args)
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
```
👉 Để ý: model có thể gọi **2 tool trong 1 lượt** (parallel tool calls). Text ReAct không làm được vậy.

---

## 🏋️ Bài tập

- 🟢 **2.1** Thêm tool `get_vnd_rate: USD` trả tỉ giá giả lập. Hỏi: *"Con border collie nặng bao nhiêu kg, và 100 USD là bao nhiêu VND?"* (cập nhật prompt cho đúng format).
- 🟢 **2.2** Thay `eval` bằng máy tính an toàn dùng module `ast` (chỉ cho phép số và `+ - * / ** ()`). Thử tấn công: `calculate: __import__('os').listdir('.')` → phải bị chặn.
- 🟡 **2.3** Khi action không tồn tại, **đừng raise** — trả về `Observation: Error: unknown action X. Available: ...` để LLM tự sửa. Thử bằng cách cố tình đổi tên tool trong prompt.
- 🟡 **2.4** Thêm vào Lab 2.4 giới hạn `max_turns` và in tổng token đã dùng (`completion.usage`).
- 🔴 **2.5 — Tự phát minh LangGraph.** Viết lại Lab 2.3 thành *state machine thuần*:
  ```python
  state = {"messages": [...], "next": "llm"}
  nodes = {"llm": call_llm, "action": run_action}   # mỗi hàm nhận state, trả dict update
  def route(state) -> str: ...                     # trả "action" | "END"
  while state["next"] != "END": ...
  ```
  Sau đó lưu `state` ra file JSON sau **mỗi** bước, và viết hàm `resume(path)` chạy tiếp từ file. Chúc mừng — mày vừa tự làm *node, edge, checkpointer*.

---

## ❓ Quiz tự kiểm tra

1. Trong ReAct, ai thực sự chạy tool: LLM hay code của mày?
2. Vì sao prompt cần "Example session"?
3. `PAUSE` có tác dụng gì?
4. Native tool calling giải quyết vấn đề gì của text ReAct?
5. Trong message `role: "tool"`, `tool_call_id` dùng để làm gì?

<details><summary>Đáp án</summary>

1. Code của mày. LLM chỉ sinh văn bản/JSON mô tả ý định.
2. Few-shot: dạy model đúng format để regex parse được.
3. Báo hiệu LLM dừng sinh tiếp để chờ Observation thật, tránh model *tự bịa* Observation.
4. Parse không ổn định, không gọi song song nhiều tool, phải tự viết mô tả tool trong prompt.
5. Ghép kết quả với đúng lời gọi tool (khi có nhiều tool call song song). Thiếu/sai id → API báo lỗi.
</details>

---

## 🚀 Milestone dự án
Chưa có milestone. Nhưng hãy liệt kê **3 tool** mà agent dự án của mày cần, viết docstring + chữ ký hàm cho từng tool vào `project/ARCHITECTURE.md`.
