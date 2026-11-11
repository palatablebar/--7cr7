"""lakePack API entrypoint.

Middleware order (outermost first):
    CORS -> RequestId -> Auth -> RateLimit -> Audit -> routes -> error handlers
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.database import init_db
from app.config.settings import settings
from app.middlewares.audit_logger import AuditMiddleware
from app.middlewares.auth import AuthMiddleware
from app.middlewares.error_handler import RequestIdMiddleware, install_error_handlers
from app.middlewares.quota import RateLimitMiddleware
from app.routes import audit, auth, health, job, plan, retirement, snapshot, table
from app.utils.logger import log_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.SEED_DEMO:
        try:
            from scripts.seed_demo import run_seed

            result = run_seed()
            log_event("SEED_DEMO_FINISHED", **result)
        except Exception as exc:  # seed must never block startup
            log_event("SEED_DEMO_FAILED", error=f"{type(exc).__name__}: {exc}")
    yield


app = FastAPI(
    title="lakePack API",
    description="数据湖小文件合并与分区整理工坊 — 拾光内容平台离线数仓小队",
    version="1.0.0",
    lifespan=lifespan,
)

install_error_handlers(app)

# added first => innermost
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIdMiddleware)
# added last => outermost (preflight is answered before auth)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# The compose stack routes `/api/` through Nginx to `backend:8000/` (the prefix is
# stripped), while direct backend curl uses `:19221/api/...`. Mounting the same
# routers under both prefixes keeps the two entrypoints identical.
for _prefix in ("", "/api"):
    app.include_router(health.router, prefix=_prefix)
    app.include_router(auth.router, prefix=_prefix)
    app.include_router(table.router, prefix=_prefix)
    app.include_router(plan.router, prefix=_prefix)
    app.include_router(job.router, prefix=_prefix)
    app.include_router(snapshot.router, prefix=_prefix)
    app.include_router(retirement.router, prefix=_prefix)
    app.include_router(audit.router, prefix=_prefix)


@app.get("/")
def index() -> dict:
    return {
        "service": "lakepack-backend",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/auth/login",
            "/tables",
            "/tables/{id}/partitions",
            "/tables/{id}/files",
            "/plans",
            "/plans/{id}/execute",
            "/jobs",
            "/tables/{id}/snapshots",
            "/snapshots/diff",
            "/tables/{id}/reclaim-manifest",
            "/tables/{id}/retirements",
            "/retirements/{id}/execute",
            "/retirements/{id}/restore",
        ],
    }
