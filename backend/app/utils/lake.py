"""Object-storage path helpers. The demo never talks to S3: it materialises the
same logical layout (`s3://bucket/warehouse/db/table/partition/...`) as DataFile
paths so the metadata story stays faithful. See README §simulation boundary."""
import hashlib
import json

from app.config.settings import settings


def table_prefix(db_name: str, table_name: str) -> str:
    return f"{settings.LAKE_BUCKET}/warehouse/{db_name}/{table_name}"


def partition_path(db_name: str, table_name: str, partition_key: str, partition_value: str) -> str:
    return f"{table_prefix(db_name, table_name)}/{partition_key}={partition_value}"


def checksum_of(*parts) -> str:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def digest_manifest(manifest: dict) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
