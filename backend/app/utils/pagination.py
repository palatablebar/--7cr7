"""Offset pagination shared by every list endpoint."""
from typing import Iterable


def paginate(items: Iterable, offset: int = 0, limit: int = 100) -> dict:
    rows = list(items)
    total = len(rows)
    offset = max(0, int(offset or 0))
    limit = max(1, min(int(limit or 100), 500))
    return {
        "items": rows[offset : offset + limit],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
