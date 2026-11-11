from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.schemas.common import iso


def list_recent(db: Session, limit: int = 20, actor_id: int | None = None) -> list[dict]:
    query = db.query(AuditLog).order_by(AuditLog.id.desc())
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    rows = query.limit(max(1, min(limit, 100))).all()
    actors = {user.id: user.display_name for user in db.query(User).all()}
    return [
        {
            "id": row.id,
            "actor_id": row.actor_id,
            "actor_name": actors.get(row.actor_id, "系统"),
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "created_at": iso(row.created_at),
        }
        for row in rows
    ]
