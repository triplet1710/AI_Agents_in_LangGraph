# Bài 5 — Persistence & Streaming

⏱️ ~3 ngày · 🎬 Video: *Persistence and Streaming*

## 🎯 Mục tiêu
- Hiểu checkpointer lưu cái gì, khi nào, theo khóa gì.
- Phân biệt short-term memory (thread) và long-term memory (store).
- Thành thạo 4 kiểu stream và chọn đúng cho UI.

---

## 📖 Lý thuyết

### 5.1 Checkpointer
Compile graph với checkpointer → sau **mỗi super-step**, LangGraph lưu một *snapshot* state.

```python
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "user-42"}}
graph.invoke({"messages": [...]}, config)
```

```
thread "user-42":
  checkpoint 0 ─ input
  checkpoint 1 ─ sau node llm
  checkpoint 2 ─ sau node action
  checkpoint 3 ─ sau node llm (END)
  ── lượt hỏi tiếp theo nối tiếp từ checkpoint 3 ──
```

Checkpointer mở khóa: **(1)** nhớ hội thoại, **(2)** human-in-the-loop, **(3)** time travel, **(4)** chịu lỗi (crash → chạy tiếp từ checkpoint cuối).

| Checkpointer | Package | Dùng khi |
|-------------|--------|---------|
| `InMemorySaver` | `langgraph` | Học, test — mất khi tắt process |
| `SqliteSaver` / `AsyncSqliteSaver` | `langgraph-checkpoint-sqlite` | App cá nhân, demo |
| `PostgresSaver` / `AsyncPostgresSaver` | `langgraph-checkpoint-postgres` | Production |

### 5.2 `StateSnapshot`
`graph.get_state(config)` trả về:

| Field | Ý nghĩa |
|------|--------|
| `values` | State tại checkpoint |
| `next` | Tuple node sẽ chạy tiếp (rỗng = đã xong) — **cực quan trọng ở bài 6** |
| `config` | Có `thread_id` + `checkpoint_id` |
| `parent_config` | Checkpoint trước đó |
| `metadata` | `step`, `source`, node nào ghi |
| `tasks` | Task đang chờ, kể cả interrupt |

`graph.get_state_history(config)` → duyệt toàn bộ snapshot, mới nhất trước.

### 5.3 Short-term vs long-term memory

| | Short-term | Long-term |
|--|-----------|-----------|
| Phạm vi | 1 thread | Mọi thread của 1 user |
| Cơ chế | Checkpointer | `Store` (bài 8) |
| Ví dụ | "Còn ở LA thì sao?" | "User thích trả lời ngắn, đang tìm việc Python" |

### 5.4 Streaming

| `stream_mode` | Nhận được | Dùng cho |
|--------------|----------|---------|
| `"values"` | **Toàn bộ state** sau mỗi step | Debug, UI hiển thị trạng thái đầy đủ |
| `"updates"` | `{node_name: update}` sau mỗi step | Hiển thị tiến trình "đang search…" |
| `"messages"` | `(message_chunk, metadata)` theo **token** | Hiệu ứng gõ chữ như ChatGPT |
| `"custom"` | Bất cứ gì node gửi qua `get_stream_writer()` | Progress tùy biến trong tool/node |

Có thể kết hợp: `stream_mode=["updates", "messages"]` → nhận tuple `(mode, chunk)`.
Bản async: `astream(...)`.

### 5.5 Vấn đề context window
Thread dài → messages phình → chậm, tốn tiền, vượt context. Giải pháp:
- **Cắt**: chỉ gửi N message cuối cho LLM (`trim_messages` trong `langchain_core.messages`).
- **Tóm tắt**: node `summarize` gộp message cũ thành 1 bản tóm tắt, xóa bản gốc bằng `RemoveMessage`.

---

## 🛠️ Thực hành

### Lab 5.1 — Thêm memory cho agent (bám khóa học)
Dùng agent Lab 3.2, chỉ đổi dòng compile:
```python
from langgraph.checkpoint.memory import InMemorySaver

graph = builder.compile(checkpointer=InMemorySaver())

def ask(text, thread_id):
    config = {"configurable": {"thread_id": thread_id}}
    for event in graph.stream({"messages": [HumanMessage(text)]}, config, stream_mode="updates"):
        for node, update in event.items():
            print(f"[{node}]", update["messages"][-1].content[:200] or update["messages"][-1].tool_calls)

ask("What is the weather in sf?", "1")
ask("What about in la?", "1")          # hiểu "what about" nhờ memory
ask("Which one is warmer?", "1")
ask("Which one is warmer?", "2")       # thread mới → không biết gì
```

