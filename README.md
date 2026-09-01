# 题13 · AI 全栈客服系统

面向云协作 SaaS 平台「云作 Cloudwork」的端到端 AI 客服系统，覆盖**前端 + 后端 + AI + 数据**四大栈，实现「用户咨询 → RAG 智能问答 → 置信度判断 → 转人工工单 → 数据看板闭环」。

---

## 一、快速启动（一键命令）

### 方式 A：本机 conda（推荐，已实测）

```bat
:: Windows：双击或命令行执行
start.bat
```

脚本会自动：① 检查/创建 `ys-ai-kefu` conda 环境 → ② 构建前端（若未构建）→ ③ 启动后端并打开浏览器 `http://localhost:8000`。

> 依赖两个真实 API（已在 shell 环境变量中配置好）：
> - `DEEPSEEK_API_KEY` —— LLM（DeepSeek `deepseek-chat`）
> - `DASHSCOPE_API_KEY` —— 向量嵌入（DashScope `text-embedding-v4`）

### 方式 B：docker-compose（已在 Rocky Linux 9.4 虚拟机实测）

```bash
export DEEPSEEK_API_KEY=sk-xxxx
export DASHSCOPE_API_KEY=sk-xxxx
docker compose up -d --build
# 打开 http://localhost:8000
```

也可直接使用仓库内的一键脚本：

```bash
./docker-start.sh       # Linux / macOS / Git Bash
docker-start.bat        # Windows
```

### 手动启动

```bash
conda activate ys-ai-kefu
cd frontend && npm install && npm run build && cd ..
cd backend && python run.py
```

---

## 二、功能总览（对照题目 4 大模块）

| 模块 | 说明 | 入口 |
| --- | --- | --- |
| **① 知识库管理** | 文档上传/增删改查，自动分块 + 向量化入库，版本历史追溯 | 管理后台 → 知识库管理 |
| **② 对话引擎** | RAG 检索 + LLM 生成（带来源引用）、置信度判断 + 防幻觉、意图识别（咨询/投诉/查订单）、转人工、多轮上下文 | 用户端 |
| **③ 工单系统** | 转人工自动生成工单（AI 摘要 + 优先级）、分配、状态流转、AI 建议回复（知识库 + 历史相似工单）、人工处理意见保存 | 管理后台 → 工单系统 |
| **④ 数据分析看板** | 今日会话量、AI 解决率、平均响应时长、热门问题 Top10（AI 聚类）、知识库缺口分析、满意度，时间范围筛选 + 可视化 | 管理后台 → 数据看板 |

---

## 三、技术选型

| 层 | 选型 | 理由 |
| --- | --- | --- |
| 前端 | React 18 + Vite + Recharts | 单页应用，聊天窗口 + 管理后台双界面 |
| 后端 | Python FastAPI + SQLAlchemy | 异步、类型友好、开发快 |
| 关系库 | SQLite | 单机跑通，零部署；ORM 可平滑切 MySQL |
| 向量库 | chromadb（持久化） | 向量+文本落盘到 ~/.kefu_data/chroma，重启不丢、无需重建；更新/删除文档时同步删向量，与 DB 严格一致 |
| 嵌入 | DashScope `text-embedding-v4` | 中文效果好，OpenAI 兼容接口，无需本地模型 |
| LLM | DeepSeek `deepseek-chat` | OpenAI 兼容，性价比高，已实测连通 |

> **防幻觉核心**：召回 Top-1 相似度 < 阈值（默认 0.6）时，系统诚实回答「不知道」并转人工，**绝不硬编知识库外的答案**。

---

## 四、项目结构

```
题13-AI全栈客服系统/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 路由 + 静态托管 + 启动播种
│   │   ├── config.py        # 全局配置（阈值/模型/路径）
│   │   ├── models.py        # ORM：用户/会话/消息/工单/文档/版本/分块/反馈/订单
│   │   ├── chunking.py      # FAQ 感知分块
│   │   ├── embeddings.py    # DashScope 嵌入封装
│   │   ├── vector_store.py  # chromadb 封装
│   │   ├── rag.py           # RAG 检索（active 过滤 + 置信度）
│   │   ├── llm.py           # DeepSeek 客户端
│   │   ├── intent.py        # 意图识别（规则 + LLM）
│   │   ├── chat_service.py  # 对话引擎
│   │   ├── kb_service.py    # 知识库 CRUD + 版本 + 向量化
│   │   ├── ticket_service.py# 工单 + AI 摘要/建议回复/相似工单
│   │   ├── clustering.py    # AI 聚类（numpy KMeans + LLM 标签）
│   │   ├── dashboard_service.py # 看板统计
│   │   └── seed.py          # 种子数据
│   └── run.py               # 启动入口
├── frontend/                # Vite + React
│   └── src/views/           # ChatView / Dashboard / KnowledgeBase / Tickets
├── seed_data/kb/            # 4 份种子知识库（.md）
├── start.bat / start.sh     # 一键启动
├── docker-compose.yml / Dockerfile / .dockerignore
├── docker-start.sh / docker-start.bat  # Docker 一键启动
└── 设计说明.md / Prompt日志.md / 自评反思.md
```

---

## 五、验收自查清单

- [x] 端到端可跑：一条命令起服务，浏览器打开可对话、可看板
- [x] AI 真用：RAG / 意图识别 / 聚类 / 建议回复均真调 DeepSeek + DashScope，无 mock
- [x] 防幻觉：超纲问题（如问股票代码）Top-1 < 0.6 → 诚实转人工，不硬编
- [x] 数据真实：看板数字全部由真实对话/工单表实时统计（含 10 历史工单 + 8 历史会话种子）
- [x] 种子数据：4 知识库（60 条 FAQ）+ 10 历史工单 + 7 用户（5 客户）+ 10 订单

---

## 六、种子数据说明

首次启动自动播种：7 用户（5 客户 + 2 客服）、4 篇知识库（共 60 条 FAQ）、10 个订单（每位客户 2 单）、10 张历史工单（覆盖待处理/处理中/已解决/已关闭、含满意度）、8 段历史 AI 已解决会话（分布在近 7 天，供看板趋势/聚类/缺口分析展示）。
