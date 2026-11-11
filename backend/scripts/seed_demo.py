"""Idempotent demo seed for the 拾光 lake workspace.

Scene (see batch-plan gb-548):
  3 lake tables — ods.events (8 dt partitions), dwd.orders (4 partitions),
  dim.user (1 partition); a historical completed compaction on ods.events
  dt=20261108 with before/after manifest snapshots; 3 role accounts.

Determinism: every file is generated from a SHA-256 derived RNG seed, so two
runs produce byte-identical paths/sizes/checksums. Re-running the script only
upserts by natural keys (email / db+table / path / table+version) and therefore
never changes row counts. The script ends with a machine-readable line:

    SEED_SUMMARY {"compact_job":1,"compact_plan":1,...}

which the batch QA uses to verify idempotency.
"""
import hashlib
import json
import random

from sqlalchemy import func

from app.compaction.binpack import build_plan
from app.compaction.cost_model import CostParams
from app.config.database import SessionLocal, init_db
from app.config.settings import settings
from app.constants.file_format import TableStatus
from app.constants.plan_status import PlanStatus
from app.models import (
    CompactJob,
    CompactPlan,
    DataFile,
    LakeTable,
    PartitionRetirement,
    PartitionSpec,
    TableSnapshot,
    User,
)
from app.services import auth_service, partition_service, snapshot_service
from app.utils.lake import checksum_of
from app.utils.logger import log_event

DEMO_PASSWORD = "Demo@2026"
SEED_PLAN_NOTE = "seed:historical-compaction"

ACCOUNTS = [
    ("admin@lake.local", "顾砚舟", "admin"),
    ("eng@lake.local", "沈知微", "engineer"),
    ("analyst@lake.local", "周予安", "analyst"),
]

TABLE_CATALOGUE = [
    {
        "key": "ods_events",
        "db_name": "ods",
        "table_name": "events",
        "partition_key": "dt",
        "target_file_size_mb": 256,
        "small_file_threshold_mb": 64,
        "partitions": ["20261103", "20261104", "20261105", "20261106", "20261107", "20261108", "20261109", "20261110"],
        "small_counts": [18, 24, 12, 27, 21, 30, 15, 23],
        "large_counts": [2, 1, 0, 3, 1, 0, 2, 1],
        "small_range_mb": (6.0, 62.0),
        "large_range_mb": (92.0, 178.0),
        "avg_row_bytes": 380,
        "owner_name": "沈知微",
        "description": "客户端埋点事件原始层，Flink 每小时落盘，供 Presto 即席查询",
    },
    {
        "key": "dwd_orders",
        "db_name": "dwd",
        "table_name": "orders",
        "partition_key": "dt",
        "target_file_size_mb": 256,
        "small_file_threshold_mb": 64,
        "partitions": ["20261107", "20261108", "20261109", "20261110"],
        "small_counts": [16, 22, 14, 26],
        "large_counts": [3, 2, 4, 2],
        "small_range_mb": (8.0, 60.0),
        "large_range_mb": (118.0, 238.0),
        "avg_row_bytes": 520,
        "owner_name": "沈知微",
        "description": "订单明细宽表，BI 日活报表主力消费表",
    },
    {
        "key": "dim_user",
        "db_name": "dim",
        "table_name": "user",
        "partition_key": "dt",
        "target_file_size_mb": 128,
        "small_file_threshold_mb": 64,
        "partitions": ["20261110"],
        "small_counts": [18],
        "large_counts": [0],
        "small_range_mb": (4.0, 58.0),
        "large_range_mb": (80.0, 120.0),
        "avg_row_bytes": 640,
        "owner_name": "周予安",
        "description": "用户维表全量快照，每日重建，下游画像与人群圈选",
    },
]

HIST_PARTITION = "20261108"

# 快照之后迟到的 backfill 文件：不被任何保留快照引用，是退役回收的候选；
# 同分区的其余文件仍被快照引用而受保护 —— 退役页借此展示 保护引用 vs 可回收。
BACKFILL_CATALOGUE = [
    {"table_key": "ods_events", "partition_value": "20261103", "count": 3, "size_range_mb": (9.0, 41.0)},
    {"table_key": "ods_events", "partition_value": "20261104", "count": 2, "size_range_mb": (12.0, 47.0)},
    {"table_key": "dwd_orders", "partition_value": "20261107", "count": 3, "size_range_mb": (10.0, 38.0)},
]


def _rng(*parts) -> random.Random:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _file_path(cfg: dict, partition_value: str, index: int, kind: str) -> str:
    digest = hashlib.sha256(f"{cfg['key']}:{partition_value}:{index}:{kind}".encode()).hexdigest()[:8]
    return (
        f"{settings.LAKE_BUCKET}/warehouse/{cfg['db_name']}/{cfg['table_name']}"
        f"/{cfg['partition_key']}={partition_value}/part-{index:05d}-{digest}.parquet"
    )


