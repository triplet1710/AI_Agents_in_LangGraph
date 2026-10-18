# Bài 6 — Human in the Loop

⏱️ ~3 ngày · 🎬 Video: *Human in the Loop*

## 🎯 Mục tiêu
- Dừng graph trước khi hành động, cho người **duyệt / sửa / từ chối**.
- Sửa state giữa chừng bằng `update_state`, hiểu reducer ảnh hưởng thế nào.
- **Time travel**: xem lại, chạy lại, rẽ nhánh từ checkpoint cũ.
- Dùng `interrupt()` + `Command(resume=...)` — cách chuẩn hiện nay.

---

## 📖 Lý thuyết

### 6.1 Vì sao cần người trong vòng lặp
- **An toàn**: hành động không đảo ngược được (gửi email, chuyển tiền, xóa file, nộp đơn).
- **Chất lượng**: người review bản nháp/kế hoạch trước khi tiếp tục.
- **Mơ hồ**: agent cần hỏi lại thông tin.

### 6.2 Hai cách dừng graph

| | Static breakpoint | Dynamic `interrupt()` |
|--|-------------------|----------------------|
| Khai báo | `compile(interrupt_before=["action"])` | Gọi `interrupt(payload)` **bên trong** node/tool |
| Dừng khi | Luôn dừng trước/sau node đó | Chỉ khi code chạy tới dòng đó (có thể kèm `if`) |
| Gửi dữ liệu cho người | Không (tự đọc state) | Có — `payload` hiện trong `result["__interrupt__"]` |
| Tiếp tục | `graph.invoke(None, config)` | `graph.invoke(Command(resume=value), config)` → `value` là giá trị trả về của `interrupt()` |
| Dùng cho | Debug, khóa học | **Production** |

Cả hai đều **bắt buộc có checkpointer**.

### 6.3 ⚠️ Cạm bẫy số 1 của `interrupt()`
Khi resume, **node chạy lại từ đầu**, không phải từ dòng `interrupt`.

```python
def node(state):
    charge_credit_card()            # ❌ chạy 2 lần: trước khi dừng và khi resume!
    ok = interrupt("Xác nhận?")
    if ok: send_email()             # ✅ side effect đặt SAU interrupt
```
Quy tắc: code trước `interrupt()` phải **idempotent** (chạy lại không sao).

### 6.4 Sửa state: `update_state`
```python
graph.update_state(config, {"messages": [edited_msg]}, as_node="llm")
```
- Tạo **checkpoint mới** như thể node `as_node` vừa trả về update đó.
- Update **đi qua reducer**! Với `operator.add`, message sửa sẽ bị *nối thêm* (trùng lặp). Với `add_messages`, message cùng `id` sẽ được *thay thế*. → Đây là lý do khóa học phải tự viết `reduce_messages`.

### 6.5 Time travel

```
checkpoint: c0 ── c1 ── c2 ── c3 ── c4 (hiện tại)
                         │
                         └── c2' ── c3' ...   ← fork: update_state trên config của c2
```
- **Replay**: `graph.invoke(None, old_snapshot.config)` → chạy tiếp từ checkpoint cũ.
- **Fork**: `graph.update_state(old_snapshot.config, {...})` → nhánh mới, rồi `invoke(None, new_config)`.

### 6.6 `Command` — điều hướng từ trong node
```python
from langgraph.types import Command
def review(state) -> Command[Literal["write", "publish"]]:
    decision = interrupt({"draft": state["draft"]})
    if decision == "approve":
        return Command(goto="publish")
    return Command(goto="write", update={"feedback": decision})
```
`Command` vừa cập nhật state vừa chọn node tiếp theo — thay cho conditional edge.

---

## 🛠️ Thực hành

### Lab 6.1 — Duyệt trước khi chạy tool (bám khóa học)
Dùng agent Lab 3.2 (state `MessagesState`):
```python
from langgraph.checkpoint.memory import InMemorySaver

graph = builder.compile(checkpointer=InMemorySaver(), interrupt_before=["tools"])
config = {"configurable": {"thread_id": "hitl-1"}}

for e in graph.stream({"messages": [HumanMessage("Whats the weather in SF?")]}, config, stream_mode="values"):
    e["messages"][-1].pretty_print()

snap = graph.get_state(config)
print(snap.next)                               # ('tools',) → đang dừng
print(snap.values["messages"][-1].tool_calls)  # agent định gọi gì

for e in graph.stream(None, config, stream_mode="values"):   # None = tiếp tục
    e["messages"][-1].pretty_print()
```

Vòng duyệt:
```python
config = {"configurable": {"thread_id": "hitl-2"}}
graph.invoke({"messages": [HumanMessage("Whats the weather in LA?")]}, config)
while graph.get_state(config).next:
    print(graph.get_state(config).values["messages"][-1].tool_calls)
    if input("proceed? (y/n) ") != "y":
        print("aborting"); break
    graph.invoke(None, config)
```

