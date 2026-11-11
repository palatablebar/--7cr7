from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(190), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # role: admin | engineer | analyst  (mirrored in frontend/src/types/user.ts)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="analyst")
    daily_plan_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    plan_used_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    plan_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} role={self.role}>"