def build_catalogue() -> dict[str, dict[str, list[dict]]]:
    """Deterministic in-memory file catalogue: table_key -> partition -> files."""
    catalogue: dict[str, dict[str, list[dict]]] = {}
    for cfg in TABLE_CATALOGUE:
        per_partition: dict[str, list[dict]] = {}
        for index, partition_value in enumerate(cfg["partitions"]):
            rng = _rng(cfg["key"], partition_value)
            files: list[dict] = []
            small_count = cfg["small_counts"][index]
            large_count = cfg["large_counts"][index]
            for item in range(small_count):
                size_mb = round(rng.uniform(*cfg["small_range_mb"]), 1)
                files.append(_make_file(cfg, partition_value, item, size_mb, "flink"))
            for item in range(large_count):
                size_mb = round(rng.uniform(*cfg["large_range_mb"]), 1)
                files.append(_make_file(cfg, partition_value, small_count + item, size_mb, "flink"))
            per_partition[partition_value] = files
        catalogue[cfg["key"]] = per_partition
    return catalogue


def _make_file(cfg: dict, partition_value: str, index: int, size_mb: float, source: str) -> dict:
    size_bytes = int(round(size_mb * 1024 * 1024))
    row_count = max(1, int(size_bytes / cfg["avg_row_bytes"]))
    path = _file_path(cfg, partition_value, index, "small" if size_mb < cfg["small_file_threshold_mb"] else "large")
    return {
        "path": path,
        "partition_value": partition_value,
        "size_bytes": size_bytes,
        "row_count": row_count,
        "checksum": checksum_of(path, row_count, size_bytes),
        "file_format": "parquet",
        "write_source": source,
    }


def build_backfill_files() -> dict[str, list[dict]]:
    """Deterministic late-arriving files, inserted *after* the snapshots."""
    cfg_by_key = {cfg["key"]: cfg for cfg in TABLE_CATALOGUE}
    backfill: dict[str, list[dict]] = {}
    for spec in BACKFILL_CATALOGUE:
        cfg = cfg_by_key[spec["table_key"]]
        rng = _rng("backfill", cfg["key"], spec["partition_value"])
        files: list[dict] = []
        for index in range(spec["count"]):
            size_mb = round(rng.uniform(*spec["size_range_mb"]), 1)
            size_bytes = int(round(size_mb * 1024 * 1024))
            row_count = max(1, int(size_bytes / cfg["avg_row_bytes"]))
            digest = hashlib.sha256(
                f"backfill:{cfg['key']}:{spec['partition_value']}:{index}".encode()
            ).hexdigest()[:8]
            path = (
                f"{settings.LAKE_BUCKET}/warehouse/{cfg['db_name']}/{cfg['table_name']}"
                f"/{cfg['partition_key']}={spec['partition_value']}/backfill-{index:05d}-{digest}.parquet"
            )
            files.append(
                {
                    "path": path,
                    "partition_value": spec["partition_value"],
                    "size_bytes": size_bytes,
                    "row_count": row_count,
                    "checksum": checksum_of(path, row_count, size_bytes),
                    "file_format": "parquet",
                    "write_source": "backfill",
                }
            )
        backfill.setdefault(spec["table_key"], []).extend(files)
    return backfill


def _upsert_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, display_name, role in ACCOUNTS:
        users[role] = auth_service.upsert_user(db, email, DEMO_PASSWORD, display_name, role)
    return users


def _upsert_tables(db) -> dict[str, LakeTable]:
    tables: dict[str, LakeTable] = {}
    for cfg in TABLE_CATALOGUE:
        table = (
            db.query(LakeTable)
            .filter(LakeTable.db_name == cfg["db_name"], LakeTable.table_name == cfg["table_name"])
            .first()
        )
        if table is None:
            table = LakeTable(
                db_name=cfg["db_name"],
                table_name=cfg["table_name"],
                partition_key=cfg["partition_key"],
                file_format="parquet",
                target_file_size_mb=cfg["target_file_size_mb"],
                small_file_threshold_mb=cfg["small_file_threshold_mb"],
                status=TableStatus.ACTIVE.value,
                description=cfg["description"],
                owner_name=cfg["owner_name"],
            )
            db.add(table)
            db.flush()
        else:
            table.partition_key = cfg["partition_key"]
            table.target_file_size_mb = cfg["target_file_size_mb"]
            table.small_file_threshold_mb = cfg["small_file_threshold_mb"]
            table.description = cfg["description"]
            table.owner_name = cfg["owner_name"]
        tables[cfg["key"]] = table
    db.commit()
    return tables


