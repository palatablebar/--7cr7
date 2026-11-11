"""Engine / session factory shared by the FastAPI app and the Celery worker."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}, "pool_pre_ping": True, "future": True}
    return {"pool_pre_ping": True, "pool_recycle": 1800, "pool_size": 8, "max_overflow": 4, "future": True}


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(max_attempts: int = 30, delay: float = 2.0) -> None:
    """Create all tables, waiting for MySQL to finish its first boot."""
    import time

    import app.models  # noqa: F401

    last_error = None
    for _ in range(max_attempts):
        try:
            Base.metadata.create_all(bind=engine)
            _ensure_schema_patches()
            return
        except Exception as exc:  # pragma: no cover - infra retry
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"database bootstrap failed: {last_error}")


def _ensure_schema_patches() -> None:
    """create_all() never alters pre-existing tables; patch the columns the
    retirement feature added so existing MySQL volumes keep working."""
    from sqlalchemy import inspect, text

    patches = {
        "partition_specs": (
            "lifecycle",
            "ALTER TABLE partition_specs ADD COLUMN lifecycle VARCHAR(16) NOT NULL DEFAULT 'active'",
        ),
    }
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table_name, (column, ddl) in patches.items():
            if table_name not in inspector.get_table_names():
                continue
            columns = {col["name"] for col in inspector.get_columns(table_name)}
            if column not in columns:
                conn.execute(text(ddl))
