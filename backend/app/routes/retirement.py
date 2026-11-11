from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import retirement_controller
from app.middlewares.auth import get_current_user
from app.middlewares.rbac import require_roles
from app.models import User
from app.schemas.retirement import RetirementCreateRequest, RetirementExecuteRequest

router = APIRouter(tags=["retirements"])


@router.get("/tables/{table_id}/reclaim-manifest")
def reclaim_manifest(table_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return retirement_controller.reclaim_manifest(db, table_id)


@router.get("/tables/{table_id}/retirements")
def list_retirements(table_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return retirement_controller.list_retirements(db, table_id)


@router.post("/tables/{table_id}/retirements")
def create_retirement(
    table_id: int,
    payload: RetirementCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "engineer")),
):
    return retirement_controller.create_retirement(db, table_id, payload, request, user)


@router.get("/retirements/{retirement_id}")
def get_retirement(retirement_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return retirement_controller.get_retirement(db, retirement_id)


@router.post("/retirements/{retirement_id}/execute")
def execute_retirement(
    retirement_id: int,
    request: Request,
    payload: RetirementExecuteRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "engineer")),
):
    return retirement_controller.execute_retirement(db, retirement_id, payload, request, user)


@router.post("/retirements/{retirement_id}/restore")
def restore_retirement(
    retirement_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "engineer")),
):
    return retirement_controller.restore_retirement(db, retirement_id, request, user)
