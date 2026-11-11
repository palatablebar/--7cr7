from datetime import date

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.constants.error_codes import AppError, ErrorCode
from app.models import User
from app.utils.jwt import create_access_token
from app.utils.logger import log_event
from app.utils.password import hash_password, verify_password

ROLE_QUOTAS = {"admin": 20, "engineer": 8, "analyst": 0}


def upsert_user(db: Session, email: str, password: str, display_name: str, role: str, quota: int | None = None) -> User:
    """The one and only user-creation branch (seed + future admin flows)."""
    user = db.query(User).filter(User.email == email).first()
    daily = quota if quota is not None else ROLE_QUOTAS.get(role, settings.PLAN_DAILY_QUOTA)
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role=role,
            daily_plan_quota=daily,
            plan_used=0,
            plan_used_date=None,
        )
        db.add(user)
        db.flush()
    else:
        # idempotent: refresh metadata but keep the user's own quota usage
        user.display_name = display_name
        user.role = role
        if quota is not None:
            user.daily_plan_quota = quota
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        log_event("AUTH_LOGIN_FAILED", email=email, reason="bad_credentials")
        raise AppError(ErrorCode.UNAUTHORIZED, message="邮箱或密码不正确", status_code=401)
    token = create_access_token(user)
    log_event("AUTH_LOGIN_SUCCEEDED", user_id=user.id, role=user.role)
    return user, token


def load_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def reset_daily_quota_if_needed(db: Session, user: User) -> User:
    today = date.today()
    if user.plan_used_date != today:
        user.plan_used_date = today
        user.plan_used = 0
        db.commit()
    return user
