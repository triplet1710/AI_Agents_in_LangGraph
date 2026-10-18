# Bài 0 — Cài đặt môi trường

⏱️ ~1–2 giờ · 🎯 Chạy được `practice/check_setup.py` toàn ✅

---

## 1. Học 0 đồng — thứ cần có

| Dịch vụ | Dùng ở đâu | Chi phí |
|--------|-----------|--------|
| **Ollama + `qwen3:8b`** (đã có trên máy) | Mọi bài | Miễn phí, chạy local trên RTX 4060 8GB. Hỗ trợ **tool calling** (cả gọi song song) + **structured output** — đủ cho toàn bộ khóa. |
| **Tavily** | Bài 3, 4, 7, dự án | Free tier ~1000 credit/tháng, **không cần thẻ**. Không muốn đăng ký → dùng DuckDuckGo (mục 1.3). |
| **LangSmith** | Khuyến khích từ bài 3, bắt buộc bài 9 | Gói Developer free, **không cần thẻ**. |

### 1.1 Dòng khởi tạo model chuẩn (dùng trong mọi lab)
```python
from langchain.chat_models import init_chat_model
model = init_chat_model("ollama:qwen3:8b", temperature=0, reasoning=False, num_ctx=8192)
```
| Tham số | Vì sao |
|--------|-------|
| `reasoning=False` | qwen3 mặc định bật "thinking": nghĩ rất dài trước khi trả lời → chậm, output lẫn suy nghĩ. Tắt đi cho lab. (Muốn xem nó nghĩ: `reasoning=True`, phần suy nghĩ nằm riêng trong `additional_kwargs`.) |
| `num_ctx=8192` | Ollama mặc định context nhỏ → kết quả search dài bị **cắt mất mà không báo lỗi**. 8192 vẫn vừa 8GB VRAM. Đừng tăng quá 16384 kẻo tràn sang RAM, chậm hẳn. |
| `temperature=0` | Model nhỏ ổn định hơn nhiều khi tool calling. |

Bài 2 dùng OpenAI SDK trỏ vào Ollama (`base_url="http://localhost:11434/v1"`), tắt thinking bằng `reasoning_effort="none"` — code có sẵn trong bài.

### 1.2 Model local khác lúc chạy khóa học thế nào
Model 8B yếu hơn GPT-4o. Gặp mấy chuyện này thì là **bình thường**, không phải mày code sai:
- Thỉnh thoảng không gọi tool khi cần, hoặc gọi sai tham số → viết docstring tool rõ hơn, system prompt cụ thể hơn. *(Đây lại là kỹ năng rất đáng luyện.)*
- Structured output đôi khi hỏng → bọc `try/except`, retry 1 lần.
- Câu hỏi nhiều bước (Super Bowl → bang → GDP ở bài 3) có thể sai một bước → so sánh với kết quả trong video.
- Bài 7 (Essay Writer) chạy vài phút → giữ `max_results=2`, `max_revisions=2`.

Tip: lúc học, mở cửa sổ khác chạy `ollama ps` để chắc model đang chạy **100% GPU**.

### 1.3 Không dùng Tavily: DuckDuckGo thay thế
```python
from ddgs import DDGS
from langchain_core.tools import tool

@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date information. Returns titles, URLs and snippets."""
    results = DDGS().text(query, max_results=4)
    return "\n\n".join(f"{r['title']}\n{r['href']}\n{r['body']}" for r in results)
```
Dùng `web_search` ở mọi chỗ trong lab ghi `TavilySearch(...)`. Snippet ngắn hơn Tavily nhiều — chính bài 4 sẽ giải thích vì sao. Gặp lỗi rate limit thì chờ vài phút.

### 1.4 Khi nào có tiền / muốn so sánh
Chỉ đổi một dòng model (`init_chat_model("google_genai:gemini-2.5-flash")` — Gemini có free tier qua Google AI Studio, không cần thẻ). Toàn bộ code LangGraph giữ nguyên — đó chính là cái hay của việc tách model khỏi graph.

## 2. Tạo môi trường Python

> Máy mày đang có Python 3.14. Nếu cài package bị lỗi wheel, dùng 3.12 hoặc 3.13 qua `uv` (cách 1) cho lành.

**Cách 1 — `uv` (khuyên dùng, nhanh hơn pip nhiều):**
```powershell
winget install astral-sh.uv          # hoặc: pip install uv
uv venv --python 3.12
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

**Cách 2 — venv truyền thống:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Nếu PowerShell chặn script activate: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## 3. Cấu hình key

```powershell
Copy-Item .env.example .env
code .env      # điền key, chọn MODEL
python practice/check_setup.py
```

Trong notebook, luôn mở đầu bằng:
```python
from dotenv import load_dotenv
load_dotenv()
```

Trong VS Code: mở file `.ipynb` → *Select Kernel* → chọn `.venv`.

## 4. ⚠️ Khóa học quay bằng phiên bản cũ — bảng đối chiếu

Video khóa học dùng LangGraph 0.0.x (2024). Hiện tại là **LangGraph 1.x**. Logic giống hệt, chỉ khác vài import/API. Giáo trình này viết theo bản mới; khi xem video thấy khác thì tra bảng này:

| Trong video | Bản hiện tại |
|------------|--------------|
| `from langchain_community.tools.tavily_search import TavilySearchResults` | `from langchain_tavily import TavilySearch` |
| `from langchain_openai import ChatOpenAI` | Vẫn dùng được. Hoặc trung lập provider: `from langchain.chat_models import init_chat_model` |
| `SqliteSaver.from_conn_string(":memory:")` dùng thẳng | Giờ là **context manager** → `with SqliteSaver.from_conn_string(...) as memory:` hoặc `SqliteSaver(sqlite3.connect(path, check_same_thread=False))` |
| `from langgraph.checkpoint.memory import MemorySaver` | `InMemorySaver` (tên `MemorySaver` vẫn còn là alias) |
| `graph.astream_events(..., version="v1")` để stream token | `graph.stream(..., stream_mode="messages")` |
| `graph.set_entry_point("llm")` | Vẫn chạy; cách mới: `graph.add_edge(START, "llm")` |
| Chỉ có `interrupt_before=[...]` | Vẫn có, nhưng cách chính giờ là `interrupt()` + `Command(resume=...)` |
| `from duckduckgo_search import DDGS` | `from ddgs import DDGS` (package đổi tên) |
| `from langgraph.prebuilt import create_react_agent` | `from langchain.agents import create_agent` |
| Model `gpt-3.5-turbo`, `gpt-4o` | Dùng model rẻ & mới hơn, set qua biến `MODEL` |

## 5. Quy ước thư mục practice

```
practice/
├── lesson01/  lab_1_1.ipynb, lab_1_2.ipynb, ex_1_1.ipynb ...
├── lesson02/
└── ...
```
Đặt tên `lab_X_Y` cho lab, `ex_X_Y` cho bài tập → tao review dễ.

## ✅ Checklist

- [ ] `ollama list` có `qwen3:8b`; có key Tavily (hoặc dùng DuckDuckGo) (+ LangSmith)
- [ ] Tạo `.venv`, cài `requirements.txt`
- [ ] `python practice/check_setup.py` toàn ✅
- [ ] Mở được notebook trong VS Code với kernel `.venv`