### Lab 5.2 — Persistence ra file SQLite
```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
graph = builder.compile(checkpointer=SqliteSaver(conn))
ask("My name is Tin. Remember it.", "persist-1")
```
👉 **Restart kernel**, chạy lại setup, rồi `ask("What's my name?", "persist-1")`. Nó vẫn nhớ.

### Lab 5.3 — Soi checkpoint
```python
config = {"configurable": {"thread_id": "1"}}
snap = graph.get_state(config)
print(snap.next, len(snap.values["messages"]), snap.metadata)

for s in graph.get_state_history(config):
    print(s.metadata["step"], s.next, len(s.values.get("messages", [])), s.config["configurable"]["checkpoint_id"])
```

### Lab 5.4 — Stream token
```python
config = {"configurable": {"thread_id": "4"}}
for chunk, meta in graph.stream(
    {"messages": [HumanMessage("What is the weather in Hanoi?")]}, config, stream_mode="messages"
):
    if meta["langgraph_node"] == "llm" and chunk.content:
        print(chunk.content, end="", flush=True)
```
> Khóa học dùng `astream_events(..., version="v1")` — cách cũ, giờ dùng `stream_mode="messages"`.
> Một số provider (vd Anthropic) trả `content` dạng list block → lấy phần text trong block.

### Lab 5.5 — Async + AsyncSqliteSaver
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async with AsyncSqliteSaver.from_conn_string("checkpoints_async.sqlite") as memory:
    agraph = builder.compile(checkpointer=memory)
    config = {"configurable": {"thread_id": "a1"}}
    async for chunk, meta in agraph.astream(
        {"messages": [HumanMessage("Weather in Da Nang?")]}, config, stream_mode="messages"
    ):
        if chunk.content and meta["langgraph_node"] == "llm":
            print(chunk.content, end="", flush=True)
```
(Notebook hỗ trợ `await` trực tiếp; trong file `.py` bọc trong `asyncio.run(main())`.)

---

## 🏋️ Bài tập

- 🟢 **5.1** Viết CLI chat: `python chat.py --thread abc`. Gõ `/new` tạo thread mới, `/history` in số message, `/quit` thoát. Dùng `SqliteSaver`.
- 🟢 **5.2** Chạy cùng câu hỏi với `stream_mode` = `"values"`, `"updates"`, `["updates", "messages"]`. Viết 2–3 câu nhận xét mỗi mode hợp với UI nào.
- 🟡 **5.3** Trong tool search, dùng `get_stream_writer()` gửi tiến trình:
  ```python
  from langgraph.config import get_stream_writer
  writer = get_stream_writer()
  writer({"status": f"Đang tìm: {query}"})
  ```
  Stream với `stream_mode=["custom", "messages"]` và in status riêng.
- 🟡 **5.4** Thêm node `summarize`: khi `len(messages) > 10`, tóm tắt các message cũ vào field `summary`, xóa chúng bằng `RemoveMessage(id=...)`, giữ 4 message cuối. Đưa `summary` vào system prompt.
- 🔴 **5.5** UI Streamlit tối giản: ô chat, token stream, sidebar chọn/tạo thread (dữ liệu lấy từ SQLite). Gợi ý: `st.write_stream(generator)`.

---

## ❓ Quiz tự kiểm tra

1. Checkpoint được lưu khi nào?
2. Không truyền `thread_id` khi graph có checkpointer thì sao?
3. `snap.next == ()` nghĩa là gì?
4. Muốn hiện "Đang tìm kiếm…" rồi mới stream câu trả lời — dùng mode nào?
5. Vì sao cần tóm tắt/cắt messages dù đã có persistence?

<details><summary>Đáp án</summary>

1. Sau mỗi super-step (và cả input ban đầu).
2. Báo lỗi — checkpointer cần `thread_id` để biết lưu vào đâu.
3. Graph đã chạy xong ở checkpoint đó, không còn node nào chờ.
4. `["updates", "messages"]` (hoặc thêm `"custom"`): `updates` báo node tools đang chạy, `messages` stream token.
5. Persistence chỉ lưu; mỗi lần gọi LLM vẫn gửi toàn bộ messages → tốn token, chậm, có thể vượt context window.
</details>

---

## 🚀 Milestone dự án: **M3**
Dự án nhớ hội thoại qua `SqliteSaver`, có UI Streamlit stream token. Xem [PROJECT.md](../project/PROJECT.md).
