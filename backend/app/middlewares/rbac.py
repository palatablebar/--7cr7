"""Role checks as FastAPI dependencies.

``require_roles("admin", "engineer")`` yields a 403 whose detail names the roles
that would be allowed. Resource-level rules (analyst can never spend quota)
live in services/plan_service.py.
"""
from fastapi import Depends

from app.constants.error_codes import AppError, ErrorCode
from app.middlewares.auth import get_current_user
from app.models import User

ADMIN = "admin"
ENGINEER = "engineer"
ANALYST = "analyst"
WRITE_ROLES = (ADMIN, ENGINEER)


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(
                ErrorCode.FORBIDDEN,
                message=f"当前角色 {user.role} 无权执行该操作，需要 {'/'.join(roles)}",
                detail={"required_roles": list(roles), "role": user.role},
            )
        return user

    return dependency


def can_write(user: User) -> bool:
    return user.role in WRITE_ROLES
