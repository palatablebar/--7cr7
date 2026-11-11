from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # demo accounts use the reserved .local domain, so validate the shape
    # instead of using EmailStr (which rejects special-use TLDs).
    email: str = Field(min_length=5, max_length=190, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    daily_plan_quota: int
    plan_used: int
    quota_remaining: int


def serialize_user(user) -> dict:
    quota = int(user.daily_plan_quota or 0)
    used = int(user.plan_used or 0)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "daily_plan_quota": quota,
        "plan_used": used,
        "quota_remaining": max(0, quota - used),
    }
