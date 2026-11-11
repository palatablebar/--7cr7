from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class CompactPlan(Base):
    """Persisted bin-packing plan. `groups` holds the FFD output; `fingerprint`
    is the deterministic digest used for the idempotency check."""

    __tablename__ = "compact_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("lake_tables.id", ondelete="CASCADE"), index=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="ffd_256")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    partition_values: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    groups: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cost: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    candidate_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    group_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_output_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rewritten_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    est_duration_seconds: Mapped[float] = mapped_column(nullable=False, default=0)
    est_cost_yuan: Mapped[float] = mapped_column(nullable=False, default=0)
    savings_pct: Mapped[float] = mapped_column(nullable=False, default=0)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    table = relationship("LakeTable", back_populates="plans")
    jobs = relationship("CompactJob", back_populates="plan", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CompactPlan {self.id} groups={self.group_count}>"
