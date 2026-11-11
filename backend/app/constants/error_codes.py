"""Central error-code catalogue + AppError.

LAKE-2xxx is referenced by services, tasks and by
frontend/src/constants/errorCodes.ts.
"""
from enum import Enum


class ErrorCode(str, Enum):
    TABLE_NOT_FOUND = "LAKE-2001"
    TABLE_DUPLICATE = "LAKE-2002"
    PARTITION_NOT_FOUND = "LAKE-2003"
    NO_SMALL_FILES = "LAKE-2004"
    PLAN_NOT_FOUND = "LAKE-2005"
    PLAN_ALREADY_EXECUTED = "LAKE-2006"
    PLAN_PARTITIONS_INVALID = "LAKE-2007"
    JOB_NOT_FOUND = "LAKE-2008"
    JOB_LOCKED = "LAKE-2009"
    QUOTA_EXHAUSTED = "LAKE-2010"
    RATE_LIMITED = "LAKE-2011"
    SNAPSHOT_NOT_FOUND = "LAKE-2012"
    SNAPSHOT_DIFF_INVALID = "LAKE-2013"
    TABLE_PAUSED = "LAKE-2014"
    # auth layer
    FORBIDDEN = "LAKE-2015"
    UNAUTHORIZED = "LAKE-2016"
    # partition retirement
    PARTITION_RETIRING = "LAKE-2017"
    RETIREMENT_NOT_FOUND = "LAKE-2019"
    RETIREMENT_STATE_INVALID = "LAKE-2020"


ERROR_MESSAGES = {
    ErrorCode.TABLE_NOT_FOUND: "湖表不存在或已删除",
    ErrorCode.TABLE_DUPLICATE: "同名湖表已存在",
    ErrorCode.PARTITION_NOT_FOUND: "分区不存在",
    ErrorCode.NO_SMALL_FILES: "所选分区没有低于小文件阈值的文件，无需整理",
    ErrorCode.PLAN_NOT_FOUND: "合并计划不存在",
    ErrorCode.PLAN_ALREADY_EXECUTED: "该计划已提交或已完成，不能重复执行",
    ErrorCode.PLAN_PARTITIONS_INVALID: "所选分区不属于该湖表",
    ErrorCode.JOB_NOT_FOUND: "合并任务不存在",
    ErrorCode.JOB_LOCKED: "该湖表已有合并任务在执行，请稍后再试",
    ErrorCode.QUOTA_EXHAUSTED: "今日合并计划配额已用尽",
    ErrorCode.RATE_LIMITED: "请求过于频繁",
    ErrorCode.SNAPSHOT_NOT_FOUND: "快照不存在",
    ErrorCode.SNAPSHOT_DIFF_INVALID: "快照对比参数非法（不能与自身对比）",
    ErrorCode.TABLE_PAUSED: "湖表已暂停，不能生成或执行计划",
    ErrorCode.FORBIDDEN: "当前角色无权执行该操作",
    ErrorCode.UNAUTHORIZED: "未登录或登录已过期",
    ErrorCode.PARTITION_RETIRING: "分区已纳入退役单并冻结，停止新合并",
    ErrorCode.RETIREMENT_NOT_FOUND: "退役单不存在",
    ErrorCode.RETIREMENT_STATE_INVALID: "退役单当前状态不允许该操作",
}

ERROR_STATUS = {
    ErrorCode.TABLE_NOT_FOUND: 404,
    ErrorCode.TABLE_DUPLICATE: 409,
    ErrorCode.PARTITION_NOT_FOUND: 404,
    ErrorCode.NO_SMALL_FILES: 409,
    ErrorCode.PLAN_NOT_FOUND: 404,
    ErrorCode.PLAN_ALREADY_EXECUTED: 409,
    ErrorCode.PLAN_PARTITIONS_INVALID: 400,
    ErrorCode.JOB_NOT_FOUND: 404,
    ErrorCode.JOB_LOCKED: 409,
    ErrorCode.QUOTA_EXHAUSTED: 429,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.SNAPSHOT_NOT_FOUND: 404,
    ErrorCode.SNAPSHOT_DIFF_INVALID: 400,
    ErrorCode.TABLE_PAUSED: 409,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.PARTITION_RETIRING: 409,
    ErrorCode.RETIREMENT_NOT_FOUND: 404,
    ErrorCode.RETIREMENT_STATE_INVALID: 409,
}


class AppError(Exception):
    def __init__(self, code, message: str | None = None, detail=None, context: str | None = None, status_code: int | None = None):
        self.code = code.value if isinstance(code, ErrorCode) else str(code)
        try:
            enum_code = ErrorCode(self.code)
        except ValueError:
            enum_code = None
        self.message = message or (ERROR_MESSAGES.get(enum_code, "请求处理失败") if enum_code else "请求处理失败")
        if context:
            self.message = f"{self.message}（{context}）"
        self.detail = detail
        self.status_code = status_code or (ERROR_STATUS.get(enum_code, 400) if enum_code else 400)
        super().__init__(self.message)
