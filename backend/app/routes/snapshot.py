from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import snapshot_controller
from app.middlewares.auth import get_current_user
from app.middlewares.rbac import require_roles
from app.models import User
from app.schemas.snapshot import SnapshotCreateRequest

router = APIRouter(tags=["snapshots"])


@router.get("/tables/{table_id}/snapshots")
def list_snapshots(table_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return snapshot_controller.list_snapshots(db, table_id)


@router.post("/tables/{table_id}/snapshots")
def create_snapshot(
    table_id: int,
    payload: SnapshotCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "engineer")),
):
    return snapshot_controller.create_snapshot(db, table_id, payload, request, user)


@router.get("/snapshots/diff")
def diff_snapshots(
    left_id: int,
    right_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return snapshot_controller.diff_snapshots(db, left_id, right_id)
