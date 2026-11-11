from fastapi import Request
from sqlalchemy.orm import Session

from app.middlewares import audit_logger
from app.models import User
from app.services import plan_service


def create_plan(db: Session, payload, request: Request, user: User) -> dict:
    result = plan_service.create_plan(db, user, payload)
    plan = result["plan"]
    audit_logger.record(
        request,
        "plan.created",
        "compact_plan",
        plan["id"],
        after={
            "table_id": plan["table_id"],
            "partitions": plan["partition_values"],
            "groups": plan["group_count"],
            "fingerprint": plan["fingerprint"],
            "idempotent": result["idempotent"],
        },
    )
    return result


def list_plans(db: Session, table_id: int | None = None) -> dict:
    return {"items": plan_service.list_plans(db, table_id)}


def get_plan(db: Session, plan_id: int) -> dict:
    plan = plan_service.get_plan_or_404(db, plan_id)
    return {"plan": plan_service.serialize_plan(db, plan, include_groups=True)}


def execute_plan(db: Session, plan_id: int, request: Request, user: User) -> dict:
    job = plan_service.execute_plan(db, user, plan_id)
    audit_logger.record(
        request,
        "plan.executed",
        "compact_job",
        job["id"],
        after={"plan_id": plan_id, "status": job["status"]},
    )
    return {"job": job}
