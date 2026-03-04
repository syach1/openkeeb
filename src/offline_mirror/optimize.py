from __future__ import annotations

from collections import deque
from pathlib import Path
from urllib.parse import urljoin

from offline_mirror.crawl import clean_url, extract_css_refs, extract_html_refs, extract_js_refs, to_local_path


PRUNE_TARGET_PREFIXES = ("js/", "assets/images/")
PRUNE_PROTECTED_PREFIXES = ("company/", "assets/fonts/")
PRUNE_PROTECTED_PATHS = {"README.md", "index.html", "CONFIG.json"}


def _collect_reachable_files(site_root: Path, base_url: str) -> set[str]:
    base_url = clean_url(base_url.rstrip("/") + "/")

    all_files = {
        file_path.relative_to(site_root).as_posix(): file_path
        for file_path in site_root.rglob("*")
        if file_path.is_file()
    }

    queue: deque[str] = deque()
    if "index.html" in all_files:
        queue.append("index.html")

    reachable: set[str] = set()
    while queue:
        rel_path = queue.popleft()
        if rel_path in reachable:
            continue

        file_path = all_files.get(rel_path)
        if file_path is None:
            continue

        reachable.add(rel_path)

        suffix = file_path.suffix.lower()
        if suffix not in {".html", ".js", ".mjs", ".css"}:
            continue

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        file_url = urljoin(base_url, rel_path)

        refs: set[str] = set()
        if suffix == ".html":
            refs |= extract_html_refs(file_url, text)
        elif suffix in {".js", ".mjs"}:
            refs |= extract_js_refs(file_url, text)
        elif suffix == ".css":
            refs |= extract_css_refs(file_url, text)

        for ref in refs:
            local_target = to_local_path(site_root, clean_url(ref))
            if local_target.exists() and local_target.is_file():
                child_rel = local_target.relative_to(site_root).as_posix()
                if child_rel not in reachable:
                    queue.append(child_rel)

    return reachable


def _remove_empty_dirs(root: Path) -> None:
    for directory in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass


def prune_orphan_runtime_assets(site_root: Path, base_url: str) -> tuple[int, int, list[str]]:
    reachable = _collect_reachable_files(site_root, base_url)
    all_files = {
        file_path.relative_to(site_root).as_posix(): file_path
        for file_path in site_root.rglob("*")
        if file_path.is_file()
    }

    orphan_rel_paths = sorted(set(all_files) - reachable)

    removed_count = 0
    removed_bytes = 0
    removed_preview: list[str] = []

    for rel_path in orphan_rel_paths:
        if rel_path in PRUNE_PROTECTED_PATHS:
            continue
        if rel_path.startswith(PRUNE_PROTECTED_PREFIXES):
            continue
        if not rel_path.startswith(PRUNE_TARGET_PREFIXES):
            continue

        target_path = all_files[rel_path]
        file_size = target_path.stat().st_size
        target_path.unlink(missing_ok=True)

        removed_count += 1
        removed_bytes += file_size
        if len(removed_preview) < 20:
            removed_preview.append(rel_path)

    _remove_empty_dirs(site_root / "js")
    _remove_empty_dirs(site_root / "assets" / "images")

    return removed_count, removed_bytes, removed_preview
