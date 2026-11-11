from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import plan_controller
from app.middlewares.auth import get_current_user
from app.middlewares.rbac import require_roles
from app.models import User
from app.schemas.plan import PlanCreateRequest

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("")
def list_plans(
    table_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return plan_controller.list_plans(db, table_id)


@router.post("")
def create_plan(
    payload: PlanCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "engineer")),
):
    return plan_controller.create_plan(db, payload, request, user)


@router.get("/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return plan_controller.get_plan(db, plan_id)


@router.post("/{plan_id}/execute")
def execute_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "engineer")),
):
    return plan_controller.execute_plan(db, plan_id, request, user)
