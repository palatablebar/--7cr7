from pydantic import BaseModel


class AuditOut(BaseModel):
    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    created_at: str | None