### Lab 6.2 — Sửa tool call trước khi chạy
```python
config = {"configurable": {"thread_id": "hitl-3"}}
graph.invoke({"messages": [HumanMessage("Whats the weather in LA?")]}, config)

snap = graph.get_state(config)
last = snap.values["messages"][-1]
last.tool_calls[0]["args"]["query"] = "current weather in Hanoi"   # đổi ý!
graph.update_state(config, {"messages": [last]})                    # cùng id → thay thế

print(graph.get_state(config).values["messages"][-1].tool_calls)
graph.invoke(None, config)
print(graph.get_state(config).values["messages"][-1].content)       # trả lời về Hanoi
```
👉 Thử lại với state dùng `operator.add` → đếm số message, thấy bị nhân đôi.

### Lab 6.3 — Time travel
```python
states = list(graph.get_state_history(config))
for i, s in enumerate(states):
    print(i, s.metadata["step"], s.next, len(s.values.get("messages", [])))

to_replay = next(s for s in states if s.next == ("tools",))   # điểm ngay trước khi chạy tool
graph.invoke(None, to_replay.config)                          # replay

# Fork: sửa tool call ở checkpoint cũ thành query khác
msg = to_replay.values["messages"][-1]
msg.tool_calls[0]["args"]["query"] = "current weather in Tokyo"
branch_config = graph.update_state(to_replay.config, {"messages": [msg]})
graph.invoke(None, branch_config)
```

### Lab 6.4 — `interrupt()` trong tool nguy hiểm
```python
from langchain_core.tools import tool
from langgraph.types import interrupt, Command

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    decision = interrupt({"action": "send_email", "to": to, "subject": subject, "body": body})
    if decision["type"] == "approve":
        return f"Email sent to {to}."
    if decision["type"] == "edit":
        return f"Email sent to {to} with edited body: {decision['body']}"
    return "User rejected sending this email. Do not retry."

tools = [send_email]
# ... build graph như Lab 3.2 với tools này, compile(checkpointer=InMemorySaver()) — KHÔNG cần interrupt_before

config = {"configurable": {"thread_id": "email-1"}}
result = graph.invoke({"messages": [HumanMessage("Email boss@x.com xin nghỉ thứ 6")]}, config)
print(result["__interrupt__"][0].value)        # payload để hiện cho người

result = graph.invoke(Command(resume={"type": "approve"}), config)
print(result["messages"][-1].content)
```

> 💡 `create_agent` (LangChain 1.x) có sẵn `HumanInTheLoopMiddleware` làm đúng việc này cho từng tool. Biết để dùng, nhưng tự làm một lần để hiểu.

---

## 🏋️ Bài tập

- 🟢 **6.1** Lab 6.4: thêm nhánh `"edit"` thật sự — cho người sửa `subject`/`body` trong terminal rồi resume.
- 🟢 **6.2** Viết tool `ask_human(question: str) -> str` dùng `interrupt` để agent **hỏi lại** khi thiếu thông tin. Test: *"Đặt bàn nhà hàng cho tao"*.
- 🟡 **6.3** Chứng minh cạm bẫy 6.3: đặt `print("side effect!")` trước `interrupt` trong một node, đếm số lần in ra sau khi resume.
- 🟡 **6.4** Viết lại Lab 6.1 bằng `interrupt()` trong một node `review_tool_calls` đứng giữa `llm` và `tools` với `Command(goto=...)`: approve → `tools`; reject → quay về `llm` kèm `ToolMessage` báo bị từ chối (nhớ: mỗi tool_call cần một ToolMessage!).
- 🔴 **6.5** CLI "Git cho agent": lệnh `/log` in lịch sử checkpoint, `/checkout <i>` quay về checkpoint i, `/edit` sửa message cuối, `/run` chạy tiếp từ đó.

---

## ❓ Quiz tự kiểm tra

1. Vì sao HITL bắt buộc có checkpointer?
2. Khác nhau giữa `graph.invoke(None, config)` và `graph.invoke(Command(resume=x), config)`?
3. Sửa message bằng `update_state` mà bị nhân đôi — nguyên nhân?
4. Node có 2 lời gọi `interrupt()` — resume hoạt động thế nào?
5. Replay khác fork thế nào?

<details><summary>Đáp án</summary>

1. Graph phải dừng hẳn và tiếp tục sau (có thể ở process khác, sau vài giờ) → state phải được lưu.
2. `None`: tiếp tục sau static breakpoint. `Command(resume=x)`: tiếp tục sau `interrupt()` và `x` thành giá trị trả về của `interrupt()`.
3. Reducer `operator.add` nối thêm. Dùng `add_messages` và giữ nguyên `id` để thay thế.
4. Node chạy lại từ đầu; các `interrupt()` được khớp theo **thứ tự** với các giá trị resume đã có; cái đã có giá trị thì trả luôn, cái kế tiếp thì dừng lại hỏi.
5. Replay chạy lại từ checkpoint cũ với state y nguyên. Fork sửa state ở checkpoint cũ trước → tạo nhánh lịch sử mới.
</details>

---

## 🚀 Milestone dự án: **M4**
Mọi hành động "có hậu quả" của dự án phải qua người duyệt. Xem [PROJECT.md](../project/PROJECT.md).
