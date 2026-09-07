"""
Database session and connection management for Client Core Service.
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings
from src.models.base import Base


def create_db_engine(db_url: str | None = None) -> Any:
    url = db_url or settings.database_url
    connect_args: dict[str, Any] = {}

    if url.startswith("sqlite"):
        if "///" in url and not url.startswith("sqlite:///:memory:"):
            db_path_str = url.split("///", 1)[1]
            db_path = Path(db_path_str)
            if db_path.parent and not db_path.parent.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
        connect_args["check_same_thread"] = False
        engine = create_engine(url, connect_args=connect_args, echo=settings.app_debug)
    else:
        engine = create_engine(url, pool_size=10, max_overflow=20, pool_pre_ping=True)

    return engine


engine = create_db_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def init_db(target_engine: Any = None) -> None:
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> bool:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
