from sqlalchemy.orm import Session

from app.models import LakeTable
from app.services import file_service, table_service


def list_files(
    db: Session,
    table_id: int,
    *,
    partition_value: str | None = None,
    size_lt_mb: float | None = None,
    size_gte_mb: float | None = None,
    sort: str = "size_desc",
    offset: int = 0,
    limit: int = 100,
) -> dict:
    table: LakeTable = table_service.get_table_or_404(db, table_id)
    return file_service.list_files(
        db,
        table,
        partition_value=partition_value,
        size_lt_mb=size_lt_mb,
        size_gte_mb=size_gte_mb,
        sort=sort,
        offset=offset,
        limit=limit,
    )
