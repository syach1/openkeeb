from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from offline_mirror.crawl import crawl, ensure_company_logo_aliases, verify_local_references
from offline_mirror.optimize import prune_orphan_runtime_assets
from offline_mirror.patches import apply_linux_patches


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build full offline mirror for qmk.top")
    parser.add_argument(
        "--base-url",
        default="https://www.qmk.top/",
        help="Base URL to mirror (default: https://www.qmk.top/)",
    )
    parser.add_argument(
        "--output-dir",
        default="offline-site",
        help="Output directory for the mirrored site (default: offline-site)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Retry count per URL (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=0.5,
        help="Retry delay in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--no-prune-orphans",
        action="store_true",
        help="Keep orphaned JS/image files instead of pruning unreachable runtime assets",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable live crawl progress output (progress bar or periodic status lines)",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    site_root = Path(args.output_dir).resolve()
    site_root.mkdir(parents=True, exist_ok=True)

    print(f"Mirroring {args.base_url} into {site_root} ...", flush=True)
    downloaded, discovered, failed = crawl(
        base_url=args.base_url,
        site_root=site_root,
        timeout=args.timeout,
        retries=args.retries,
        retry_delay=args.retry_delay,
        show_progress=not args.no_progress,
    )

    print(f"Downloaded files: {downloaded}", flush=True)
    print(f"Discovered URLs: {discovered}", flush=True)

    patch_notes = apply_linux_patches(site_root)
    for note in patch_notes:
        print(f"Patch: {note}", flush=True)

    alias_notes = ensure_company_logo_aliases(site_root)
    for note in alias_notes:
        print(f"Patch: {note}", flush=True)

    if args.no_prune_orphans:
        print("Optimize: Orphan pruning disabled.", flush=True)
    else:
        removed_count, removed_bytes, removed_preview = prune_orphan_runtime_assets(site_root, args.base_url)
        removed_mb = removed_bytes / (1024 * 1024)
        print(f"Optimize: Pruned orphan assets: {removed_count} files ({removed_mb:.2f} MB).", flush=True)
        if removed_preview:
            sample = ", ".join(removed_preview[:8])
            print(f"Optimize: Sample removed files: {sample}", flush=True)

    unresolved = verify_local_references(site_root, args.base_url)
    print(f"Unresolved local refs: {len(unresolved)}", flush=True)
    if unresolved:
        preview = "\n".join(unresolved[:20])
        print("First unresolved references:\n" + preview, flush=True)

    failures_path = site_root / "_mirror_failures.txt"
    if failed:
        failures_path.write_text("\n".join(failed) + "\n", encoding="utf-8")
        print(f"Failed URLs: {len(failed)} (logged to {failures_path})", flush=True)
    else:
        if failures_path.exists():
            failures_path.unlink()
        print("Failed URLs: 0", flush=True)

    # Return non-zero if there were failed downloads.
    if failed:
        return 2
    return 0
