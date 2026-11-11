"""Rate limiting, daily plan quota and the per-table execution lock.

* sliding window: Redis zset ``rl:lakepack:{user_id}`` (RATE_WINDOW_SECONDS)
* daily quota: users.daily_plan_quota / plan_used / plan_used_date
* table lock: SETNX ``joblock:{table_id}`` so two rewrite jobs never touch the
  same table concurrently (the "重复跑覆盖正在写入的分区" pain point).
"""
import time
from datetime import date

import redis
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import settings
from app.constants.error_codes import AppError, ErrorCode
from app.models import User
from app.utils.logger import log_event

_client = None
_mem_window: dict[str, list[float]] = {}
_mem_locks: dict[int, float] = {}
LOCK_TTL_SECONDS = 1800


def get_redis():
    global _client
    if _client is None:
        try:
            _client = redis.Redis.from_url(
                settings.REDIS_URL, socket_timeout=0.4, socket_connect_timeout=0.4, decode_responses=True
            )
            _client.ping()
        except Exception:
            _client = False
    return _client or None


def rate_limit_allow(user_id: int, bucket: str = "write") -> bool:
    window = settings.RATE_WINDOW_SECONDS
    max_hits = settings.RATE_WINDOW_MAX
    now = time.time()
    key = f"rl:lakepack:{bucket}:{user_id}"
    client = get_redis()
    if client is not None:
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {f"{now:.6f}": now})
            pipe.zcard(key)
            pipe.expire(key, window)
            _, _, count, _ = pipe.execute()
            allowed = int(count) <= max_hits
        except Exception:
            allowed = _mem_allow(key, now, window, max_hits)
    else:
        allowed = _mem_allow(key, now, window, max_hits)
    if not allowed:
        log_event("AUDIT_RATE_LIMITED", user_id=user_id, bucket=bucket, window_max=max_hits)
    return allowed


def _mem_allow(key: str, now: float, window: int, max_hits: int) -> bool:
    hits = [t for t in _mem_window.get(key, []) if t > now - window]
    hits.append(now)
    _mem_window[key] = hits
    return len(hits) <= max_hits


def acquire_table_lock(table_id: int) -> bool:
    client = get_redis()
    if client is not None:
        try:
            return bool(client.set(f"joblock:{table_id}", "1", nx=True, ex=LOCK_TTL_SECONDS))
        except Exception:
            pass
    expiry = _mem_locks.get(table_id)
    if expiry and expiry > time.time():
        return False
    _mem_locks[table_id] = time.time() + LOCK_TTL_SECONDS
    return True


def release_table_lock(table_id: int) -> None:
    client = get_redis()
    if client is not None:
        try:
            client.delete(f"joblock:{table_id}")
        except Exception:
            pass
    _mem_locks.pop(table_id, None)


def quota_snapshot(user: User) -> dict:
    quota = int(user.daily_plan_quota or 0)
    used = int(user.plan_used or 0)
    return {
        "daily_plan_quota": quota,
        "plan_used": used,
        "quota_remaining": max(0, quota - used),
        "plan_used_date": user.plan_used_date.strftime("%Y-%m-%d") if user.plan_used_date else None,
        "window_max": settings.RATE_WINDOW_MAX,
        "window_seconds": settings.RATE_WINDOW_SECONDS,
    }


def consume_plan_quota(db: Session, user: User) -> dict:
    """Called when a compaction plan is generated (the expensive operation)."""
    today = date.today()
    if user.plan_used_date != today:
        user.plan_used_date = today
        user.plan_used = 0
    if not rate_limit_allow(user.id, "plan"):
        raise AppError(
            ErrorCode.RATE_LIMITED,
            detail={"retry_after": settings.RATE_WINDOW_SECONDS},
        )
    if user.plan_used >= user.daily_plan_quota:
        log_event(
            "AUDIT_QUOTA_REJECTED",
            user_id=user.id,
            used=user.plan_used,
            quota=user.daily_plan_quota,
        )
        raise AppError(
            ErrorCode.QUOTA_EXHAUSTED,
            detail={
                "quota": user.daily_plan_quota,
                "used": user.plan_used,
                "retry_after": 3600,
            },
        )
    user.plan_used += 1
    db.commit()
    return quota_snapshot(user)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis sliding window on write requests; 429 carries retry_after."""

    WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

    async def dispatch(self, request, call_next):
        if request.method in self.WRITE_METHODS:
            claims = getattr(request.state, "user_claims", None) or {}
            user_id = claims.get("sub")
            if user_id and not rate_limit_allow(int(user_id)):
                from starlette.responses import JSONResponse

                from app.schemas.common import error_envelope

                return JSONResponse(
                    status_code=429,
                    content=error_envelope(
                        ErrorCode.RATE_LIMITED.value,
                        "请求过于频繁",
                        getattr(request.state, "request_id", None),
                        {"retry_after": settings.RATE_WINDOW_SECONDS},
                    ),
                )
        return await call_next(request)
