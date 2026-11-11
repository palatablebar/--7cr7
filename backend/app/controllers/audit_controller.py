from sqlalchemy.orm import Session

from app.services import audit_service


def recent(db: Session, limit: int = 20) -> dict:
    return {"items": audit_service.list_recent(db, limit=limit)}
