"""Algorithm 2 — manifest snapshot diff + row-conservation / checksum audit.

输入：两版快照 manifest（path -> {size_bytes, rows, checksum, partition}）。
处理：集合差得到 added / removed；同路径但 (size,rows,checksum) 变化记 changed；
      分别校验 Σrows 是否守恒、同路径 checksum 是否一致。
输出：可审计的 diff 明细 + row_conserved / checksum mismatches 列表。
幂等判定：由 binpack 指纹比较（同一计划重跑产出相同 groups），见 plan_service。
"""
import hashlib
import json

MAX_DETAIL_ITEMS = 250


def build_manifest(files: list[dict]) -> dict:
    manifest: dict[str, dict] = {}
    for item in files:
        manifest[item["path"]] = {
            "size_bytes": int(item.get("size_bytes") or 0),
            "rows": int(item.get("row_count") or 0),
            "checksum": item.get("checksum"),
            "partition": item.get("partition_value"),
        }
    return manifest


def digest(manifest: dict) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def _entry(path: str, meta: dict | None) -> dict:
    meta = meta or {}
    return {
        "path": path,
        "size_bytes": int(meta.get("size_bytes") or 0),
        "rows": int(meta.get("rows") or 0),
        "checksum": meta.get("checksum"),
        "partition": meta.get("partition"),
    }


def diff_manifests(before: dict | None, after: dict | None) -> dict:
    before = before or {}
    after = after or {}
    before_paths = set(before)
    after_paths = set(after)

    added_paths = sorted(after_paths - before_paths)
    removed_paths = sorted(before_paths - after_paths)
    common = sorted(before_paths & after_paths)
    changed_paths = [
        path
        for path in common
        if (
            int(before[path].get("size_bytes") or 0) != int(after[path].get("size_bytes") or 0)
            or int(before[path].get("rows") or 0) != int(after[path].get("rows") or 0)
            or before[path].get("checksum") != after[path].get("checksum")
        )
    ]
    checksum_mismatches = [
        path for path in common if before[path].get("checksum") != after[path].get("checksum")
    ]

    rows_before = sum(int(meta.get("rows") or 0) for meta in before.values())
    rows_after = sum(int(meta.get("rows") or 0) for meta in after.values())
    bytes_before = sum(int(meta.get("size_bytes") or 0) for meta in before.values())
    bytes_after = sum(int(meta.get("size_bytes") or 0) for meta in after.values())

    return {
        "added": [_entry(path, after[path]) for path in added_paths[:MAX_DETAIL_ITEMS]],
        "removed": [_entry(path, before[path]) for path in removed_paths[:MAX_DETAIL_ITEMS]],
        "changed": [
            {"path": path, "before": _entry(path, before[path]), "after": _entry(path, after[path])}
            for path in changed_paths[:MAX_DETAIL_ITEMS]
        ],
        "added_count": len(added_paths),
        "removed_count": len(removed_paths),
        "changed_count": len(changed_paths),
        "file_count_before": len(before_paths),
        "file_count_after": len(after_paths),
        "file_count_delta": len(after_paths) - len(before_paths),
        "size_before_bytes": bytes_before,
        "size_after_bytes": bytes_after,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "row_delta": rows_after - rows_before,
        "row_conserved": rows_before == rows_after,
        "checksum_mismatches": checksum_mismatches[:MAX_DETAIL_ITEMS],
        "checksum_ok": len(checksum_mismatches) == 0,
        "conservation_ok": rows_before == rows_after and len(checksum_mismatches) == 0,
        "detail_truncated": any(
            count > MAX_DETAIL_ITEMS
            for count in (len(added_paths), len(removed_paths), len(changed_paths))
        ),
    }
