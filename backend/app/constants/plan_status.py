"""CompactPlan lifecycle. Mirrored in frontend/src/constants/planStatus.ts."""
from enum import Enum


class PlanStatus(str, Enum):
    DRAFT = "draft"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


PLAN_STATUS_LABELS = {
    PlanStatus.DRAFT: "草稿",
    PlanStatus.EXECUTING: "已提交",
    PlanStatus.COMPLETED: "已完成",
    PlanStatus.FAILED: "失败",
}
