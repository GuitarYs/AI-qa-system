#!/usr/bin/env bash
# 云作 Cloudwork · AI 全栈客服系统 一键启动（Linux / macOS / Git Bash）
set -e
cd "$(dirname "$0")"

echo "============================================================"
echo "  云作 Cloudwork · AI 全栈客服系统 一键启动"
echo "============================================================"

# 1. 检查 / 创建 conda 环境
echo "[1/3] 检查 conda 环境 ys-ai-kefu ..."
if ! conda env list | grep -q "ys-ai-kefu"; then
    echo "      未找到 ys-ai-kefu，尝试从 ys-ai 克隆 ..."
    conda create -n ys-ai-kefu --clone ys-ai -y || {
        conda create -n ys-ai-kefu python=3.11 -y
        conda run -n ys-ai-kefu pip install -r backend/requirements.txt
    }
fi

# 2. 构建前端（若未构建）
echo "[2/3] 构建前端 ..."
if [ ! -f "frontend/dist/index.html" ]; then
    (cd frontend && npm install --no-audit --no-fund && npm run build)
fi

# 3. 启动后端
echo "[3/3] 启动后端 http://localhost:8000 ..."
(cd backend && conda run -n ys-ai-kefu --no-capture-output python run.py)
