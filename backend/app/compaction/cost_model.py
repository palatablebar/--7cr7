"""Rewrite cost / duration model.

Documented口径 (also printed in the plan detail panel):

  transfer_seconds = rewritten_bytes / (bandwidth_mb_per_s * 1024 * 1024)
  overhead_seconds = per_file_overhead_s * candidate_file_count
  est_duration_s   = transfer_seconds + overhead_seconds
  rewrite_gb       = rewritten_bytes / 1024^3
  est_cost_yuan    = rewrite_gb * unit_cost_per_gb
  monthly_saving   = saved_files * cost_per_file_day * 30
  payback_days     = est_cost_yuan / (monthly_saving / 30)   (None if no saving)

The defaults live in app/config/settings.py and are overridable per deployment.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CostParams:
    bandwidth_mb_per_s: float = 80.0
    per_file_overhead_s: float = 0.3
    unit_cost_per_gb: float = 0.85
    cost_per_file_day: float = 0.0004


def estimate_cost(
    *,
    rewritten_bytes: int,
    candidate_file_count: int,
    saved_files: int,
    params: CostParams,
) -> dict:
    rewrite_gb = max(0.0, rewritten_bytes) / (1024**3)
    transfer_seconds = max(0.0, rewritten_bytes) / (params.bandwidth_mb_per_s * 1024 * 1024)
    overhead_seconds = params.per_file_overhead_s * max(0, candidate_file_count)
    duration = transfer_seconds + overhead_seconds
    est_cost = rewrite_gb * params.unit_cost_per_gb
    monthly_saving = max(0, saved_files) * params.cost_per_file_day * 30
    daily_saving = monthly_saving / 30
    payback_days = round(est_cost / daily_saving, 1) if daily_saving > 0 else None

    return {
        "bandwidth_mb_per_s": params.bandwidth_mb_per_s,
        "per_file_overhead_s": params.per_file_overhead_s,
        "unit_cost_per_gb": params.unit_cost_per_gb,
        "cost_per_file_day": params.cost_per_file_day,
        "rewrite_gb": round(rewrite_gb, 4),
        "transfer_seconds": round(transfer_seconds, 2),
        "overhead_seconds": round(overhead_seconds, 2),
        "est_duration_seconds": round(duration, 1),
        "est_cost_yuan": round(est_cost, 2),
        "monthly_saving_yuan": round(monthly_saving, 2),
        "payback_days": payback_days,
    }
