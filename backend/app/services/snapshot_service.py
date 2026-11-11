"""Manifest snapshots + algorithm-2 diff / row-conservation audit."""
from sqlalchemy.orm import Session

from app.compaction.manifest import build_manifest, diff_manifests, digest
from app.constants.error_codes import AppError, ErrorCode
from app.models import DataFile, LakeTable, TableSnapshot
from app.schemas.common import iso


def manifest_for_table(db: Session, table: LakeTable) -> dict:
    rows = db.query(DataFile).filter(DataFile.table_id == table.id).all()
    files = [
        {
            "path": row.path,
            "size_bytes": int(row.size_bytes),
            "row_count": int(row.row_count),
            "checksum": row.checksum,
            "partition_value": row.partition_value,
        }
        for row in rows
    ]
    return build_manifest(files)


def latest_snapshot(db: Session, table_id: int) -> TableSnapshot | None:
    return (
        db.query(TableSnapshot)
        .filter(TableSnapshot.table_id == table_id)
        .order_by(TableSnapshot.version.desc())
        .first()
    )


def create_snapshot(
    db: Session,
    table: LakeTable,
    *,
    created_by: int | None = None,
    note: str | None = None,
    job_id: int | None = None,
) -> TableSnapshot:
    manifest = manifest_for_table(db, table)
    previous = latest_snapshot(db, table.id)
    verification = (
        diff_manifests(previous.manifest, manifest)
        if previous is not None
        else {
            "baseline": True,
            "compared_to_version": None,
            "row_conserved": True,
            "checksum_ok": True,
            "conservation_ok": True,
            "added_count": len(manifest),
            "removed_count": 0,
            "changed_count": 0,
            "rows_before": sum(int(meta.get("rows") or 0) for meta in manifest.values()),
            "rows_after": sum(int(meta.get("rows") or 0) for meta in manifest.values()),
        }
    )
    if previous is not None:
        verification["compared_to_version"] = previous.version
        verification["compared_to_id"] = previous.id

    snapshot = TableSnapshot(
        table_id=table.id,
        version=(previous.version + 1) if previous is not None else 1,
        manifest=manifest,
        file_count=len(manifest),
        total_rows=sum(int(meta.get("rows") or 0) for meta in manifest.values()),
        total_bytes=sum(int(meta.get("size_bytes") or 0) for meta in manifest.values()),
        checksum=digest(manifest),
        verification=verification,
        note=note,
        job_id=job_id,
        created_by=created_by,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_snapshot_or_404(db: Session, snapshot_id: int) -> TableSnapshot:
    snapshot = db.get(TableSnapshot, snapshot_id)
    if snapshot is None:
        raise AppError(ErrorCode.SNAPSHOT_NOT_FOUND)
    return snapshot


def serialize_snapshot(db: Session, snapshot: TableSnapshot, *, include_verification: bool = True) -> dict:
    table = db.get(LakeTable, snapshot.table_id)
    data = {
        "id": snapshot.id,
        "table_id": snapshot.table_id,
        "table_fq_name": table.fq_name if table else None,
        "version": snapshot.version,
        "file_count": snapshot.file_count,
        "total_rows": int(snapshot.total_rows),
        "total_bytes": int(snapshot.total_bytes),
        "checksum": snapshot.checksum,
        "note": snapshot.note,
        "job_id": snapshot.job_id,
        "created_at": iso(snapshot.created_at),
    }
    if include_verification:
        data["verification"] = snapshot.verification or {}
    return data


def list_snapshots(db: Session, table_id: int) -> list[dict]:
    rows = (
        db.query(TableSnapshot)
        .filter(TableSnapshot.table_id == table_id)
        .order_by(TableSnapshot.version.desc())
        .all()
    )
    return [serialize_snapshot(db, row) for row in rows]


def diff_snapshots(db: Session, left_id: int, right_id: int) -> dict:
    if left_id == right_id:
        raise AppError(ErrorCode.SNAPSHOT_DIFF_INVALID, message="请选择两个不同的快照进行对比")
    left = get_snapshot_or_404(db, left_id)
    right = get_snapshot_or_404(db, right_id)
    if left.table_id != right.table_id:
        raise AppError(ErrorCode.SNAPSHOT_DIFF_INVALID, message="只能对比同一张湖表的快照")
    diff = diff_manifests(left.manifest, right.manifest)
    return {
        "left": serialize_snapshot(db, left, include_verification=False),
        "right": serialize_snapshot(db, right, include_verification=False),
        "diff": diff,
    }
