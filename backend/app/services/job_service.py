"""Compact job read model + lifecycle transitions used by the API and worker."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.constants.error_codes import AppError, ErrorCode
from app.models import CompactJob, CompactPlan, LakeTable, User
from app.schemas.common import iso


def get_job_or_404(db: Session, job_id: int) -> CompactJob:
    job = db.get(CompactJob, job_id)
    if job is None:
        raise AppError(ErrorCode.JOB_NOT_FOUND)
    return job


def serialize_job(db: Session, job: CompactJob) -> dict:
    plan = db.get(CompactPlan, job.plan_id)
    table = db.get(LakeTable, job.table_id)
    trigger_user = db.get(User, job.triggered_by) if job.triggered_by else None
    return {
        "id": job.id,
        "plan_id": job.plan_id,
        "table_id": job.table_id,
        "table_fq_name": table.fq_name if table else None,
        "partition_values": (plan.partition_values or []) if plan else [],
        "strategy": plan.strategy if plan else None,
        "fingerprint": plan.fingerprint if plan else None,
        "status": job.status,
        "progress": int(job.progress or 0),
        "groups_total": int(job.groups_total or 0),
        "processed_groups": int(job.processed_groups or 0),
        "rewritten_files": int(job.rewritten_files or 0),
        "produced_files": int(job.produced_files or 0),
        "bytes_written": int(job.bytes_written or 0),
        "rows_before": int(job.rows_before or 0),
        "rows_after": int(job.rows_after or 0),
        "row_conserved": int(job.rows_before or 0) == int(job.rows_after or 0),
        "snapshot_id": job.snapshot_id,
        "celery_task_id": job.celery_task_id,
        "failure_reason": job.failure_reason,
        "triggered_by": job.triggered_by,
        "triggered_by_name": trigger_user.display_name if trigger_user else None,
        "started_at": iso(job.started_at),
        "finished_at": iso(job.finished_at),
        "created_at": iso(job.created_at),
        "est_duration_seconds": float(plan.est_duration_seconds) if plan else None,
    }


def list_jobs(db: Session, table_id: int | None = None, limit: int = 30) -> list[dict]:
    query = db.query(CompactJob).order_by(CompactJob.id.desc())
    if table_id:
        query = query.filter(CompactJob.table_id == table_id)
    return [serialize_job(db, job) for job in query.limit(limit).all()]


def mark_running(db: Session, job: CompactJob) -> None:
    job.status = "running"
    job.started_at = datetime.now()
    job.progress = max(1, int(job.progress or 0))
    db.commit()


def update_progress(
    db: Session,
    job: CompactJob,
    *,
    progress: int,
    processed_groups: int,
    rewritten_files: int,
    produced_files: int,
    bytes_written: int,
    rows_before: int,
    rows_after: int,
) -> None:
    job.progress = max(0, min(100, int(progress)))
    job.processed_groups = processed_groups
    job.rewritten_files = rewritten_files
    job.produced_files = produced_files
    job.bytes_written = bytes_written
    job.rows_before = rows_before
    job.rows_after = rows_after
    db.commit()


def mark_succeeded(db: Session, job: CompactJob, snapshot_id: int | None) -> None:
    job.status = "succeeded"
    job.progress = 100
    job.snapshot_id = snapshot_id
    job.finished_at = datetime.now()
    plan = db.get(CompactPlan, job.plan_id)
    if plan is not None:
        plan.status = "completed"
    db.commit()


def mark_failed(db: Session, job: CompactJob, reason: str) -> None:
    job.status = "failed"
    job.failure_reason = reason[:900]
    job.finished_at = datetime.now()
    plan = db.get(CompactPlan, job.plan_id)
    if plan is not None:
        plan.status = "failed"
    db.commit()
