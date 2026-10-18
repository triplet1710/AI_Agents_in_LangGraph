# Bài 9 — Production: quan sát, kiểm thử, triển khai

⏱️ ~3 ngày · 🎬 Không có video — bài ngoài khóa, để dự án thành sản phẩm thật

## 🎯 Mục tiêu
- Trace & debug với LangSmith, chạy LangGraph Studio.
- Viết test cho node/graph, đánh giá (eval) chất lượng agent.
- Xử lý lỗi, giới hạn chi phí.
- Deploy lên Hugging Face Spaces (sân nhà của mày).

---

## 📖 Lý thuyết

### 9.1 Observability — LangSmith
Chỉ cần biến môi trường, không sửa code:
```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=my-project
```
Mỗi lần chạy → một trace: cây node, input/output từng LLM call, token, latency, lỗi. Gắn thêm thông tin:
```python
graph.invoke(inputs, {"configurable": {...}, "tags": ["v2"], "metadata": {"user": "tin"}})
```

### 9.2 LangGraph Studio
```powershell
pip install "langgraph-cli[inmem]"
```
`langgraph.json` ở gốc dự án:
```json
{
  "dependencies": ["."],
  "graphs": { "agent": "./src/jobpilot/graph.py:graph" },
  "env": ".env"
}
```
```powershell
langgraph dev
```
→ mở Studio trên trình duyệt: nhìn graph chạy, xem/sửa state, interrupt, time travel bằng UI.
(Graph export ra cho Studio **không cần** checkpointer — server tự gắn.)

### 9.3 Kiểm thử — 3 tầng

| Tầng | Kiểm cái gì | Cách |
|-----|-----------|-----|
| Unit | Node thuần, hàm route, tool | `pytest`, gọi hàm với state giả |
| Graph | Luồng đi đúng nhánh | Thay LLM bằng fake model trả câu cố định |
| Eval | Chất lượng output thật | Dataset + LLM-as-judge trên LangSmith |

Fake model:
```python
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

fake = GenericFakeChatModel(messages=iter([AIMessage("Plan: ..."), AIMessage("Draft: ...")]))
```
Test route:
```python
def test_should_continue_stops():
    assert should_continue({"revision_number": 3, "max_revisions": 2}) == END
```

Eval agent nên đo:
- **Final answer**: đúng/đủ/có nguồn? (LLM-as-judge theo rubric)
- **Trajectory**: có gọi đúng tool, đúng thứ tự, không thừa?
- **Chi phí & latency** mỗi lần chạy.

### 9.4 Độ bền
- **Retry** node gọi API chập chờn:
  ```python
  from langgraph.types import RetryPolicy
  builder.add_node("search", search_node, retry_policy=RetryPolicy(max_attempts=3))
  ```
- **`recursion_limit`** trong config chặn vòng lặp vô hạn.
- **Timeout** cho tool gọi mạng.
- **Giới hạn chi phí**: đếm token qua `usage_metadata`, dừng khi vượt ngân sách.

### 9.5 Bảo mật
- Không để `.env` lên git/Spaces (dùng *Secrets* của Spaces).
- Nội dung từ web là dữ liệu không tin cậy (bài 4.4).
- Tool có hậu quả → luôn HITL (bài 6).
- Không `eval` input của LLM (bài 2.2).

### 9.6 Các lựa chọn deploy

| Cách | Hợp với |
|-----|--------|
| **HF Spaces + Streamlit/Gradio** | Demo portfolio — miễn phí, mày đã quen |
| FastAPI + Docker (Render, Railway, Fly.io) | Có API cho app khác gọi |
| LangSmith Deployment (LangGraph Platform) | Production có sẵn persistence, queue, Studio |

---

## 🛠️ Thực hành

### Lab 9.1 — Bật tracing, so sánh 2 phiên bản prompt
Chạy Essay Writer với 2 bản `WRITER_PROMPT` (tag `v1`, `v2`) → so sánh trong LangSmith.

### Lab 9.2 — `langgraph dev`
Chuyển Essay Writer thành `src/essay/graph.py` (biến `graph` ở module level), tạo `langgraph.json`, chạy Studio, thử sửa `plan` giữa chừng bằng UI.

### Lab 9.3 — pytest
Viết ≥ 5 test: route function, một node với fake model, một tool, toàn graph với fake model đi đúng số vòng revision.

### Lab 9.4 — Deploy HF Spaces
1. Tạo Space (SDK: Streamlit hoặc Docker).
2. Đẩy `app.py` + `requirements.txt` + code.
3. Thêm key vào *Settings → Secrets*.
4. Lưu ý: dữ liệu ghi đĩa trên Space free có thể mất khi restart → chấp nhận cho demo, hoặc dùng Postgres ngoài (Neon/Supabase free).

---

## 🏋️ Bài tập

- 🟢 **9.1** Tạo dataset 5 input trên LangSmith cho agent bài 3, chạy eval "câu trả lời có trích nguồn không" bằng LLM-as-judge.
- 🟡 **9.2** Thêm budget guard: dừng graph và báo khi tổng token của thread > ngưỡng.
- 🔴 **9.3** Bọc graph bằng FastAPI: `POST /threads/{id}/runs` (stream SSE), `POST /threads/{id}/resume` (cho HITL). Dockerize.

---

## ❓ Quiz tự kiểm tra

1. Vì sao unit test node dễ hơn test cả agent?
2. Trajectory eval khác final-answer eval thế nào?
3. Deploy lên Space free dùng `SqliteSaver` có vấn đề gì?
4. Liệt kê 3 biện pháp chống agent "đốt tiền".

<details><summary>Đáp án</summary>

1. Node là hàm thuần nhận state trả dict → input/output xác định, không cần gọi LLM thật.
2. Final-answer chỉ chấm kết quả cuối; trajectory chấm cả quá trình (tool nào, thứ tự, số bước) — bắt được trường hợp đúng nhờ may mắn hoặc tốn bước thừa.
3. Ổ đĩa không bền → mất lịch sử khi Space restart; nhiều replica/instance không dùng chung file.
4. `recursion_limit`; `max_revisions`/bộ đếm vòng; budget token; model rẻ cho bước đơn giản; cache kết quả search; giới hạn `max_results`.
</details>

---

## 🚀 Milestone dự án: **M7 — Về đích**
Deploy + README + demo GIF + eval. Xem [PROJECT.md](../project/PROJECT.md).
