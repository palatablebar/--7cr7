"""Structured single-line logs so `docker compose logs` stays greppable."""
import json
import logging
import sys

_LOGGER = logging.getLogger("lakepack")
if not _LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False


def log_event(event: str, **fields) -> None:
    payload = {"event": event, **fields}
    _LOGGER.info(json.dumps(payload, ensure_ascii=False, default=str))
