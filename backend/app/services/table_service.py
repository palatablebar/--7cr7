"""Lake table CRUD + roll-up summaries used by the overview page."""
from sqlalchemy.orm import Session

from app.constants.error_codes import AppError, ErrorCode
from app.constants.file_format import TableStatus
from app.models import CompactPlan, DataFile, LakeTable, PartitionSpec
from app.schemas.common import iso
from app.services import partition_service


def get_table_or_404(db: Session, table_id: int) -> LakeTable:
    table = db.get(LakeTable, table_id)
    if table is None:
        raise AppError(ErrorCode.TABLE_NOT_FOUND)
    return table


def _specs(db: Session, table: LakeTable) -> list[PartitionSpec]:
    return (
        db.query(PartitionSpec)
        .filter(PartitionSpec.table_id == table.id)
        .order_by(PartitionSpec.partition_value.desc())
        .all()
    )


def table_summary(db: Session, table: LakeTable, specs: list[PartitionSpec] | None = None) -> dict:
    specs = specs if specs is not None else _specs(db, table)
    # 退役冻结/已退役的分区（含 0 文件墓碑）不参与健康度与文件数聚合
    active_specs = [s for s in specs if s.lifecycle == "active"]
    threshold_bytes = int(table.small_file_threshold_mb) * 1024 * 1024
    file_count = sum(s.file_count for s in active_specs)
    small_count = sum(s.small_file_count for s in active_specs)
    total_size = sum(s.total_size_bytes for s in active_specs)
    scores = [s.health_score for s in active_specs]
    avg_health = int(round(sum(scores) / len(scores))) if scores else 0
    small_file_rows = (
        db.query(DataFile).filter(DataFile.table_id == table.id, DataFile.size_bytes < threshold_bytes).all()
    )
    reclaimable = sum(max(0, s.small_file_count - 1) for s in active_specs)
    latest_plan = (
        db.query(CompactPlan)
        .filter(CompactPlan.table_id == table.id)
        .order_by(CompactPlan.id.desc())
        .first()
    )
    return {
        "partition_count": len(active_specs),
        "file_count": file_count,
        "small_file_count": small_count,
        "total_size_bytes": total_size,
        "avg_file_size_bytes": int(total_size / file_count) if file_count else 0,
        "avg_health_score": avg_health,
        "avg_health_band": _band(avg_health),
        "hot_partition_count": sum(1 for s in active_specs if s.risk == "hot"),
        "pending_partition_count": sum(1 for s in active_specs if s.small_file_count > 0),
        "retiring_partition_count": sum(1 for s in specs if s.lifecycle == "retiring"),
        "retired_partition_count": sum(1 for s in specs if s.lifecycle == "retired"),
        "reclaimable_file_count": reclaimable,
        "small_file_bytes": sum(int(f.size_bytes) for f in small_file_rows),
        "latest_plan_id": latest_plan.id if latest_plan else None,
        "latest_plan_status": latest_plan.status if latest_plan else None,
    }


def _band(score: int) -> str:
    from app.constants.health_band import band_for

    return band_for(score)


def serialize_table(db: Session, table: LakeTable, specs: list[PartitionSpec] | None = None) -> dict:
    specs = specs if specs is not None else _specs(db, table)
    summary = table_summary(db, table, specs)
    return {
        "id": table.id,
        "db_name": table.db_name,
        "table_name": table.table_name,
        "fq_name": table.fq_name,
        "partition_key": table.partition_key,
        "file_format": table.file_format,
        "target_file_size_mb": table.target_file_size_mb,
        "small_file_threshold_mb": table.small_file_threshold_mb,
        "status": table.status,
        "description": table.description,
        "owner_name": table.owner_name,
        "created_at": iso(table.created_at),
        "partitions": [
            {
                "id": spec.id,
                "partition_value": spec.partition_value,
                "file_count": spec.file_count,
                "small_file_count": spec.small_file_count,
                "health_score": spec.health_score,
                "health_band": spec.health_band,
                "risk": spec.risk,
                "lifecycle": spec.lifecycle,
            }
            for spec in sorted(specs, key=lambda item: item.partition_value)
            if spec.lifecycle == "active"
        ],
        **summary,
    }


def list_tables(db: Session) -> dict:
    tables = db.query(LakeTable).order_by(LakeTable.db_name, LakeTable.table_name).all()
    items = []
    for table in tables:
        partition_service.recompute_table(db, table, commit=False)
    db.commit()
    for table in tables:
        items.append(serialize_table(db, table))

    summary = {
        "table_count": len(items),
        "file_count": sum(i["file_count"] for i in items),
        "small_file_count": sum(i["small_file_count"] for i in items),
        "total_size_bytes": sum(i["total_size_bytes"] for i in items),
        "pending_partition_count": sum(i["pending_partition_count"] for i in items),
        "hot_partition_count": sum(i["hot_partition_count"] for i in items),
        "reclaimable_file_count": sum(i["reclaimable_file_count"] for i in items),
        "avg_health_score": int(round(sum(i["avg_health_score"] for i in items) / len(items))) if items else 0,
    }
    return {"items": items, "summary": summary}


def create_table(db: Session, payload) -> LakeTable:
    exists = (
        db.query(LakeTable)
        .filter(LakeTable.db_name == payload.db_name, LakeTable.table_name == payload.table_name)
        .first()
    )
    if exists is not None:
        raise AppError(ErrorCode.TABLE_DUPLICATE, detail={"table_id": exists.id})
    table = LakeTable(
        db_name=payload.db_name,
        table_name=payload.table_name,
        partition_key=payload.partition_key,
        file_format=payload.file_format,
        target_file_size_mb=payload.target_file_size_mb,
        small_file_threshold_mb=payload.small_file_threshold_mb,
        status=TableStatus.ACTIVE.value,
        description=payload.description,
        owner_name=None,
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    partition_service.recompute_table(db, table)
    return table


def update_table(db: Session, table: LakeTable, payload) -> LakeTable:
    before = {
        "target_file_size_mb": table.target_file_size_mb,
        "small_file_threshold_mb": table.small_file_threshold_mb,
        "status": table.status,
        "description": table.description,
    }
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is not None:
            setattr(table, field, value)
    db.commit()
    db.refresh(table)
    partition_service.recompute_table(db, table)
    table._before_snapshot = before  # consumed by the controller for the audit row
    return table
