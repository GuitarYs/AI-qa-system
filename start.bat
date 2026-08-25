@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   云作 Cloudwork · AI 全栈客服系统 一键启动
echo ============================================================

REM ---------- 1. 检查 / 创建 conda 环境 ----------
echo [1/3] 检查 conda 环境 ys-ai-kefu ...
conda env list 2>nul | findstr /C:"ys-ai-kefu" >nul
if errorlevel 1 (
    echo       未找到 ys-ai-kefu，尝试从 ys-ai 克隆 ...
    conda create -n ys-ai-kefu --clone ys-ai -y
    if errorlevel 1 (
        echo       克隆失败，改为新建空环境并安装依赖 ...
        conda create -n ys-ai-kefu python=3.11 -y
        call conda run -n ys-ai-kefu pip install -r backend\requirements.txt
    )
)

REM ---------- 2. 构建前端（若未构建） ----------
echo [2/3] 构建前端 ...
if not exist "frontend\dist\index.html" (
    pushd frontend
    call npm install --no-audit --no-fund
    call npm run build
    popd
)

REM ---------- 3. 启动后端 ----------
echo [3/3] 启动后端 http://localhost:8000 ...
echo        （浏览器将自动打开，Ctrl+C 停止）
cd backend
call conda run -n ys-ai-kefu --no-capture-output python run.py

endlocal
