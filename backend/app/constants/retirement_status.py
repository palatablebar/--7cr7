"""PartitionRetirement lifecycle. Mirrored in frontend/src/constants/retirementStatus.ts.

retiring — 退役单已生成、分区已冻结（停止新合并），等待一次性执行
retired  — 退役执行成功：可回收文件已在同一事务内清理完毕
failed   — 执行失败：事务已回滚、分区文件保持原样，可执行恢复
restored — 已恢复：分区解冻回到 active，退役单关闭（不重复清理）
"""
from enum import Enum


class RetirementStatus(str, Enum):
    RETIRING = "retiring"
    RETIRED = "retired"
    FAILED = "failed"
    RESTORED = "restored"


RETIREMENT_STATUS_LABELS = {
    RetirementStatus.RETIRING: "已冻结·待执行",
    RetirementStatus.RETIRED: "已退役",
    RetirementStatus.FAILED: "失败·可恢复",
    RetirementStatus.RESTORED: "已恢复",
}
