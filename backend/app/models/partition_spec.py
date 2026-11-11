from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class PartitionSpec(Base):
    """Cached aggregate for one partition; recomputed from data_files."""

    __tablename__ = "partition_specs"
    __table_args__ = (UniqueConstraint("table_id", "partition_value", name="uq_partition_spec"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("lake_tables.id", ondelete="CASCADE"), index=True)
    partition_value: Mapped[str] = mapped_column(String(32), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    small_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    avg_file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # band: healthy | watch | degraded
    health_band: Mapped[str] = mapped_column(String(16), nullable=False, default="degraded")
    # risk: normal | hot (newest partition for the table)
    risk: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    last_compacted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    table = relationship("LakeTable", back_populates="partitions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PartitionSpec {self.partition_value} files={self.file_count}>"
