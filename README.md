# 🧠 AI Agents in LangGraph — Giáo trình tự học

> Dựa trên khóa **DeepLearning.AI – AI Agents in LangGraph** (Harrison Chase & Rotem Weiss),
> mở rộng thêm phần nâng cao + một dự án cá nhân để làm portfolio.
>
> **Tiền đề:** đã học xong Hugging Face Agents Course (biết ReAct, tools, smolagents, LlamaIndex, LangGraph sơ bộ).
> **Mục tiêu:** hiểu LangGraph *từ bên trong* (state, reducer, checkpoint, interrupt…) và tự build được một agent hoàn chỉnh, có thể deploy.

---

## 🗺️ Lộ trình (≈ 4–5 tuần, 1–1.5h/ngày)

| # | Bài | Nội dung chính | Thời lượng | Milestone dự án |
|---|-----|----------------|-----------|-----------------|
| 0 | [Cài đặt môi trường](lessons/00_setup.md) | venv, API keys, khác biệt API khóa học ↔ LangGraph 1.x | 0.5 ngày | — |
| 1 | [Giới thiệu & cầu nối từ HF Course](lessons/01_intro.md) | Agent là gì, vì sao LangGraph, mô hình thực thi | 1 ngày | M0: chọn đề, vẽ kiến trúc |
| 2 | [Build agent từ con số 0](lessons/02_agent_from_scratch.md) | ReAct thủ công, parse action, vòng lặp | 2 ngày | — |
| 3 | [Các thành phần của LangGraph](lessons/03_langgraph_components.md) | State, reducer, node, edge, tool calling | 3 ngày | M1: agent CLI đầu tiên |
| 4 | [Agentic Search](lessons/04_agentic_search.md) | Tavily, search thường vs agentic search | 2 ngày | M2: tool search thật |
| 5 | [Persistence & Streaming](lessons/05_persistence_streaming.md) | Checkpointer, thread, stream modes | 3 ngày | M3: nhớ hội thoại + UI |
| 6 | [Human in the Loop](lessons/06_human_in_the_loop.md) | Breakpoint, `interrupt()`, sửa state, time travel | 3 ngày | M4: duyệt trước khi hành động |
| 7 | [Essay Writer](lessons/07_essay_writer.md) | Plan → Research → Write → Reflect | 3 ngày | M5: writer có reflection |
| 8 | [Tài nguyên LangChain & Pattern nâng cao](lessons/08_advanced_patterns.md) | Multi-agent, `Send`, subgraph, long-term memory | 4 ngày | M6: multi-agent hoàn chỉnh |
| 9 | [Production](lessons/09_production.md) | LangSmith, test, eval, deploy | 3 ngày | M7: deploy + portfolio |

📌 **Dự án cá nhân:** [project/PROJECT.md](project/PROJECT.md)
📈 **Theo dõi tiến độ:** [PROGRESS.md](PROGRESS.md)

---

## 🔁 Quy trình học mỗi bài (đừng skip bước nào)

1. **Xem video** bài tương ứng trên DeepLearning.AI (bật notebook của họ song song).
2. **Đọc phần Lý thuyết** trong file bài học → ghi lại bằng lời của mình vào mục *Từ điển khái niệm* trong `PROGRESS.md`.
3. **Làm Lab**: tự gõ lại code (KHÔNG copy-paste) vào `practice/lessonXX/`. Gõ lại là cách nhanh nhất để thấm.
4. **Làm Bài tập** theo 3 mức: 🟢 cơ bản → 🟡 nâng cao → 🔴 thử thách.
5. **Tự kiểm tra** bằng quiz cuối bài (che đáp án, trả lời xong mới mở).
6. **Làm milestone dự án** của bài đó.
7. **Cập nhật `PROGRESS.md`** (tick checklist + ghi nhật ký).

## 👨‍🏫 Làm việc với "giáo viên" (Claude)

Cứ nhắn mấy câu kiểu này trong VS Code:

| Mày nhắn | Tao làm |
|---------|---------|
| `chấm lab 3.2` / `review practice/lesson03/` | Đọc code, chỉ lỗi, gợi ý cách viết "chuẩn LangGraph" hơn |
| `gợi ý bài 4.3` | Gợi ý từng bước, không đưa lời giải ngay |
| `quiz bài 5` | Ra thêm câu hỏi mới (khó hơn quiz trong file) |
| `giải thích lại reducer` | Giải thích theo cách khác + ví dụ mới |
| `xong bài 6` | Kiểm tra checklist, cập nhật `PROGRESS.md`, chuẩn bị bài sau |
| `review milestone M4` | Review dự án theo tiêu chí Definition of Done |

## 📁 Cấu trúc thư mục

```
AI_Agents_in_LangGraph/
├── README.md              ← file này
├── PROGRESS.md            ← theo dõi tiến độ
├── requirements.txt
├── .env.example           ← copy thành .env rồi điền key
├── lessons/               ← giáo trình (lý thuyết + lab + bài tập + quiz)
├── practice/              ← code mày tự gõ, chia theo bài
│   └── check_setup.py     ← chạy đầu tiên để kiểm tra môi trường
└── project/
    └── PROJECT.md         ← đề bài + milestone dự án cá nhân
```

## 📚 Tài liệu gốc

- Khóa học: https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/
- LangGraph docs: https://docs.langchain.com/oss/python/langgraph/overview
- LangChain Academy (free, sâu hơn): https://academy.langchain.com/courses/intro-to-langgraph
