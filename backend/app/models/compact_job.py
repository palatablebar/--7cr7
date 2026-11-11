from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class CompactJob(Base):
    """Celery-backed rewrite job. Progress is a percentage 0-100."""

    __tablename__ = "compact_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("compact_plans.id", ondelete="CASCADE"), index=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("lake_tables.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    groups_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_groups: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rewritten_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    produced_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bytes_written: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rows_before: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rows_after: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    snapshot_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("table_snapshots.id", ondelete="SET NULL"), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    plan = relationship("CompactPlan", back_populates="jobs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CompactJob {self.id} status={self.status} progress={self.progress}>"
