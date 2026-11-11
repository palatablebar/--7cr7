from fastapi import Request
from sqlalchemy.orm import Session

from app.middlewares import audit_logger
from app.models import User
from app.services import snapshot_service, table_service


def list_snapshots(db: Session, table_id: int) -> dict:
    table = table_service.get_table_or_404(db, table_id)
    return {"items": snapshot_service.list_snapshots(db, table.id)}


def create_snapshot(db: Session, table_id: int, payload, request: Request, user: User) -> dict:
    table = table_service.get_table_or_404(db, table_id)
    snapshot = snapshot_service.create_snapshot(
        db, table, created_by=user.id, note=payload.note or "手工创建快照"
    )
    audit_logger.record(
        request,
        "snapshot.created",
        "table_snapshot",
        snapshot.id,
        after={"table_id": table.id, "version": snapshot.version, "checksum": snapshot.checksum},
    )
    return {"snapshot": snapshot_service.serialize_snapshot(db, snapshot)}


def diff_snapshots(db: Session, left_id: int, right_id: int) -> dict:
    return snapshot_service.diff_snapshots(db, left_id, right_id)
