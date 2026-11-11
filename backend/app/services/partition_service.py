"""Partition health aggregation.

health_score formula (documented in README §algorithms / health):
    utilization   = min(1, avg_file_size / target_file_size)
    fragmentation = min(1, file_count / 60)
    score         = round(100 * (0.65 * utilization + 0.35 * (1 - fragmentation)))
band = healthy (>=75) / watch (>=50) / degraded (<50)
risk = hot when the partition value equals the table's newest partition value.

lifecycle (active | retiring | retired) is owned by the retirement flow and is
never recomputed here; partitions under retirement with zero files left are
kept as tombstone rows so the retirement result stays visible.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.constants.error_codes import AppError, ErrorCode
from app.constants.health_band import FRAGMENTATION_SATURATION, band_for
from app.constants.partition_lifecycle import PartitionLifecycle
from app.constants.partition_risk import PartitionRisk
from app.models import DataFile, LakeTable, PartitionSpec
from app.schemas.common import iso


def health_score(avg_file_size_bytes: int, file_count: int, target_file_size_mb: int) -> tuple[int, str]:
    target_bytes = max(1, int(target_file_size_mb) * 1024 * 1024)
    utilization = min(1.0, (avg_file_size_bytes or 0) / target_bytes)
    fragmentation = min(1.0, (file_count or 0) / FRAGMENTATION_SATURATION)
    score = int(round(100 * (0.65 * utilization + 0.35 * (1 - fragmentation))))
    return score, band_for(score)


def recompute_table(db: Session, table: LakeTable, *, commit: bool = True) -> list[PartitionSpec]:
    """Recompute every PartitionSpec for one table from its data_files rows."""
    rows = db.query(DataFile).filter(DataFile.table_id == table.id).all()
    grouped: dict[str, list[DataFile]] = {}
    for row in rows:
        grouped.setdefault(row.partition_value, []).append(row)

    hot_value = max(grouped) if grouped else None
    existing = {spec.partition_value: spec for spec in db.query(PartitionSpec).filter(PartitionSpec.table_id == table.id)}
    threshold_bytes = int(table.small_file_threshold_mb) * 1024 * 1024
    now = datetime.now()

    for partition_value, files in grouped.items():
        spec = existing.get(partition_value)
        if spec is None:
            spec = PartitionSpec(table_id=table.id, partition_value=partition_value)
            db.add(spec)
            existing[partition_value] = spec
        file_count = len(files)
        total_size = sum(int(f.size_bytes) for f in files)
        total_rows = sum(int(f.row_count) for f in files)
        avg_size = int(total_size / file_count) if file_count else 0
        score, band = health_score(avg_size, file_count, table.target_file_size_mb)
        spec.file_count = file_count
        spec.small_file_count = sum(1 for f in files if int(f.size_bytes) < threshold_bytes)
        spec.total_size_bytes = total_size
        spec.total_rows = total_rows
        spec.avg_file_size_bytes = avg_size
        spec.health_score = score
        spec.health_band = band
        spec.risk = PartitionRisk.HOT.value if partition_value == hot_value else PartitionRisk.NORMAL.value
        spec.updated_at = now

    # partitions whose files disappeared entirely:
    #   active   -> drop the spec (should not happen outside tests)
    #   retiring/retired -> keep a zeroed tombstone so the retirement trail and
    #                       the merge gate survive the file deletion
    for partition_value, spec in list(existing.items()):
        if partition_value not in grouped and spec.id is not None:
            if spec.lifecycle and spec.lifecycle != PartitionLifecycle.ACTIVE.value:
                spec.file_count = 0
                spec.small_file_count = 0
                spec.total_size_bytes = 0
                spec.total_rows = 0
                spec.avg_file_size_bytes = 0
                spec.health_score = 0
                spec.health_band = "degraded"
                spec.risk = PartitionRisk.NORMAL.value
                spec.updated_at = now
            else:
                db.delete(spec)

    if commit:
        db.commit()
    return list(existing.values())


def list_partitions(db: Session, table: LakeTable) -> list[dict]:
    specs = recompute_table(db, table)
    specs.sort(key=lambda s: s.partition_value, reverse=True)
    return [serialize_partition(s, table) for s in specs]


def get_partition(db: Session, table: LakeTable, partition_value: str) -> PartitionSpec | None:
    return (
        db.query(PartitionSpec)
        .filter(PartitionSpec.table_id == table.id, PartitionSpec.partition_value == partition_value)
        .first()
    )


def assert_partitions_mergeable(db: Session, table: LakeTable, partition_values: list[str]) -> None:
    """Gate shared by plan creation / execution: partitions frozen by a
    retirement order (or already retired) refuse new merges (LAKE-2017)."""
    if not partition_values:
        return
    frozen = [
        spec.partition_value
        for spec in db.query(PartitionSpec)
        .filter(
            PartitionSpec.table_id == table.id,
            PartitionSpec.partition_value.in_(list(partition_values)),
            PartitionSpec.lifecycle != PartitionLifecycle.ACTIVE.value,
        )
        .all()
    ]
    if frozen:
        raise AppError(
            ErrorCode.PARTITION_RETIRING,
            detail={"partitions": sorted(frozen)},
        )


def serialize_partition(spec: PartitionSpec, table: LakeTable) -> dict:
    return {
        "id": spec.id,
        "partition_value": spec.partition_value,
        "file_count": spec.file_count,
        "small_file_count": spec.small_file_count,
        "total_size_bytes": spec.total_size_bytes,
        "total_rows": spec.total_rows,
        "avg_file_size_bytes": spec.avg_file_size_bytes,
        "health_score": spec.health_score,
        "health_band": spec.health_band,
        "risk": spec.risk,
        "lifecycle": spec.lifecycle,
        "last_compacted_at": iso(spec.last_compacted_at),
        "target_file_size_mb": table.target_file_size_mb,
    }