def _insert_files(db, table: LakeTable, files: list[dict]) -> None:
    for item in files:
        db.add(
            DataFile(
                table_id=table.id,
                partition_value=item["partition_value"],
                path=item["path"],
                size_bytes=item["size_bytes"],
                row_count=item["row_count"],
                checksum=item["checksum"],
                file_format=item["file_format"],
                write_source=item["write_source"],
            )
        )
    db.commit()


def _build_historical_plan(cfg: dict, files: list[dict]) -> dict:
    return build_plan(
        table={
            "db_name": cfg["db_name"],
            "table_name": cfg["table_name"],
            "partition_key": cfg["partition_key"],
            "target_file_size_mb": cfg["target_file_size_mb"],
            "small_file_threshold_mb": cfg["small_file_threshold_mb"],
            "bucket": settings.LAKE_BUCKET,
        },
        partition_files={HIST_PARTITION: files},
        strategy="ffd_256",
        cost_params=CostParams(
            bandwidth_mb_per_s=settings.BANDWIDTH_MBPS,
            per_file_overhead_s=settings.PER_FILE_OVERHEAD_S,
            unit_cost_per_gb=settings.UNIT_COST_PER_GB,
            cost_per_file_day=settings.COST_PER_FILE_DAY,
        ),
    )


def _apply_merge(db, table: LakeTable, plan: CompactPlan) -> dict:
    """Rewrite the metadata manifest exactly like app/tasks/compact_job.py does."""
    rewritten = 0
    produced = 0
    rows_before = 0
    rows_after = 0
    bytes_written = 0
    for group in plan.groups:
        if group.get("action") != "rewrite":
            continue
        paths = [item["path"] for item in group["files"]]
        inputs = db.query(DataFile).filter(DataFile.table_id == table.id, DataFile.path.in_(paths)).all()
        if len(inputs) < len(paths):
            continue
        output_rows = int(group["output_rows"])
        output_size = int(group["output_size_bytes"])
        db.query(DataFile).filter(DataFile.table_id == table.id, DataFile.path.in_(paths)).delete(
            synchronize_session=False
        )
        db.add(
            DataFile(
                table_id=table.id,
                partition_value=group["partition_value"],
                path=group["output_file"],
                size_bytes=output_size,
                row_count=output_rows,
                checksum=checksum_of(group["output_file"], output_rows, output_size),
                file_format=table.file_format,
                write_source="compaction",
            )
        )
        rewritten += len(inputs)
        produced += 1
        bytes_written += output_size
        rows_before += sum(int(row.row_count) for row in inputs)
        rows_after += output_rows
    db.commit()
    return {
        "rewritten_files": rewritten,
        "produced_files": produced,
        "bytes_written": bytes_written,
        "rows_before": rows_before,
        "rows_after": rows_after,
    }


def _retired_reclaimed_paths(db) -> set[str]:
    """Paths already reclaimed by a retired retirement order: the seed must not
    resurrect them when converging the demo dataset."""
    reclaimed: set[str] = set()
    rows = db.query(PartitionRetirement).filter(PartitionRetirement.status == "retired").all()
    for row in rows:
        for path in (row.result or {}).get("reclaimed_paths", []):
            reclaimed.add(path)
    return reclaimed


def _ensure_desired_files(db, tables: dict[str, LakeTable], catalogue, seed_plan: CompactPlan, backfill) -> None:
    """Second-run path: make sure the post-merge file state exists, never duplicate."""
    retired_paths = _retired_reclaimed_paths(db)
    for cfg in TABLE_CATALOGUE:
        table = tables[cfg["key"]]
        existing = {
            row[0]
            for row in db.query(DataFile.path).filter(DataFile.table_id == table.id).all()
        }
        desired: list[dict] = []
        for partition_value, files in catalogue[cfg["key"]].items():
            for item in files:
                if cfg["key"] == "ods_events" and partition_value == HIST_PARTITION:
                    if item["size_bytes"] < cfg["small_file_threshold_mb"] * 1024 * 1024:
                        continue  # merged away by the historical plan
                desired.append(item)
        desired.extend(backfill.get(cfg["key"], []))
        desired = [item for item in desired if item["path"] not in retired_paths]
        if seed_plan.table_id != table.id:
            added = [item for item in desired if item["path"] not in existing]
            if added:
                _insert_files(db, table, added)
            continue
        for group in seed_plan.groups:
            if group.get("action") != "rewrite":
                continue
            desired.append(
                {
                    "path": group["output_file"],
                    "partition_value": group["partition_value"],
                    "size_bytes": int(group["output_size_bytes"]),
                    "row_count": int(group["output_rows"]),
                    "checksum": checksum_of(group["output_file"], group["output_rows"], group["output_size_bytes"]),
                    "file_format": "parquet",
                    "write_source": "compaction",
                }
            )
        added = [item for item in desired if item["path"] not in existing]
        if added:
            _insert_files(db, table, added)


