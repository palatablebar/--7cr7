"""Service-level tests for partition retirement (snapshot-guarded reclamation).

Runs against in-memory SQLite; Redis falls back to the in-memory lock/quota
implementation, so no external services are needed.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.database import Base
import app.models  # noqa: F401  (register every model on the metadata)
from app.constants.error_codes import AppError, ErrorCode
from app.models import DataFile, LakeTable, PartitionRetirement, PartitionSpec, TableSnapshot, User
from app.schemas.plan import PlanCreateRequest
from app.schemas.retirement import RetirementCreateRequest
from app.services import plan_service, retirement_service, snapshot_service
from app.utils.lake import checksum_of


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


@pytest.fixture()
def user(db):
    row = User(email="eng@lake.local", password_hash="x", display_name="沈知微", role="engineer")
    db.add(row)
    db.commit()
    return row


def _make_table(db, table_name="events") -> LakeTable:
    table = LakeTable(
        db_name="ods",
        table_name=table_name,
        partition_key="dt",
        file_format="parquet",
        target_file_size_mb=256,
        small_file_threshold_mb=64,
        status="active",
    )
    db.add(table)
    db.commit()
    return table


def _add_file(db, table, partition_value, name, size_mb=10.0, rows=1000) -> DataFile:
    size_bytes = int(size_mb * 1024 * 1024)
    path = (
        f"s3://shiguang-lake/warehouse/{table.db_name}/{table.table_name}"
        f"/dt={partition_value}/{name}.parquet"
    )
    row = DataFile(
        table_id=table.id,
        partition_value=partition_value,
        path=path,
        size_bytes=size_bytes,
        row_count=rows,
        checksum=checksum_of(path, rows, size_bytes),
        file_format="parquet",
        write_source="flink",
    )
    db.add(row)
    db.commit()
    return row


def _file_paths(db, table, partition_value) -> set[str]:
    return {
        row.path
        for row in db.query(DataFile).filter(
            DataFile.table_id == table.id, DataFile.partition_value == partition_value
        )
    }


def _spec(db, table, partition_value) -> PartitionSpec | None:
    return (
        db.query(PartitionSpec)
        .filter(PartitionSpec.table_id == table.id, PartitionSpec.partition_value == partition_value)
        .first()
    )


@pytest.fixture()
def scene(db, user):
    """dt=20261101: 3 files, two covered by snapshot v1 (protected), one late
    backfill (reclaimable). dt=20261102: 2 files, no snapshot at all."""
    table = _make_table(db)
    protected_a = _add_file(db, table, "20261101", "part-00001", size_mb=30.0)
    protected_b = _add_file(db, table, "20261101", "part-00002", size_mb=20.0)
    snapshot_service.create_snapshot(db, table, created_by=user.id, note="基线快照 v1")
    late = _add_file(db, table, "20261101", "backfill-00001", size_mb=12.0)
    free_a = _add_file(db, table, "20261102", "part-00001", size_mb=8.0)
    free_b = _add_file(db, table, "20261102", "part-00002", size_mb=9.0)
    return {
        "table": table,
        "protected": {protected_a.path, protected_b.path},
        "late": late,
        "free": {free_a.path, free_b.path},
    }


# ---------------------------------------------------------------------------
# 回收清单
# ---------------------------------------------------------------------------

def test_reclaim_manifest_invariant(db, scene):
    preview = retirement_service.reclaim_preview(db, scene["table"])
    by_partition = {item["partition_value"]: item for item in preview["items"]}

    old = by_partition["20261101"]
    assert old["file_count"] == 3
    assert old["protected_count"] == 2
    assert old["reclaimable_count"] == 1
    # 引用数 + 可回收数 == 分区文件总数
    assert old["protected_count"] + old["reclaimable_count"] == old["file_count"]
    assert old["invariant_ok"] is True
    assert old["protected_files"][0]["snapshot_versions"] == [1]
    assert old["reclaimable_files"][0]["path"] == scene["late"].path

    new = by_partition["20261102"]
    assert (new["protected_count"], new["reclaimable_count"]) == (0, 2)
    assert new["protected_count"] + new["reclaimable_count"] == new["file_count"]
    assert preview["totals"]["invariant_ok"] is True


# ---------------------------------------------------------------------------
# 冻结：停止新合并
# ---------------------------------------------------------------------------

def test_create_freezes_partitions_and_blocks_new_plans(db, user, scene):
    table = scene["table"]
    result = retirement_service.create_retirement(
        db, user, table, RetirementCreateRequest(partition_values=["20261101"])
    )
    assert result["idempotent"] is False
    retirement = result["retirement"]
    assert retirement["status"] == "retiring"
    assert retirement["protected_file_count"] == 2
    assert retirement["reclaimable_file_count"] == 1
    assert _spec(db, table, "20261101").lifecycle == "retiring"
    assert _spec(db, table, "20261102").lifecycle == "active"

    # 冻结分区：不能生成新合并计划
    with pytest.raises(AppError) as excinfo:
        plan_service.create_plan(
            db, user, PlanCreateRequest(table_id=table.id, partition_values=["20261101"])
        )
    assert excinfo.value.code == ErrorCode.PARTITION_RETIRING.value

    # 未冻结分区：照常生成计划
    plan = plan_service.create_plan(
        db, user, PlanCreateRequest(table_id=table.id, partition_values=["20261102"])
    )
    assert plan["plan"]["status"] == "draft"

    # 冻结后，冻结前生成的草稿计划也不允许执行
    draft = plan_service.create_plan(
        db, user, PlanCreateRequest(table_id=table.id, partition_values=["20261102"])
    )["plan"]
    retirement_service.create_retirement(
        db, user, table, RetirementCreateRequest(partition_values=["20261102"])
    )
    with pytest.raises(AppError) as excinfo:
        plan_service.execute_plan(db, user, draft["id"])
    assert excinfo.value.code == ErrorCode.PARTITION_RETIRING.value


def test_create_is_idempotent_by_fingerprint(db, user, scene):
    table = scene["table"]
    payload = RetirementCreateRequest(partition_values=["20261101"])
    first = retirement_service.create_retirement(db, user, table, payload)["retirement"]
    second = retirement_service.create_retirement(db, user, table, payload)
    assert second["idempotent"] is True
    assert second["retirement"]["id"] == first["id"]
    assert db.query(PartitionRetirement).count() == 1


# ---------------------------------------------------------------------------
# 一次性退役 + 幂等执行
# ---------------------------------------------------------------------------

def test_execute_is_atomic_and_idempotent(db, user, scene):
    table = scene["table"]
    retirement = retirement_service.create_retirement(
        db, user, table, RetirementCreateRequest(partition_values=["20261101", "20261102"])
    )["retirement"]

    result = retirement_service.execute_retirement(db, user, retirement["id"])
    assert result["ok"] is True
    retired = result["retirement"]
    assert retired["status"] == "retired"
    assert retired["result"]["reclaimed_file_count"] == 3  # 1 backfill + 2 free

    # 受保护文件原样保留，可回收文件被清理
    assert _file_paths(db, table, "20261101") == scene["protected"]
    assert _file_paths(db, table, "20261102") == set()
    # 全部回收的分区留下墓碑，不再参与合并
    assert _spec(db, table, "20261102").lifecycle == "retired"
    assert _spec(db, table, "20261102").file_count == 0
    assert _spec(db, table, "20261101").lifecycle == "retired"

    # 重复执行：不重复清理，直接返回首次结果
    again = retirement_service.execute_retirement(db, user, retirement["id"])
    assert again["idempotent"] is True
    assert again["retirement"]["status"] == "retired"
    assert _file_paths(db, table, "20261101") == scene["protected"]
    assert db.query(DataFile).filter(DataFile.table_id == table.id).count() == 2


def test_execute_respects_snapshots_created_after_manifest(db, user, scene):
    """清单生成后新建的快照若引用了待删文件，执行时必须跳过它。"""
    table = scene["table"]
    retirement = retirement_service.create_retirement(
        db, user, table, RetirementCreateRequest(partition_values=["20261101"])
    )["retirement"]
    snapshot_service.create_snapshot(db, table, created_by=user.id, note="v2：backfill 也被引用")

    result = retirement_service.execute_retirement(db, user, retirement["id"])
    assert result["ok"] is True
    partition_result = result["retirement"]["result"]["partitions"][0]
    assert partition_result["reclaimed_count"] == 0
    assert partition_result["skipped_protected"] == [scene["late"].path]
    assert scene["late"].path in _file_paths(db, table, "20261101")


# ---------------------------------------------------------------------------
# 失败回滚 + 恢复原分区
# ---------------------------------------------------------------------------

def test_failed_execute_rolls_back_everything_then_restore(db, user, scene):
    table = scene["table"]
    retirement = retirement_service.create_retirement(
        db, user, table, RetirementCreateRequest(partition_values=["20261101", "20261102"])
    )["retirement"]
    before_counts = {
        value: len(_file_paths(db, table, value)) for value in ("20261101", "20261102")
    }

    result = retirement_service.execute_retirement(db, user, retirement["id"], simulate_failure=True)
    assert result["ok"] is False
    failed = result["retirement"]
    assert failed["status"] == "failed"
    assert failed["failure_reason"]

    # 中途失败不留半个分区：两个分区的文件都原样保留
    for value, count in before_counts.items():
        assert len(_file_paths(db, table, value)) == count
    # 分区仍处于冻结态（安全），等待恢复
    assert _spec(db, table, "20261101").lifecycle == "retiring"

    # 失败的退役单不能直接执行，先恢复原分区
    with pytest.raises(AppError) as excinfo:
        retirement_service.execute_retirement(db, user, retirement["id"])
    assert excinfo.value.code == ErrorCode.RETIREMENT_STATE_INVALID.value

    restored = retirement_service.restore_retirement(db, user, retirement["id"])["retirement"]
    assert restored["status"] == "restored"
    assert _spec(db, table, "20261101").lifecycle == "active"
    assert _spec(db, table, "20261102").lifecycle == "active"

    # 恢复后分区可以重新生成合并计划
    plan = plan_service.create_plan(
        db, user, PlanCreateRequest(table_id=table.id, partition_values=["20261102"])
    )
    assert plan["plan"]["status"] == "draft"

    # 恢复是幂等的
    again = retirement_service.restore_retirement(db, user, retirement["id"])
    assert again["idempotent"] is True


def test_retired_cannot_be_restored(db, user, scene):
    table = scene["table"]
    retirement = retirement_service.create_retirement(
        db, user, table, RetirementCreateRequest(partition_values=["20261102"])
    )["retirement"]
    retirement_service.execute_retirement(db, user, retirement["id"])
    with pytest.raises(AppError) as excinfo:
        retirement_service.restore_retirement(db, user, retirement["id"])
    assert excinfo.value.code == ErrorCode.RETIREMENT_STATE_INVALID.value
