# 多阶段构建：前端 Vite 构建 → 后端 FastAPI 单容器托管全部（前端静态 + API）
# 说明：本机无 docker，此文件为「docker-compose 优先」的交付，未在本机实测；
#       本机推荐直接双击 start.bat 一键启动。

# ---------- 前端构建 ----------
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 后端 ----------
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY seed_data/ ./seed_data/
COPY --from=frontend /fe/dist ./frontend/dist

# 数据目录（SQLite + 上传文件）；向量库 FAISS 为内存态，启动时从 DB 重建
ENV KEFU_DATA_DIR=/app/data
EXPOSE 8000
CMD ["python", "backend/run.py"]
