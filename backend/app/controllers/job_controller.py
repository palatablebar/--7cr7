from fastapi import Request
from sqlalchemy.orm import Session

from app.middlewares import audit_logger
from app.models import User
from app.services import job_service, plan_service


def list_jobs(db: Session, table_id: int | None = None) -> dict:
    return {"items": job_service.list_jobs(db, table_id)}


def get_job(db: Session, job_id: int) -> dict:
    job = job_service.get_job_or_404(db, job_id)
    return {"job": job_service.serialize_job(db, job)}


def retry_job(db: Session, job_id: int, request: Request, user: User) -> dict:
    job = plan_service.retry_job(db, user, job_id)
    audit_logger.record(
        request,
        "job.retried",
        "compact_job",
        job["id"],
        after={"plan_id": job["plan_id"], "status": job["status"]},
    )
    return {"job": job}
