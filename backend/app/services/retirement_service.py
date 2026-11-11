"""Partition retirement — snapshot-guarded reclamation.

回收清单（reclaim manifest）：对每个分区，把当前文件分成两类——
  * protected  ：仍被保留快照（table_snapshots 中现存的任意版本）manifest 引用的文件，不删；
  * reclaimable：未被任何保留快照引用的文件，可随退役一次性清理。
不变式：protected_count + reclaimable_count == 分区文件总数（生成与序列化时都会校验）。

退役语义：
  * 生成退役单时先把分区 lifecycle 置为 retiring —— 停止新合并（见
    partition_service.assert_partitions_mergeable，计划生成/执行都会检查）；
  * execute 在**单个数据库事务**内删除全部选中分区的可回收文件：要么整批
    提交，要么整体回滚 —— 不会出现"分区只剩一部分"的中间态；
  * 执行失败 -> 状态 failed，文件原样保留，restore 可把分区解冻回 active；
  * 重复执行已 retired 的退役单 -> 直接返回既有结果（idempotent），不重复清理；
  * 相同指纹（同表、同分区、同清单）重复创建 -> 返回已有退役单（idempotent）。
"""
import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.constants.error_codes import AppError, ErrorCode
from app.constants.partition_lifecycle import PartitionLifecycle
from app.constants.retirement_status import RetirementStatus
from app.middlewares.quota import acquire_table_lock, release_table_lock
from app.models import DataFile, LakeTable, PartitionRetirement, PartitionSpec, TableSnapshot, User
from app.schemas.common import iso
from app.services import partition_service, table_service
from app.utils.logger import log_event

MAX_MANIFEST_FILES = 500  # per-partition file lists are capped in payloads; counts stay exact


# ---------------------------------------------------------------------------
# reclaim manifest (回收清单)
# ---------------------------------------------------------------------------

def protected_path_refs(db: Session, table_id: int) -> dict[str, list[int]]:
    """path -> sorted snapshot versions that still reference it (retained snapshots)."""
    refs: dict[str, set[int]] = {}
    snapshots = (
        db.query(TableSnapshot)
        .filter(TableSnapshot.table_id == table_id)
        .order_by(TableSnapshot.version.asc())
        .all()
    )
    for snapshot in snapshots:
        for path in (snapshot.manifest or {}).keys():
            refs.setdefault(path, set()).add(int(snapshot.version))
    return {path: sorted(versions) for path, versions in refs.items()}


def build_reclaim_manifest(db: Session, table: LakeTable, partition_values: list[str] | None = None) -> list[dict]:
    """Per-partition protected/reclaimable split against retained snapshots."""
    refs = protected_path_refs(db, table.id)
    query = db.query(DataFile).filter(DataFile.table_id == table.id)
    if partition_values:
        query = query.filter(DataFile.partition_value.in_(list(partition_values)))
    rows = query.order_by(DataFile.partition_value.asc(), DataFile.path.asc()).all()

    specs = {
        spec.partition_value: spec
        for spec in db.query(PartitionSpec).filter(PartitionSpec.table_id == table.id).all()
    }
    grouped: dict[str, list[DataFile]] = {}
    for row in rows:
        grouped.setdefault(row.partition_value, []).append(row)

    items: list[dict] = []
    for partition_value in sorted(grouped):
        files = grouped[partition_value]
        protected_files: list[dict] = []
        reclaimable_files: list[dict] = []
        protected_bytes = 0
        reclaimable_bytes = 0
        for row in files:
            entry = {
                "path": row.path,
                "size_bytes": int(row.size_bytes),
                "row_count": int(row.row_count),
                "checksum": row.checksum,
            }
            versions = refs.get(row.path)
            if versions:
                entry["snapshot_versions"] = versions
                protected_files.append(entry)
                protected_bytes += int(row.size_bytes)
            else:
                reclaimable_files.append(entry)
                reclaimable_bytes += int(row.size_bytes)
        file_count = len(files)
        items.append(
            {
                "partition_value": partition_value,
                "lifecycle": specs[partition_value].lifecycle if partition_value in specs else PartitionLifecycle.ACTIVE.value,
                "file_count": file_count,
                "protected_count": len(protected_files),
                "reclaimable_count": len(reclaimable_files),
                "protected_bytes": protected_bytes,
                "reclaimable_bytes": reclaimable_bytes,
                # 引用数 + 可回收数 == 分区文件总数（逐分区不变式）
                "invariant_ok": len(protected_files) + len(reclaimable_files) == file_count,
                "protected_files": protected_files[:MAX_MANIFEST_FILES],
                "reclaimable_files": reclaimable_files[:MAX_MANIFEST_FILES],
                "files_truncated": max(len(protected_files), len(reclaimable_files)) > MAX_MANIFEST_FILES,
            }
        )
    return items


