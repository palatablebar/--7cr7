"""Algorithm 1 — partition small-file bin packing (first-fit decreasing).

输入：单分区内 size < small_file_threshold 的文件列表（path / size / rows / checksum）。
处理：每个分区独立，按 (size desc, path asc) 排序后 first-fit-decreasing 装进
     容量 target_file_size_mb 的箱；箱内 >= 2 个文件才真正重写（action=rewrite），
     单文件箱保持原样（action=carry）。输出组、产出文件数、重写字节、节省率、
     预计耗时/成本（cost_model.py），以及指纹（幂等判定依据）。
失败态：无候选文件 -> 调用方抛 LAKE-2004（本函数返回空 groups 并由上层判定）。
可复现：输入顺序无关（排序稳定），同一输入集合必得同一指纹。
"""
import hashlib
import json

from app.compaction.cost_model import CostParams, estimate_cost

COMPRESSION_RATIO = 0.97  # merged parquet is slightly denser than the sum of parts


def _fingerprint(strategy: str, target_mb: int, threshold_mb: int, partitions: list[str], groups: list[dict]) -> str:
    canonical = {
        "strategy": strategy,
        "target_mb": target_mb,
        "threshold_mb": threshold_mb,
        "partitions": sorted(partitions),
        "groups": [
            [g["partition_value"], g["action"], sorted(f["path"] for f in g["files"])]
            for g in groups
        ],
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def _pack_partition(files: list[dict], target_bytes: int) -> list[list[dict]]:
    ordered = sorted(files, key=lambda f: (-int(f["size_bytes"]), f["path"]))
    bins: list[dict] = []
    for item in ordered:
        placed = False
        for bucket in bins:
            if bucket["bytes"] + int(item["size_bytes"]) <= target_bytes:
                bucket["files"].append(item)
                bucket["bytes"] += int(item["size_bytes"])
                placed = True
                break
        if not placed:
            bins.append({"files": [item], "bytes": int(item["size_bytes"])})
    return [bucket["files"] for bucket in bins]


def build_plan(
    *,
    table: dict,
    partition_files: dict[str, list[dict]],
    strategy: str = "ffd_256",
    target_file_size_mb: int | None = None,
    hot_partitions: set[str] | None = None,
    cost_params: CostParams | None = None,
) -> dict:
    """Build the deterministic compaction plan for the selected partitions.

    ``table`` keys: db_name, table_name, partition_key, target_file_size_mb,
    small_file_threshold_mb. ``partition_files`` maps partition value to its
    DataFile dicts (keys: path, size_bytes, row_count, checksum).
    """
    hot = set(hot_partitions or set())
    threshold_mb = int(table["small_file_threshold_mb"])
    target_mb = int(target_file_size_mb or table["target_file_size_mb"])
    target_bytes = target_mb * 1024 * 1024
    threshold_bytes = threshold_mb * 1024 * 1024
    params = cost_params or CostParams()

    groups: list[dict] = []
    empty_partitions: list[str] = []
    candidate_count = 0
    rewritten_bytes = 0
    group_seq = 0

    for partition_value in sorted(partition_files.keys()):
        files = [f for f in partition_files[partition_value] if int(f["size_bytes"]) < threshold_bytes]
        if not files:
            empty_partitions.append(partition_value)
            continue
        candidate_count += len(files)
        for bucket in _pack_partition(files, target_bytes):
            group_seq += 1
            packed_bytes = sum(int(f["size_bytes"]) for f in bucket)
            rows = sum(int(f.get("row_count") or 0) for f in bucket)
            action = "rewrite" if len(bucket) > 1 else "carry"
            if action == "rewrite":
                rewritten_bytes += packed_bytes
            file_digest = hashlib.sha256(
                "|".join(sorted(f["path"] for f in bucket)).encode("utf-8")
            ).hexdigest()[:8]
            group_id = f"g{group_seq:02d}"
            output_name = f"compacted-{group_id}-{file_digest}.parquet"
            output_size = int(round(packed_bytes * COMPRESSION_RATIO)) if action == "rewrite" else packed_bytes
            groups.append(
                {
                    "group_id": group_id,
                    "partition_value": partition_value,
                    "action": action,
                    "risk": "hot" if partition_value in hot else "normal",
                    "defer_recommended": partition_value in hot,
                    "file_count": len(bucket),
                    "packed_size_bytes": packed_bytes,
                    "packed_size_mb": round(packed_bytes / (1024 * 1024), 2),
                    "fill_ratio": round(packed_bytes / target_bytes, 3),
                    "target_size_mb": target_mb,
                    "saved_files": len(bucket) - 1 if action == "rewrite" else 0,
                    "output_file": f"{_prefix(table, partition_value)}/{output_name}",
                    "output_size_bytes": output_size,
                    "output_rows": rows,
                    "files": [
                        {
                            "path": f["path"],
                            "size_bytes": int(f["size_bytes"]),
                            "size_mb": round(int(f["size_bytes"]) / (1024 * 1024), 2),
                            "row_count": int(f.get("row_count") or 0),
                            "checksum": f.get("checksum"),
                        }
                        for f in sorted(bucket, key=lambda x: x["path"])
                    ],
                }
            )

    rewrite_groups = [g for g in groups if g["action"] == "rewrite"]
    produced_files = len(groups)  # every bin becomes exactly one output object
    saved_files = candidate_count - produced_files
    cost = estimate_cost(
        rewritten_bytes=rewritten_bytes,
        candidate_file_count=candidate_count,
        saved_files=saved_files,
        params=params,
    )
    risk_flags = [
        {
            "partition_value": value,
            "code": "hot_partition",
            "severity": "warn",
            "message": f"分区 {table['partition_key']}={value} 是最新分区，上游可能仍在写入；建议延后到下游确认后再执行。",
        }
        for value in sorted(hot)
        if any(g["partition_value"] == value for g in groups)
    ]
    fingerprint = _fingerprint(strategy, target_mb, threshold_mb, sorted(partition_files.keys()), groups)

    return {
        "strategy": strategy,
        "target_file_size_mb": target_mb,
        "small_file_threshold_mb": threshold_mb,
        "partition_values": sorted(partition_files.keys()),
        "groups": groups,
        "rewrite_groups": len(rewrite_groups),
        "carried_groups": len(groups) - len(rewrite_groups),
        "candidate_file_count": candidate_count,
        "group_count": len(groups),
        "expected_output_files": produced_files,
        "saved_files": saved_files,
        "savings_pct": round((saved_files / candidate_count) * 100, 1) if candidate_count else 0.0,
        "rewritten_bytes": rewritten_bytes,
        "empty_partitions": empty_partitions,
        "risk_flags": risk_flags,
        "cost": cost,
        "fingerprint": fingerprint,
    }


def _prefix(table: dict, partition_value: str) -> str:
    bucket = table.get("bucket") or "s3://shiguang-lake"
    return (
        f"{bucket}/warehouse/{table['db_name']}/{table['table_name']}"
        f"/{table['partition_key']}={partition_value}"
    )
