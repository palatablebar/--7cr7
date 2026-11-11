from pydantic import BaseModel, Field


class LakeTableCreate(BaseModel):
    db_name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    table_name: str = Field(min_length=1, max_length=96, pattern=r"^[a-z][a-z0-9_]*$")
    partition_key: str = Field(default="dt", min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_]*$")
    file_format: str = Field(default="parquet", pattern=r"^(parquet|orc)$")
    target_file_size_mb: int = Field(default=256, ge=32, le=2048)
    small_file_threshold_mb: int = Field(default=64, ge=8, le=256)
    description: str | None = None


class LakeTableUpdate(BaseModel):
    target_file_size_mb: int | None = Field(default=None, ge=32, le=2048)
    small_file_threshold_mb: int | None = Field(default=None, ge=8, le=256)
    status: str | None = Field(default=None, pattern=r"^(active|paused)$")
    description: str | None = None
