from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class PartitionRetirement(Base):
    """One partition-retirement order covering a batch of partitions.

    `items` holds the per-partition reclaim manifest generated at creation
    (protected vs reclaimable files, derived from retained-snapshot references);
    `result` holds the per-partition outcome after the one-shot atomic execute.
    `fingerprint` makes re-creation idempotent: identical table + partitions +
    manifest resolves to the same order instead of a duplicate.
    """

    __tablename__ = "partition_retirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("lake_tables.id", ondelete="CASCADE"), index=True)
    # status: retiring | retired | failed | restored
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="retiring")
    partition_values: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    protected_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reclaimable_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reclaimable_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    table = relationship("LakeTable", back_populates="retirements")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PartitionRetirement {self.id} status={self.status} partitions={len(self.partition_values or [])}>"
