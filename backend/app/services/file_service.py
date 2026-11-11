"""DataFile browsing with the filters the blueprint table needs."""
from sqlalchemy.orm import Session

from app.models import DataFile, LakeTable
from app.schemas.common import iso
from app.utils.formatting import mb
from app.utils.pagination import paginate

SORT_OPTIONS = {
    "size_desc": (DataFile.size_bytes.desc(), DataFile.path.asc()),
    "size_asc": (DataFile.size_bytes.asc(), DataFile.path.asc()),
    "rows_desc": (DataFile.row_count.desc(), DataFile.path.asc()),
    "path_asc": (DataFile.path.asc(),),
    "partition_desc": (DataFile.partition_value.desc(), DataFile.size_bytes.desc()),
}


def list_files(
    db: Session,
    table: LakeTable,
    *,
    partition_value: str | None = None,
    size_lt_mb: float | None = None,
    size_gte_mb: float | None = None,
    sort: str = "size_desc",
    offset: int = 0,
    limit: int = 100,
) -> dict:
    query = db.query(DataFile).filter(DataFile.table_id == table.id)
    if partition_value:
        query = query.filter(DataFile.partition_value == partition_value)
    if size_lt_mb is not None:
        query = query.filter(DataFile.size_bytes < int(float(size_lt_mb) * 1024 * 1024))
    if size_gte_mb is not None:
        query = query.filter(DataFile.size_bytes >= int(float(size_gte_mb) * 1024 * 1024))
    order = SORT_OPTIONS.get(sort, SORT_OPTIONS["size_desc"])
    rows = query.order_by(*order).all()
    serialized = [serialize_file(row, table) for row in rows]
    result = paginate(serialized, offset=offset, limit=limit)
    return result


def serialize_file(row: DataFile, table: LakeTable) -> dict:
    is_small = int(row.size_bytes) < int(table.small_file_threshold_mb) * 1024 * 1024
    return {
        "id": row.id,
        "path": row.path,
        "file_name": row.path.rsplit("/", 1)[-1],
        "partition_value": row.partition_value,
        "size_bytes": int(row.size_bytes),
        "size_mb": mb(row.size_bytes),
        "row_count": int(row.row_count),
        "checksum": row.checksum,
        "file_format": row.file_format,
        "write_source": row.write_source,
        "is_small": is_small,
        "created_at": iso(row.created_at),
    }
