"""Compaction plan generation, idempotency and execution dispatch."""
from sqlalchemy.orm import Session

from app.compaction.binpack import build_plan
from app.compaction.cost_model import CostParams
from app.config.settings import settings
from app.constants.error_codes import AppError, ErrorCode
from app.constants.file_format import TableStatus
from app.constants.plan_status import PlanStatus
from app.middlewares.quota import acquire_table_lock, consume_plan_quota, quota_snapshot, release_table_lock
from app.models import CompactJob, CompactPlan, DataFile, LakeTable, PartitionSpec, User
from app.schemas.common import iso
from app.services import partition_service, table_service
from app.utils.logger import log_event


def get_plan_or_404(db: Session, plan_id: int) -> CompactPlan:
    plan = db.get(CompactPlan, plan_id)
    if plan is None:
        raise AppError(ErrorCode.PLAN_NOT_FOUND)
    return plan


def cost_params() -> CostParams:
    return CostParams(
        bandwidth_mb_per_s=settings.BANDWIDTH_MBPS,
        per_file_overhead_s=settings.PER_FILE_OVERHEAD_S,
        unit_cost_per_gb=settings.UNIT_COST_PER_GB,
        cost_per_file_day=settings.COST_PER_FILE_DAY,
    )


def create_plan(db: Session, user: User, payload) -> dict:
    table = table_service.get_table_or_404(db, payload.table_id)
    if table.status != TableStatus.ACTIVE.value:
        raise AppError(ErrorCode.TABLE_PAUSED)
    partitions = sorted({str(value).strip() for value in payload.partition_values if str(value).strip()})
    if not partitions:
        raise AppError(ErrorCode.PLAN_PARTITIONS_INVALID)

    # refresh specs first so hot/newest partitions are evaluated on live data
    partition_service.recompute_table(db, table)
    specs = (
        db.query(PartitionSpec)
        .filter(PartitionSpec.table_id == table.id, PartitionSpec.partition_value.in_(partitions))
        .all()
    )
    found = {spec.partition_value for spec in specs}
    missing = [value for value in partitions if value not in found]
    if missing:
        raise AppError(ErrorCode.PARTITION_NOT_FOUND, detail={"missing": missing})

    files = (
        db.query(DataFile)
        .filter(DataFile.table_id == table.id, DataFile.partition_value.in_(partitions))
        .all()
    )
    partition_files: dict[str, list[dict]] = {value: [] for value in partitions}
    for row in files:
        partition_files[row.partition_value].append(
            {
                "path": row.path,
                "size_bytes": int(row.size_bytes),
                "row_count": int(row.row_count),
                "checksum": row.checksum,
                "partition_value": row.partition_value,
            }
        )

    hot = {spec.partition_value for spec in specs if spec.risk == "hot"}
    strategy = payload.strategy or ("ffd_target" if payload.target_file_size_mb else "ffd_256")
    result = build_plan(
        table={
            "db_name": table.db_name,
            "table_name": table.table_name,
            "partition_key": table.partition_key,
            "target_file_size_mb": table.target_file_size_mb,
            "small_file_threshold_mb": table.small_file_threshold_mb,
            "bucket": settings.LAKE_BUCKET,
        },
        partition_files=partition_files,
        strategy=strategy,
        target_file_size_mb=payload.target_file_size_mb,
        hot_partitions=hot,
        cost_params=cost_params(),
    )
    if result["candidate_file_count"] == 0:
        raise AppError(ErrorCode.NO_SMALL_FILES, detail={"partitions": partitions})

    quota = consume_plan_quota(db, user)

    previous = (
        db.query(CompactPlan)
        .filter(CompactPlan.table_id == table.id, CompactPlan.fingerprint == result["fingerprint"])
        .order_by(CompactPlan.id.desc())
        .first()
    )
    plan = CompactPlan(
        table_id=table.id,
        strategy=result["strategy"],
        status=PlanStatus.DRAFT.value,
        partition_values=result["partition_values"],
        groups=result["groups"],
        risk_flags=result["risk_flags"],
        cost=result["cost"],
        candidate_file_count=result["candidate_file_count"],
        group_count=result["group_count"],
        expected_output_files=result["expected_output_files"],
        rewritten_bytes=result["rewritten_bytes"],
        est_duration_seconds=float(result["cost"]["est_duration_seconds"]),
        est_cost_yuan=float(result["cost"]["est_cost_yuan"]),
        savings_pct=float(result["savings_pct"]),
        fingerprint=result["fingerprint"],
        note=payload.note,
        created_by=user.id,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    log_event("PLAN_CREATED", plan_id=plan.id, table=f"{table.db_name}.{table.table_name}", groups=plan.group_count)

    return {
        "plan": serialize_plan(db, plan, include_groups=True),
        "idempotent": previous is not None,
        "previous_plan": (
            {
                "id": previous.id,
                "created_at": iso(previous.created_at),
                "status": previous.status,
            }
            if previous is not None
            else None
        ),
        "quota": quota_snapshot(user),
        "candidate_files": result["candidate_file_count"],
        "empty_partitions": result["empty_partitions"],
    }


def serialize_plan(db: Session, plan: CompactPlan, *, include_groups: bool = False) -> dict:
    table = db.get(LakeTable, plan.table_id)
    creator = db.get(User, plan.created_by) if plan.created_by else None
    latest_job = (
        db.query(CompactJob).filter(CompactJob.plan_id == plan.id).order_by(CompactJob.id.desc()).first()
    )
    data = {
        "id": plan.id,
        "table_id": plan.table_id,
        "table_fq_name": table.fq_name if table else None,
        "partition_key": table.partition_key if table else "dt",
        "strategy": plan.strategy,
        "status": plan.status,
        "partition_values": plan.partition_values or [],
        "risk_flags": plan.risk_flags or [],
        "cost": plan.cost or {},
        "candidate_file_count": plan.candidate_file_count,
        "group_count": plan.group_count,
        "expected_output_files": plan.expected_output_files,
        "saved_files": plan.candidate_file_count - plan.expected_output_files,
        "rewritten_bytes": int(plan.rewritten_bytes),
        "est_duration_seconds": float(plan.est_duration_seconds),
        "est_cost_yuan": float(plan.est_cost_yuan),
        "savings_pct": float(plan.savings_pct),
        "fingerprint": plan.fingerprint,
        "note": plan.note,
        "created_by": plan.created_by,
        "created_by_name": creator.display_name if creator else None,
        "created_at": iso(plan.created_at),
        "latest_job": (
            {
                "id": latest_job.id,
                "status": latest_job.status,
                "progress": latest_job.progress,
            }
            if latest_job is not None
            else None
        ),
    }
    if include_groups:
        data["groups"] = plan.groups or []
    return data


def list_plans(db: Session, table_id: int | None = None, limit: int = 40) -> list[dict]:
    query = db.query(CompactPlan).order_by(CompactPlan.id.desc())
    if table_id:
        query = query.filter(CompactPlan.table_id == table_id)
    return [serialize_plan(db, plan, include_groups=False) for plan in query.limit(limit).all()]


def execute_plan(db: Session, user: User, plan_id: int) -> dict:
    plan = get_plan_or_404(db, plan_id)
    if plan.status != PlanStatus.DRAFT.value:
        raise AppError(ErrorCode.PLAN_ALREADY_EXECUTED, detail={"status": plan.status})
    table = table_service.get_table_or_404(db, plan.table_id)
    if table.status != TableStatus.ACTIVE.value:
        raise AppError(ErrorCode.TABLE_PAUSED)
    if not acquire_table_lock(table.id):
        raise AppError(ErrorCode.JOB_LOCKED, detail={"table_id": table.id})

    job = CompactJob(
        plan_id=plan.id,
        table_id=table.id,
        status="queued",
        progress=0,
        groups_total=len(plan.groups or []),
        triggered_by=user.id,
    )
    try:
        db.add(job)
        plan.status = PlanStatus.EXECUTING.value
        db.commit()
        db.refresh(job)
        from app.tasks.compact_job import run_compaction_job

        async_result = run_compaction_job.delay(job.id)
        job.celery_task_id = async_result.id
        db.commit()
    except Exception as exc:  # broker badly down -> fail visibly instead of hanging
        db.rollback()
        release_table_lock(table.id)
        plan.status = PlanStatus.FAILED.value
        job.status = "failed"
        job.failure_reason = f"任务投递失败: {type(exc).__name__}"
        db.add(job)
        db.commit()
        log_event("JOB_DISPATCH_FAILED", plan_id=plan.id, reason=str(exc))
        raise AppError("LAKE-5000", message="合并任务投递失败，请稍后重试", status_code=503) from exc

    log_event("JOB_DISPATCHED", job_id=job.id, plan_id=plan.id, task_id=job.celery_task_id)
    from app.services import job_service

    return job_service.serialize_job(db, job)


def retry_job(db: Session, user: User, job_id: int) -> dict:
    from app.services import job_service

    job = job_service.get_job_or_404(db, job_id)
    if job.status != "failed":
        raise AppError("LAKE-2018", message="只有失败的任务可以重试", status_code=409, detail={"status": job.status})
    plan = get_plan_or_404(db, job.plan_id)
    table = table_service.get_table_or_404(db, plan.table_id)
    if not acquire_table_lock(table.id):
        raise AppError(ErrorCode.JOB_LOCKED, detail={"table_id": table.id})
    new_job = CompactJob(
        plan_id=plan.id,
        table_id=table.id,
        status="queued",
        progress=0,
        groups_total=len(plan.groups or []),
        triggered_by=user.id,
    )
    try:
        db.add(new_job)
        plan.status = PlanStatus.EXECUTING.value
        db.commit()
        db.refresh(new_job)
        from app.tasks.compact_job import run_compaction_job

        async_result = run_compaction_job.delay(new_job.id)
        new_job.celery_task_id = async_result.id
        db.commit()
    except Exception as exc:
        db.rollback()
        release_table_lock(table.id)
        raise AppError("LAKE-5000", message="重试任务投递失败", status_code=503) from exc
    return job_service.serialize_job(db, new_job)
