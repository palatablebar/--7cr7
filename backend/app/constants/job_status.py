"""CompactJob lifecycle. Mirrored in frontend/src/constants/jobStatus.ts."""
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


JOB_STATUS_LABELS = {
    JobStatus.QUEUED: "排队中",
    JobStatus.RUNNING: "执行中",
    JobStatus.SUCCEEDED: "已完成",
    JobStatus.FAILED: "失败",
}

ACTIVE_JOB_STATUSES = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)
