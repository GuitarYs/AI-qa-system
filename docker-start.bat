@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker is not installed or not in PATH.
  exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] docker compose plugin is not available.
  exit /b 1
)

if not exist .env (
  if defined DEEPSEEK_API_KEY (
    if defined DASHSCOPE_API_KEY (
      > .env echo DEEPSEEK_API_KEY=%DEEPSEEK_API_KEY%
      >> .env echo DASHSCOPE_API_KEY=%DASHSCOPE_API_KEY%
      >> .env echo KEFU_DATA_DIR=/app/data
      echo [INFO] Generated .env from environment variables.
    ) else (
      echo [ERROR] DASHSCOPE_API_KEY is not set.
      exit /b 1
    )
  ) else (
    echo [ERROR] DEEPSEEK_API_KEY is not set.
    exit /b 1
  )
)

echo [1/2] Building and starting containers...
docker compose up -d --build
if errorlevel 1 (
  echo [ERROR] docker compose failed.
  exit /b 1
)

echo [2/2] Current status:
docker compose ps
echo.
echo Done. Open: http://localhost:8000
