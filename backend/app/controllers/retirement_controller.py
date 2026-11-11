from fastapi import Request
from sqlalchemy.orm import Session

from app.middlewares import audit_logger
from app.models import User
from app.services import retirement_service, table_service


def reclaim_manifest(db: Session, table_id: int) -> dict:
    table = table_service.get_table_or_404(db, table_id)
    return retirement_service.reclaim_preview(db, table)


def list_retirements(db: Session, table_id: int) -> dict:
    table = table_service.get_table_or_404(db, table_id)
    return {"items": retirement_service.list_retirements(db, table.id)}


def get_retirement(db: Session, retirement_id: int) -> dict:
    retirement = retirement_service.get_retirement_or_404(db, retirement_id)
    return {"retirement": retirement_service.serialize_retirement(db, retirement)}


def create_retirement(db: Session, table_id: int, payload, request: Request, user: User) -> dict:
    table = table_service.get_table_or_404(db, table_id)
    result = retirement_service.create_retirement(db, user, table, payload)
    retirement = result["retirement"]
    audit_logger.record(
        request,
        "retirement.created",
        "partition_retirement",
        retirement["id"],
        after={
            "table_id": table.id,
            "partitions": retirement["partition_values"],
            "protected": retirement["protected_file_count"],
            "reclaimable": retirement["reclaimable_file_count"],
            "fingerprint": retirement["fingerprint"],
            "idempotent": result["idempotent"],
        },
    )
    return result


def execute_retirement(db: Session, retirement_id: int, payload, request: Request, user: User) -> dict:
    result = retirement_service.execute_retirement(
        db, user, retirement_id, simulate_failure=bool(getattr(payload, "simulate_failure", False))
    )
    retirement = result["retirement"]
    audit_logger.record(
        request,
        "retirement.executed",
        "partition_retirement",
        retirement["id"],
        after={
            "status": retirement["status"],
            "ok": result["ok"],
            "idempotent": result["idempotent"],
            "reclaimed": (retirement.get("result") or {}).get("reclaimed_file_count"),
        },
    )
    return result


def restore_retirement(db: Session, retirement_id: int, request: Request, user: User) -> dict:
    result = retirement_service.restore_retirement(db, user, retirement_id)
    retirement = result["retirement"]
    audit_logger.record(
        request,
        "retirement.restored",
        "partition_retirement",
        retirement["id"],
        after={"status": retirement["status"], "idempotent": result["idempotent"]},
    )
    return result
