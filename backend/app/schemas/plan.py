from pydantic import BaseModel, Field


class PlanCreateRequest(BaseModel):
    table_id: int
    partition_values: list[str] = Field(min_length=1, max_length=12)
    strategy: str | None = Field(default=None, pattern=r"^(ffd_256|ffd_target)$")
    target_file_size_mb: int | None = Field(default=None, ge=32, le=2048)
    note: str | None = Field(default=None, max_length=500)
