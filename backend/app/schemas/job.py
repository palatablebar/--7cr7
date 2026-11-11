from pydantic import BaseModel


class JobCreateRequest(BaseModel):
    plan_id: int
