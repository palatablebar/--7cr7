"""Import every model so Base.metadata is complete before create_all()."""
from app.models.audit_log import AuditLog
from app.models.compact_job import CompactJob
from app.models.compact_plan import CompactPlan
from app.models.data_file import DataFile
from app.models.lake_table import LakeTable
from app.models.partition_retirement import PartitionRetirement
from app.models.partition_spec import PartitionSpec
from app.models.table_snapshot import TableSnapshot
from app.models.user import User

__all__ = [
    "AuditLog",
    "CompactJob",
    "CompactPlan",
    "DataFile",
    "LakeTable",
    "PartitionRetirement",
    "PartitionSpec",
    "TableSnapshot",
    "User",
]
