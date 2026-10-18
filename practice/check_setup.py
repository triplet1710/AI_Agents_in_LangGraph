"""Kiểm tra môi trường học LangGraph.

Chạy từ thư mục gốc:  python practice/check_setup.py
"""
import os
import sys
from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

PACKAGES = [
    "langgraph",
    "langchain",
    "langchain-core",
    "langchain-ollama",
    "langgraph-checkpoint-sqlite",
    "langchain-tavily",
    "tavily-python",
]


def check_packages() -> bool:
    print("1) Packages")
    ok = True
    for name in PACKAGES:
        try:
            print(f"   ✅ {name} {version(name)}")
        except PackageNotFoundError:
            print(f"   ❌ {name} chưa cài")
            ok = False
    return ok


def check_llm() -> bool:
    print("2) LLM")
    model_name = os.environ.get("MODEL")
    if not model_name:
        print("   ❌ Chưa đặt MODEL trong .env")
        return False
    from langchain.chat_models import init_chat_model

    # qwen3 trên Ollama bật "thinking" mặc định → tắt cho nhanh và output sạch
    extra = {"reasoning": False, "num_ctx": 8192} if model_name.startswith("ollama:") else {}
    reply = init_chat_model(model_name, temperature=0, **extra).invoke("Reply with exactly one word: OK")
    print(f"   ✅ {model_name} trả lời: {reply.content!r}")
    return True


def check_tavily() -> bool:
    print("3) Tavily")
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        print("   ❌ Chưa đặt TAVILY_API_KEY trong .env")
        return False
    from tavily import TavilyClient

    result = TavilyClient(api_key=key).search("LangGraph", max_results=1)
    print(f"   ✅ Kết quả đầu tiên: {result['results'][0]['title']}")
    return True


if __name__ == "__main__":
    print(f"Python {sys.version.split()[0]}\n")
    results = [check_packages()]
    for check in (check_llm, check_tavily):
        try:
            results.append(check())
        except Exception as e:  # in lỗi gọn để dễ debug
            print(f"   ❌ {type(e).__name__}: {e}")
            results.append(False)
    print("\n🎉 Sẵn sàng học!" if all(results) else "\n⚠️  Sửa các mục ❌ ở trên rồi chạy lại.")
