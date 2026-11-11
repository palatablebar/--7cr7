from pydantic import BaseModel, Field


class RetirementCreateRequest(BaseModel):
    partition_values: list[str] = Field(min_length=1, max_length=12)
    note: str | None = Field(default=None, max_length=500)


class RetirementExecuteRequest(BaseModel):
    # 演练开关：注入一次执行失败，验证整批回滚与恢复流程
    simulate_failure: bool = False
