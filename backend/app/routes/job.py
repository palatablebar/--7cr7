from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import job_controller
from app.middlewares.auth import get_current_user
from app.middlewares.rbac import require_roles
from app.models import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    table_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return job_controller.list_jobs(db, table_id)


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return job_controller.get_job(db, job_id)


@router.post("/{job_id}/retry")
def retry_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "engineer")),
):
    return job_controller.retry_job(db, job_id, request, user)
