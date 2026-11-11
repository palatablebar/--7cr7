from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import audit_controller
from app.middlewares.rbac import require_roles
from app.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/recent")
def recent(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    return audit_controller.recent(db, limit)
