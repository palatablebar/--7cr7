"""Partition health bands derived from the 0-100 health score.

Formula (see services/partition_service.py):
    utilization  = min(1, avg_file_size / target_file_size)
    fragmentation = min(1, file_count / 60)
    score = round(100 * (0.65 * utilization + 0.35 * (1 - fragmentation)))
Bands: >=75 healthy, >=50 watch, else degraded.
Mirrored in frontend/src/constants/healthBand.ts.
"""
from enum import Enum


class HealthBand(str, Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    DEGRADED = "degraded"


HEALTHY_MIN = 75
WATCH_MIN = 50
FRAGMENTATION_SATURATION = 60


def band_for(score: int) -> str:
    if score >= HEALTHY_MIN:
        return HealthBand.HEALTHY.value
    if score >= WATCH_MIN:
        return HealthBand.WATCH.value
    return HealthBand.DEGRADED.value
