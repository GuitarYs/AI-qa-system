"""全局配置。所有可调参数集中在这里。"""
import os
from pathlib import Path

# 项目根目录（backend 的上上级，即题13 目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 数据目录：存放 SQLite 数据库、FAISS 索引、上传的文档。
# 默认放到用户主目录（避免项目路径含中文导致 FAISS 等 C++ 库写盘失败，Windows 已知问题）。
# 可用环境变量 KEFU_DATA_DIR 覆盖。
DATA_DIR = Path(os.environ.get("KEFU_DATA_DIR", str(Path.home() / ".kefu_data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "kefu.db"
FAISS_PATH = DATA_DIR / "faiss_index"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---- LLM 配置（DeepSeek，OpenAI 兼容接口）----
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LLM_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
LLM_TEMPERATURE = 0.2

# ---- 向量 / 嵌入配置 ----
# 使用阿里云 DashScope text-embedding-v3（OpenAI 兼容接口，中文效果好，无需本地模型）
EMBED_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
EMBED_BASE_URL = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-v3")
EMBED_DIM = 512  # text-embedding-v3 支持 512/768/1024，这里用 512

# RAG 检索参数
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "4"))
# 召回 Top-1 相似度阈值：低于此值认为「知识库里没有」，诚实承认不知道并转人工（防幻觉核心）
RAG_MIN_SCORE = float(os.environ.get("RAG_MIN_SCORE", "0.6"))

# 意图识别阈值 / 关键词兜底
INTENT_KEYWORDS = {
    "transfer": ["人工", "客服", "投诉", "转人工", "找人工", "真人", "打电话", "举报", "退款纠纷", "我要退款"],
    "order":    ["订单", "发货", "物流", "快递", "查订单", "查一下订单", "到哪了", "什么时候到", "包裹"],
}
