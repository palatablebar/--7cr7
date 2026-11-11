"""Partition write-risk band. Mirrored in frontend/src/constants/partitionRisk.ts."""
from enum import Enum


class PartitionRisk(str, Enum):
    NORMAL = "normal"
    HOT = "hot"


PARTITION_RISK_LABELS = {
    PartitionRisk.NORMAL: "可整理",
    PartitionRisk.HOT: "最新分区·写入中",
}