def reclaim_preview(db: Session, table: LakeTable) -> dict:
    """Read-only 回收清单 for the retirement page."""
    partition_service.recompute_table(db, table)
    items = build_reclaim_manifest(db, table)
    versions = [
        int(row.version)
        for row in db.query(TableSnapshot).filter(TableSnapshot.table_id == table.id)
        .order_by(TableSnapshot.version.asc()).all()
    ]
    totals = {
        "file_count": sum(item["file_count"] for item in items),
        "protected_count": sum(item["protected_count"] for item in items),
        "reclaimable_count": sum(item["reclaimable_count"] for item in items),
        "protected_bytes": sum(item["protected_bytes"] for item in items),
        "reclaimable_bytes": sum(item["reclaimable_bytes"] for item in items),
    }
    totals["invariant_ok"] = totals["protected_count"] + totals["reclaimable_count"] == totals["file_count"]
    return {
        "table_id": table.id,
        "table_fq_name": table.fq_name,
        "partition_key": table.partition_key,
        "retained_snapshot_versions": versions,
        "snapshot_count": len(versions),
        "items": items,
        "totals": totals,
    }


# ---------------------------------------------------------------------------
# retirement order lifecycle
# ---------------------------------------------------------------------------

def _fingerprint(table: LakeTable, items: list[dict]) -> str:
    canonical = {
        "table_id": table.id,
        "strategy": "snapshot_guarded_retire_v1",
        "partitions": [
            [
                item["partition_value"],
                sorted(f["path"] for f in item["protected_files"]),
                sorted(f["path"] for f in item["reclaimable_files"]),
            ]
            for item in items
        ],
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def get_retirement_or_404(db: Session, retirement_id: int) -> PartitionRetirement:
    retirement = db.get(PartitionRetirement, retirement_id)
    if retirement is None:
        raise AppError(ErrorCode.RETIREMENT_NOT_FOUND)
    return retirement


def create_retirement(db: Session, user: User, table: LakeTable, payload) -> dict:
    """Freeze the selected partitions and persist their reclaim manifest."""
    partitions = sorted({str(value).strip() for value in payload.partition_values if str(value).strip()})
    if not partitions:
        raise AppError(ErrorCode.PLAN_PARTITIONS_INVALID, message="请至少选择一个分区")

    partition_service.recompute_table(db, table)
    specs = (
        db.query(PartitionSpec)
        .filter(PartitionSpec.table_id == table.id, PartitionSpec.partition_value.in_(partitions))
        .all()
    )
    found = {spec.partition_value for spec in specs}
    missing = [value for value in partitions if value not in found]
    if missing:
        raise AppError(ErrorCode.PARTITION_NOT_FOUND, detail={"missing": missing})

    items = build_reclaim_manifest(db, table, partitions)
    if not items or all(item["file_count"] == 0 for item in items):
        raise AppError(ErrorCode.PARTITION_NOT_FOUND, message="所选分区没有可退役的文件")
    fingerprint = _fingerprint(table, items)

    previous = (
        db.query(PartitionRetirement)
        .filter(
            PartitionRetirement.table_id == table.id,
            PartitionRetirement.fingerprint == fingerprint,
            PartitionRetirement.status.in_([RetirementStatus.RETIRING.value, RetirementStatus.RETIRED.value]),
        )
        .order_by(PartitionRetirement.id.desc())
        .first()
    )
    if previous is not None:
        # 相同清单的退役单仍在生效：不重复冻结、不重复清理
        return {"retirement": serialize_retirement(db, previous), "idempotent": True}

    # 已冻结/已退役的分区拒绝纳入新的退役单
    partition_service.assert_partitions_mergeable(db, table, partitions)

    retirement = PartitionRetirement(
        table_id=table.id,
        status=RetirementStatus.RETIRING.value,
        partition_values=[item["partition_value"] for item in items],
        items=items,
        protected_file_count=sum(item["protected_count"] for item in items),
        reclaimable_file_count=sum(item["reclaimable_count"] for item in items),
        reclaimable_bytes=sum(item["reclaimable_bytes"] for item in items),
        fingerprint=fingerprint,
        note=payload.note,
        created_by=user.id,
    )
    db.add(retirement)
    # 先停止新合并：冻结选中分区
    for spec in specs:
        spec.lifecycle = PartitionLifecycle.RETIRING.value
        spec.updated_at = datetime.now()
    db.commit()
    db.refresh(retirement)
    log_event(
        "RETIREMENT_CREATED",
        retirement_id=retirement.id,
        table=table.fq_name,
        partitions=retirement.partition_values,
        reclaimable=retirement.reclaimable_file_count,
        protected=retirement.protected_file_count,
    )
    return {"retirement": serialize_retirement(db, retirement), "idempotent": False}


def execute_retirement(db: Session, user: User, retirement_id: int, *, simulate_failure: bool = False) -> dict:
    """One-shot atomic retire: delete every reclaimable file of every selected
    partition in a single transaction. Any failure rolls the whole batch back,
    so a partition never ends up half-cleaned."""
    retirement = get_retirement_or_404(db, retirement_id)
    if retirement.status == RetirementStatus.RETIRED.value:
        # 重复执行不重复清理：直接返回首次执行的结果
        return {"retirement": serialize_retirement(db, retirement), "idempotent": True, "ok": True}
    if retirement.status != RetirementStatus.RETIRING.value:
        raise AppError(
            ErrorCode.RETIREMENT_STATE_INVALID,
            message="只有「已冻结·待执行」的退役单可以执行；失败单请先恢复原分区",
            detail={"status": retirement.status},
        )

    table = table_service.get_table_or_404(db, retirement.table_id)
    if not acquire_table_lock(table.id):
        raise AppError(ErrorCode.JOB_LOCKED, detail={"table_id": table.id})

    now = datetime.now()
    try:
        # 删除前重新计算保留快照引用：清单生成后新建的快照可能已引用待删文件
        refs = protected_path_refs(db, table.id)
        partition_results: list[dict] = []
        reclaimed_paths: list[str] = []
        total_reclaimed = 0
        total_bytes = 0
        for item in retirement.items or []:
            reclaimed = 0
            reclaimed_bytes = 0
            skipped_protected: list[str] = []
            missing: list[str] = []
            for file_entry in item.get("reclaimable_files", []):
                path = file_entry["path"]
                if path in refs:
                    skipped_protected.append(path)
                    continue
                row = (
                    db.query(DataFile)
                    .filter(DataFile.table_id == table.id, DataFile.path == path)
                    .first()
                )
                if row is None:
                    missing.append(path)  # 已被合并等其它路径移除：跳过，不算失败
                    continue
                reclaimed += 1
                reclaimed_bytes += int(row.size_bytes)
                reclaimed_paths.append(path)
                db.delete(row)
            partition_results.append(
                {
                    "partition_value": item["partition_value"],
                    "reclaimed_count": reclaimed,
                    "reclaimed_bytes": reclaimed_bytes,
                    "protected_remaining": item["protected_count"] + len(skipped_protected),
                    "skipped_protected": skipped_protected,
                    "missing": missing,
                }
            )
            total_reclaimed += reclaimed
            total_bytes += reclaimed_bytes
        db.flush()
        if simulate_failure:
            # 演练开关：在提交前注入失败，验证整批回滚 —— 分区不会只剩一部分
            raise RuntimeError("simulate_failure: 演练注入的退役执行失败（事务已回滚，分区文件保持原样）")

        specs = (
            db.query(PartitionSpec)
            .filter(
                PartitionSpec.table_id == table.id,
                PartitionSpec.partition_value.in_(retirement.partition_values or []),
            )
            .all()
        )
        for spec in specs:
            spec.lifecycle = PartitionLifecycle.RETIRED.value
            spec.updated_at = now
        partition_service.recompute_table(db, table, commit=False)

        retirement.status = RetirementStatus.RETIRED.value
        retirement.executed_at = now
        retirement.finished_at = now
        retirement.result = {
            "ok": True,
            "partitions": partition_results,
            "reclaimed_file_count": total_reclaimed,
            "reclaimed_bytes": total_bytes,
            "reclaimed_paths": reclaimed_paths[: MAX_MANIFEST_FILES * 4],
            "executed_by": user.id,
            "executed_at": iso(now),
        }
        db.commit()
        db.refresh(retirement)
    except Exception as exc:
        db.rollback()  # 一次性语义：整批回滚，分区文件保持原样
        log_event("RETIREMENT_FAILED", retirement_id=retirement_id, reason=f"{type(exc).__name__}: {exc}")
        fresh = db.get(PartitionRetirement, retirement_id)
        if fresh is not None:
            fresh.status = RetirementStatus.FAILED.value
            fresh.failure_reason = f"{type(exc).__name__}: {exc}"[:900]
            fresh.finished_at = datetime.now()
            db.commit()
            db.refresh(fresh)
        return {"retirement": serialize_retirement(db, fresh), "idempotent": False, "ok": False}
    finally:
        release_table_lock(table.id)

    log_event(
        "RETIREMENT_EXECUTED",
        retirement_id=retirement.id,
        table=table.fq_name,
        reclaimed_files=total_reclaimed,
        reclaimed_bytes=total_bytes,
    )
    return {"retirement": serialize_retirement(db, retirement), "idempotent": False, "ok": True}


def restore_retirement(db: Session, user: User, retirement_id: int) -> dict:
    """恢复原分区：解冻分区（failed / retiring 单）。执行是原子事务，失败单
    的文件从未被部分删除，因此恢复只需把分区置回 active。"""
    retirement = get_retirement_or_404(db, retirement_id)
    if retirement.status == RetirementStatus.RESTORED.value:
        return {"retirement": serialize_retirement(db, retirement), "idempotent": True}
    if retirement.status not in (RetirementStatus.RETIRING.value, RetirementStatus.FAILED.value):
        raise AppError(
            ErrorCode.RETIREMENT_STATE_INVALID,
            message="只有待执行或执行失败的退役单可以恢复；已退役的分区无法撤销",
            detail={"status": retirement.status},
        )

    table = table_service.get_table_or_404(db, retirement.table_id)
    now = datetime.now()
    specs = (
        db.query(PartitionSpec)
        .filter(
            PartitionSpec.table_id == table.id,
            PartitionSpec.partition_value.in_(retirement.partition_values or []),
        )
        .all()
    )
    restored: list[str] = []
    for spec in specs:
        if spec.lifecycle == PartitionLifecycle.RETIRING.value:
            spec.lifecycle = PartitionLifecycle.ACTIVE.value
            spec.updated_at = now
            restored.append(spec.partition_value)
    retirement.status = RetirementStatus.RESTORED.value
    retirement.finished_at = now
    retirement.result = {
        "ok": True,
        "restored_partitions": sorted(restored),
        "restored_by": user.id,
        "restored_at": iso(now),
        "previous_status": "failed" if retirement.failure_reason else "retiring",
    }
    partition_service.recompute_table(db, table, commit=False)
    db.commit()
    db.refresh(retirement)
    log_event("RETIREMENT_RESTORED", retirement_id=retirement.id, table=table.fq_name, partitions=restored)
    return {"retirement": serialize_retirement(db, retirement), "idempotent": False}


# ---------------------------------------------------------------------------
# read model
# ---------------------------------------------------------------------------

def serialize_retirement(db: Session, retirement: PartitionRetirement, *, include_items: bool = True) -> dict:
    table = db.get(LakeTable, retirement.table_id)
    creator = db.get(User, retirement.created_by) if retirement.created_by else None
    data = {
        "id": retirement.id,
        "table_id": retirement.table_id,
        "table_fq_name": table.fq_name if table else None,
        "partition_key": table.partition_key if table else "dt",
        "status": retirement.status,
        "partition_values": retirement.partition_values or [],
        "protected_file_count": int(retirement.protected_file_count or 0),
        "reclaimable_file_count": int(retirement.reclaimable_file_count or 0),
        "reclaimable_bytes": int(retirement.reclaimable_bytes or 0),
        "fingerprint": retirement.fingerprint,
        "note": retirement.note,
        "failure_reason": retirement.failure_reason,
        "result": retirement.result,
        "created_by": retirement.created_by,
        "created_by_name": creator.display_name if creator else None,
        "created_at": iso(retirement.created_at),
        "executed_at": iso(retirement.executed_at),
        "finished_at": iso(retirement.finished_at),
    }
    if include_items:
        data["items"] = retirement.items or []
    return data


def list_retirements(db: Session, table_id: int, limit: int = 40) -> list[dict]:
    rows = (
        db.query(PartitionRetirement)
        .filter(PartitionRetirement.table_id == table_id)
        .order_by(PartitionRetirement.id.desc())
        .limit(limit)
        .all()
    )
    return [serialize_retirement(db, row) for row in rows]
