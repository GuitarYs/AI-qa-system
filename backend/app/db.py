"""数据库连接与会话（SQLAlchemy + SQLite）。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from . import config

engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},  # FastAPI 多线程访问 SQLite 需要
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每个请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
