from pydantic import BaseModel


class SnapshotCreateRequest(BaseModel):
    note: str | None = None


class SnapshotDiffQuery(BaseModel):
    left_id: int
    right_id: int
