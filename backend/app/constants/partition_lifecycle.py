"""Partition merge lifecycle. Mirrored in frontend/src/constants/partitionLifecycle.ts.

active   — 正常分区，可生成/执行合并计划
retiring — 已纳入退役单并冻结：停止新合并，等待一次性退役执行
retired  — 退役完成：不再参与合并，剩余文件仅被保留快照引用
"""
from enum import Enum


class PartitionLifecycle(str, Enum):
    ACTIVE = "active"
    RETIRING = "retiring"
    RETIRED = "retired"


PARTITION_LIFECYCLE_LABELS = {
    PartitionLifecycle.ACTIVE: "可合并",
    PartitionLifecycle.RETIRING: "退役冻结中",
    PartitionLifecycle.RETIRED: "已退役",
}
