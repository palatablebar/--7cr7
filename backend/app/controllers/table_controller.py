from fastapi import Request
from sqlalchemy.orm import Session

from app.middlewares import audit_logger
from app.models import User
from app.services import partition_service, table_service


def list_tables(db: Session) -> dict:
    return table_service.list_tables(db)


def get_table(db: Session, table_id: int) -> dict:
    table = table_service.get_table_or_404(db, table_id)
    partition_service.recompute_table(db, table)
    return {
        "table": table_service.serialize_table(db, table),
        "partitions": partition_service.list_partitions(db, table),
    }


def create_table(db: Session, payload, request: Request, user: User) -> dict:
    table = table_service.create_table(db, payload)
    audit_logger.record(
        request,
        "table.created",
        "lake_table",
        table.id,
        after={"fq_name": table.fq_name, "target_file_size_mb": table.target_file_size_mb},
    )
    return {"table": table_service.serialize_table(db, table)}


def update_table(db: Session, table_id: int, payload, request: Request) -> dict:
    table = table_service.get_table_or_404(db, table_id)
    table = table_service.update_table(db, table, payload)
    audit_logger.record(
        request,
        "table.updated",
        "lake_table",
        table.id,
        before=getattr(table, "_before_snapshot", None),
        after={"target_file_size_mb": table.target_file_size_mb, "status": table.status},
    )
    return {"table": table_service.serialize_table(db, table)}


def list_partitions(db: Session, table_id: int) -> dict:
    table = table_service.get_table_or_404(db, table_id)
    return {"items": partition_service.list_partitions(db, table)}

