"""Numeric presentation helpers used by the API payloads (bytes are kept raw
for machines; these labels are convenience fields for the UI)."""


def fmt_bytes(num_bytes: float) -> str:
    value = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024 or unit == "TB":
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{value:.1f}TB"


def mb(num_bytes: float) -> float:
    return round(float(num_bytes or 0) / (1024 * 1024), 2)


def gb(num_bytes: float) -> float:
    return round(float(num_bytes or 0) / (1024 * 1024 * 1024), 4)
