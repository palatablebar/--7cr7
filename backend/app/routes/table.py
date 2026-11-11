from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import file_controller, table_controller
from app.middlewares.auth import get_current_user
from app.middlewares.rbac import require_roles
from app.models import User
from app.schemas.table import LakeTableCreate, LakeTableUpdate

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("")
def list_tables(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return table_controller.list_tables(db)


@router.post("")
def create_table(
    payload: LakeTableCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    return table_controller.create_table(db, payload, request, user)


@router.get("/{table_id}")
def get_table(table_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return table_controller.get_table(db, table_id)


@router.patch("/{table_id}")
def update_table(
    table_id: int,
    payload: LakeTableUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    return table_controller.update_table(db, table_id, payload, request)


@router.get("/{table_id}/partitions")
def list_partitions(table_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return table_controller.list_partitions(db, table_id)


@router.get("/{table_id}/files")
def list_files(
    table_id: int,
    partition_value: str | None = None,
    size_lt_mb: float | None = None,
    size_gte_mb: float | None = None,
    sort: str = "size_desc",
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return file_controller.list_files(
        db,
        table_id,
        partition_value=partition_value,
        size_lt_mb=size_lt_mb,
        size_gte_mb=size_gte_mb,
        sort=sort,
        offset=offset,
        limit=limit,
    )
