from pydantic import BaseModel


class FileOut(BaseModel):
    id: int
    path: str
    partition_value: str
    size_bytes: int
    row_count: int
    checksum: str
    file_format: str
    write_source: str
    created_at: str | None = None
