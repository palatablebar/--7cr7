"""Celery task: execute a bin-packing plan against the metadata manifest.

For every ``action=rewrite`` group it removes the small input files, writes one
merged DataFile (deterministic checksum), reports progress, then records a new
TableSnapshot so algorithm 2 can diff the change and audit row conservation.
The demo rewrites metadata only — no object-storage bytes are moved (see README
§simulation boundary); sizes/rows follow the plan's cost model.
"""
import time

from app.config.database import SessionLocal
from app.constants.plan_status import PlanStatus
from app.middlewares.quota import release_table_lock
from app.models import CompactJob, CompactPlan, DataFile, LakeTable
from app.services import job_service, partition_service, snapshot_service, table_service
from app.utils.lake import checksum_of
from app.utils.logger import log_event

from app.config.celery_app import celery_app

PROGRESS_BUDGET = 90          # the last 10% covers snapshot + verification
SLEEP_BETWEEN_GROUPS = 0.55   # keeps progress observable in the UI


@celery_app.task(name="lakepack.run_compaction_job", bind=True)
def run_compaction_job(self, job_id: int) -> dict:  # noqa: ARG001
    db = SessionLocal()
    job = None
    table = None
    try:
        job = db.get(CompactJob, job_id)
        if job is None:
            return {"ok": False, "reason": f"job {job_id} not found"}
        plan = db.get(CompactPlan, job.plan_id)
        table = db.get(LakeTable, job.table_id)
        job_service.mark_running(db, job)

        groups = list(plan.groups or [])
        total = len(groups)
        job.groups_total = total
        db.commit()

        rewritten_files = 0
        produced_files = 0
        bytes_written = 0
        rows_before = 0
        rows_after = 0
        skipped: list[str] = []

        for index, group in enumerate(groups, start=1):
            if group.get("action") != "rewrite":
                job_service.update_progress(
                    db,
                    job,
                    progress=int(index / max(1, total) * PROGRESS_BUDGET),
                    processed_groups=index,
                    rewritten_files=rewritten_files,
                    produced_files=produced_files,
                    bytes_written=bytes_written,
                    rows_before=rows_before,
                    rows_after=rows_after,
                )
                if total:
                    time.sleep(SLEEP_BETWEEN_GROUPS / 2)
                continue

            paths = [item["path"] for item in group.get("files", [])]
            inputs = (
                db.query(DataFile)
                .filter(DataFile.table_id == table.id, DataFile.path.in_(paths))
                .all()
            )
            if len(inputs) < len(paths):
                # a retry after a partially-applied plan: keep the metadata consistent
                skipped.append(group.get("group_id", "?"))
                continue

            output_path = group["output_file"]
            output_rows = int(group.get("output_rows") or sum(int(row.row_count) for row in inputs))
            output_size = int(group.get("output_size_bytes") or sum(int(row.size_bytes) for row in inputs))
            output_checksum = checksum_of(output_path, output_rows, output_size)

            for row in inputs:
                db.delete(row)
            db.flush()
            produced = DataFile(
                table_id=table.id,
                partition_value=group["partition_value"],
                path=output_path,
                size_bytes=output_size,
                row_count=output_rows,
                checksum=output_checksum,
                file_format=table.file_format,
                write_source="compaction",
            )
            db.add(produced)
            rewritten_files += len(inputs)
            produced_files += 1
            bytes_written += output_size
            rows_before += sum(int(row.row_count) for row in inputs)
            rows_after += output_rows

            job_service.update_progress(
                db,
                job,
                progress=int(index / max(1, total) * PROGRESS_BUDGET),
                processed_groups=index,
                rewritten_files=rewritten_files,
                produced_files=produced_files,
                bytes_written=bytes_written,
                rows_before=rows_before,
                rows_after=rows_after,
            )
            time.sleep(SLEEP_BETWEEN_GROUPS)

        # refresh partition aggregates and stamp last_compacted_at
        specs = partition_service.recompute_table(db, table)
        touched = {group["partition_value"] for group in groups if group.get("action") == "rewrite"}
        for spec in specs:
            if spec.partition_value in touched:
                from datetime import datetime

                spec.last_compacted_at = datetime.now()
        db.commit()

        job.progress = 95
        db.commit()

        snapshot = snapshot_service.create_snapshot(
            db,
            table,
            created_by=job.triggered_by,
            note=f"合并任务 #{job.id} 完成快照（{len(touched)} 个分区）",
            job_id=job.id,
        )
        job_service.mark_succeeded(db, job, snapshot.id)
        log_event(
            "JOB_SUCCEEDED",
            job_id=job.id,
            plan_id=plan.id,
            rewritten_files=rewritten_files,
            produced_files=produced_files,
            snapshot_version=snapshot.version,
            skipped_groups=len(skipped),
        )
        return {
            "ok": True,
            "job_id": job.id,
            "rewritten_files": rewritten_files,
            "produced_files": produced_files,
            "snapshot_id": snapshot.id,
        }
    except Exception as exc:  # pragma: no cover - defensive worker path
        db.rollback()
        log_event("JOB_FAILED", job_id=job_id, reason=f"{type(exc).__name__}: {exc}")
        try:
            job = db.get(CompactJob, job_id)
            if job is not None:
                job_service.mark_failed(db, job, f"{type(exc).__name__}: {exc}")
                plan = db.get(CompactPlan, job.plan_id)
                if plan is not None:
                    plan.status = PlanStatus.FAILED.value
                    db.commit()
        except Exception:
            db.rollback()
        return {"ok": False, "job_id": job_id, "reason": str(exc)}
    finally:
        if table is not None:
            try:
                release_table_lock(table.id)
            except Exception:
                pass
        db.close()