def _counts(db) -> dict:
    return {
        "lake_table": int(db.query(func.count(LakeTable.id)).scalar() or 0),
        "data_file": int(db.query(func.count(DataFile.id)).scalar() or 0),
        "partition_spec": int(db.query(func.count(PartitionSpec.id)).scalar() or 0),
        "compact_plan": int(db.query(func.count(CompactPlan.id)).scalar() or 0),
        "compact_job": int(db.query(func.count(CompactJob.id)).scalar() or 0),
        "table_snapshot": int(db.query(func.count(TableSnapshot.id)).scalar() or 0),
        "partition_retirement": int(db.query(func.count(PartitionRetirement.id)).scalar() or 0),
        "user": int(db.query(func.count(User.id)).scalar() or 0),
    }


def run_seed(db=None) -> dict:
    """Idempotent seed. Returns the SEED_SUMMARY counts and prints them."""
    init_db()
    own_session = db is None
    session = db or SessionLocal()
    try:
        users = _upsert_users(session)
        tables = _upsert_tables(session)
        catalogue = build_catalogue()
        backfill = build_backfill_files()
        seed_plan = session.query(CompactPlan).filter(CompactPlan.note == SEED_PLAN_NOTE).first()

        if seed_plan is None:
            # --- first run: build the full scene ---
            for cfg in TABLE_CATALOGUE:
                table = tables[cfg["key"]]
                for partition_value, files in catalogue[cfg["key"]].items():
                    _insert_files(session, table, files)

            ods_cfg = next(cfg for cfg in TABLE_CATALOGUE if cfg["key"] == "ods_events")
            ods_table = tables["ods_events"]

            snapshot_service.create_snapshot(
                session,
                ods_table,
                created_by=users["engineer"].id,
                note="基线快照 v1：合并前 manifest",
            )

            hist_files = [
                item
                for item in catalogue["ods_events"][HIST_PARTITION]
                if item["size_bytes"] < ods_cfg["small_file_threshold_mb"] * 1024 * 1024
            ]
            result = _build_historical_plan(ods_cfg, hist_files)
            plan = CompactPlan(
                table_id=ods_table.id,
                strategy=result["strategy"],
                status=PlanStatus.EXECUTING.value,
                partition_values=[HIST_PARTITION],
                groups=result["groups"],
                risk_flags=result["risk_flags"],
                cost=result["cost"],
                candidate_file_count=result["candidate_file_count"],
                group_count=result["group_count"],
                expected_output_files=result["expected_output_files"],
                rewritten_bytes=result["rewritten_bytes"],
                est_duration_seconds=float(result["cost"]["est_duration_seconds"]),
                est_cost_yuan=float(result["cost"]["est_cost_yuan"]),
                savings_pct=float(result["savings_pct"]),
                fingerprint=result["fingerprint"],
                note=SEED_PLAN_NOTE,
                created_by=users["engineer"].id,
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)

            metrics = _apply_merge(session, ods_table, plan)

            job = CompactJob(
                plan_id=plan.id,
                table_id=ods_table.id,
                status="succeeded",
                progress=100,
                groups_total=result["group_count"],
                processed_groups=result["group_count"],
                rewritten_files=metrics["rewritten_files"],
                produced_files=metrics["produced_files"],
                bytes_written=metrics["bytes_written"],
                rows_before=metrics["rows_before"],
                rows_after=metrics["rows_after"],
                triggered_by=users["engineer"].id,
            )
            session.add(job)
            session.commit()
            session.refresh(job)

            snapshot_v2 = snapshot_service.create_snapshot(
                session,
                ods_table,
                created_by=users["engineer"].id,
                note=f"合并后快照 v2：dt={HIST_PARTITION} 小文件合并（任务 #{job.id}）",
                job_id=job.id,
            )
            job.snapshot_id = snapshot_v2.id
            plan.status = PlanStatus.COMPLETED.value
            session.commit()

            snapshot_service.create_snapshot(
                session,
                tables["dwd_orders"],
                created_by=users["engineer"].id,
                note="订单宽表基线快照 v1",
            )

            # 快照之后迟到的 backfill 文件：不被保留快照引用，成为退役回收候选
            for cfg in TABLE_CATALOGUE:
                late_files = backfill.get(cfg["key"], [])
                if late_files:
                    _insert_files(session, tables[cfg["key"]], late_files)

            log_event("SEED_DEMO_CREATED", plan_id=plan.id, job_id=job.id)
        else:
            # --- repeat run: converge to the same post-merge state ---
            _ensure_desired_files(session, tables, catalogue, seed_plan, backfill)

        for cfg in TABLE_CATALOGUE:
            partition_service.recompute_table(session, tables[cfg["key"]])

        summary = _counts(session)
        print("SEED_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
        log_event("SEED_DEMO_SUMMARY", **summary)
        return summary
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    run_seed()
