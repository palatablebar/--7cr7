from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class LakeTable(Base):
    """One lake table (db + name) with its compaction target profile."""

    __tablename__ = "lake_tables"
    __table_args__ = (UniqueConstraint("db_name", "table_name", name="uq_lake_table_identity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    db_name: Mapped[str] = mapped_column(String(64), nullable=False)
    table_name: Mapped[str] = mapped_column(String(96), nullable=False)
    partition_key: Mapped[str] = mapped_column(String(32), nullable=False, default="dt")
    file_format: Mapped[str] = mapped_column(String(16), nullable=False, default="parquet")
    target_file_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=256)
    small_file_threshold_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=64)
    # status: active | paused
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    files = relationship("DataFile", back_populates="table", cascade="all, delete-orphan")
    partitions = relationship("PartitionSpec", back_populates="table", cascade="all, delete-orphan")
    plans = relationship("CompactPlan", back_populates="table", cascade="all, delete-orphan")
    snapshots = relationship("TableSnapshot", back_populates="table", cascade="all, delete-orphan")

    @property
    def fq_name(self) -> str:
        return f"{self.db_name}.{self.table_name}"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LakeTable {self.db_name}.{self.table_name}>"
