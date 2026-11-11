from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class DataFile(Base):
    """A physical object in the lake manifest: path is the natural key per table."""

    __tablename__ = "data_files"
    __table_args__ = (UniqueConstraint("table_id", "path", name="uq_data_file_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("lake_tables.id", ondelete="CASCADE"), index=True)
    partition_value: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    file_format: Mapped[str] = mapped_column(String(16), nullable=False, default="parquet")
    write_source: Mapped[str] = mapped_column(String(32), nullable=False, default="flink")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    table = relationship("LakeTable", back_populates="files")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DataFile {self.path} bytes={self.size_bytes}>"
