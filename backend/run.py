"""后端启动入口：python run.py（在 backend 目录下执行，或 python backend/run.py）。"""
import os
import sys
import webbrowser
import threading

# 确保 backend 目录在 sys.path（无论从哪里启动都能 import app.*）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn  # noqa: E402


def _open_browser():
    if os.environ.get("NO_BROWSER") != "1":
        webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(2.0, _open_browser).start()
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
