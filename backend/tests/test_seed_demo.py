"""Seed-level integration checks: deterministic seed, backfill files that stay
unprotected by retained snapshots, and retirement interplay (the seed must not
resurrect files a retired order reclaimed)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.database import Base
import app.models  # noqa: F401
from app.models import DataFile, LakeTable, TableSnapshot, User
from app.schemas.retirement import RetirementCreateRequest
from app.services import retirement_service
from scripts import seed_demo


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _run_seed(db, monkeypatch):
    monkeypatch.setattr(seed_demo, "init_db", lambda *a, **k: None)
    return seed_demo.run_seed(db=db)


def test_seed_is_idempotent_and_leaves_backfill_unprotected(db, monkeypatch):
    first = _run_seed(db, monkeypatch)
    second = _run_seed(db, monkeypatch)
    assert first == second  # 幂等：两次 seed 的计数完全一致

    ods = db.query(LakeTable).filter_by(db_name="ods", table_name="events").one()
    refs = retirement_service.protected_path_refs(db, ods.id)
    backfill_paths = {
        row.path
        for row in db.query(DataFile).filter(
            DataFile.table_id == ods.id, DataFile.write_source == "backfill"
        )
    }
    assert len(backfill_paths) == 5  # 3 + 2 个迟到文件
    # backfill 文件不被任何保留快照引用；同分区其余文件受保护
    assert not any(path in refs for path in backfill_paths)
    old_partition_files = db.query(DataFile).filter(
        DataFile.table_id == ods.id, DataFile.partition_value == "20261103"
    ).all()
    protected = [row for row in old_partition_files if row.path in refs]
    reclaimable = [row for row in old_partition_files if row.path not in refs]
    assert len(protected) + len(reclaimable) == len(old_partition_files)
    assert len(reclaimable) == 3


def test_seed_does_not_resurrect_retired_files(db, monkeypatch):
    _run_seed(db, monkeypatch)
    ods = db.query(LakeTable).filter_by(db_name="ods", table_name="events").one()
    user = db.query(User).filter_by(role="engineer").one()

    retirement = retirement_service.create_retirement(
        db, user, ods, RetirementCreateRequest(partition_values=["20261103"])
    )["retirement"]
    result = retirement_service.execute_retirement(db, user, retirement["id"])
    assert result["ok"] is True
    reclaimed = result["retirement"]["result"]["reclaimed_file_count"]
    assert reclaimed == 3  # 只有 backfill 文件被回收

    summary = _run_seed(db, monkeypatch)
    remaining = db.query(DataFile).filter(
        DataFile.table_id == ods.id, DataFile.partition_value == "20261103"
    ).count()
    assert remaining == 20  # 20 个受保护文件仍在，被回收的 3 个没有被 seed 复活
    assert summary["partition_retirement"] == 1
