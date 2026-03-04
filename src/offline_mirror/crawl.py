from __future__ import annotations

import shutil
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

try:
    from tqdm import tqdm as tqdm_factory
except ImportError:
    tqdm_factory = None

from offline_mirror.constants import (
    ALLOWED_EXTENSIONS,
    CSS_URL_RE,
    HTML_ATTR_REF_RE,
    QUOTED_PATH_RE,
    TEXT_MIME_HINTS,
)


HTML_MIME_PREFIXES = ("text/html", "application/xhtml+xml")
JAVASCRIPT_MIME_PREFIXES = ("application/javascript", "text/javascript", "application/x-javascript")
CSS_MIME_PREFIXES = ("text/css",)
HTML_SUFFIXES = {".html", ".htm"}
MAX_CONSECUTIVE_JS_SEGMENTS = 1
MAX_ASSETS_ICO_CHAIN_REPETITIONS = 1


def clean_url(raw_url: str) -> str:
    parts = urlsplit(raw_url)
    # Query is intentionally dropped for static mirrors.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def to_request_url(url: str) -> str:
    parts = urlsplit(url)
    encoded_path = quote(parts.path, safe="/%-._~!$&'()*+,;=:@")
    return urlunsplit((parts.scheme, parts.netloc, encoded_path, parts.query, parts.fragment))


def to_local_path(site_root: Path, url: str) -> Path:
    parts = urlsplit(url)
    path = parts.path or "/"
    if path.endswith("/"):
        path = path + "index.html"
    rel = path.lstrip("/")
    if not rel:
        rel = "index.html"
    return site_root / rel


def media_type_from_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def sniff_payload_content_type(payload: bytes) -> str:
    sample = payload[:4096].decode("utf-8", errors="ignore").lstrip("\ufeff\r\n\t ")
    lowered = sample.lower()
    if lowered.startswith("<!doctype html") or lowered.startswith("<html"):
        return "text/html"
    if "<html" in lowered[:512]:
        return "text/html"
    return ""


def infer_content_type(path: Path, payload: bytes, content_type_hint: str) -> str:
    hinted = media_type_from_content_type(content_type_hint)
    if hinted:
        return content_type_hint.lower()

    sniffed = sniff_payload_content_type(payload)
    if sniffed:
        return sniffed

    return guess_content_type_from_suffix(path)


def has_recursive_segment(path: str, segment: str, *, max_consecutive: int = 1) -> bool:
    consecutive = 0
    for part in (chunk for chunk in path.split("/") if chunk):
        if part == segment:
            consecutive += 1
            if consecutive > max_consecutive:
                return True
        else:
            consecutive = 0
    return False


def has_repeated_segment_pattern(path: str, pattern: tuple[str, ...], *, max_repetitions: int = 1) -> bool:
    if not pattern:
        return False

    parts = [part for part in path.split("/") if part]
    pattern_len = len(pattern)
    index = 0

    while index <= len(parts) - pattern_len:
        if tuple(parts[index : index + pattern_len]) != pattern:
            index += 1
            continue

        repetitions = 1
        cursor = index + pattern_len
        while cursor <= len(parts) - pattern_len:
            if tuple(parts[cursor : cursor + pattern_len]) != pattern:
                break
            repetitions += 1
            cursor += pattern_len

        if repetitions > max_repetitions:
            return True

        index = cursor

    return False


def initial_seed_urls(base_url: str) -> set[str]:
    return {clean_url(base_url.rstrip("/") + "/")}


def determine_reference_kind(path: Path, content_type: str) -> str | None:
    suffix = path.suffix.lower()
    media_type = media_type_from_content_type(content_type)

    if any(media_type.startswith(prefix) for prefix in HTML_MIME_PREFIXES):
        if suffix not in HTML_SUFFIXES:
            return None
        return "html"

    if any(media_type.startswith(prefix) for prefix in JAVASCRIPT_MIME_PREFIXES):
        return "js"

    if any(media_type.startswith(prefix) for prefix in CSS_MIME_PREFIXES):
        return "css"

    if suffix == ".html":
        return "html"
    if suffix in {".js", ".mjs"}:
        return "js"
    if suffix == ".css":
        return "css"

    return None


def should_keep_url(base_netloc: str, absolute_url: str) -> bool:
    parts = urlsplit(absolute_url)
    if parts.scheme not in {"http", "https"}:
        return False
    if parts.netloc and parts.netloc != base_netloc:
        return False

    path = parts.path or "/"
    if has_recursive_segment(path, "js", max_consecutive=MAX_CONSECUTIVE_JS_SEGMENTS):
        return False
    if has_repeated_segment_pattern(
        path,
        ("assets", "ico"),
        max_repetitions=MAX_ASSETS_ICO_CHAIN_REPETITIONS,
    ):
        return False

    if path.endswith("/"):
        return True

    suffix = Path(path).suffix.lower()
    if suffix in ALLOWED_EXTENSIONS:
        return True

    # Keep root-like entries such as /index or /app if ever used.
    if suffix == "" and path.count("/") <= 2:
        return True

    return False


def parse_text_payload(payload: bytes) -> str:
    return payload.decode("utf-8", errors="ignore")


def normalize_ref(ref: str) -> str:
    ref = ref.strip().strip('"').strip("'")
    if not ref:
        return ""
    # Normalize JS escaped slash variants.
    ref = ref.replace("\\/", "/")
    ref = ref.replace("\\", "/")
    return ref


def extract_html_refs(current_url: str, text: str) -> set[str]:
    refs: set[str] = set()
    for match in HTML_ATTR_REF_RE.findall(text):
        ref = normalize_ref(match)
        if not ref or ref.startswith(("data:", "blob:", "javascript:", "mailto:", "#")):
            continue
        refs.add(urljoin(current_url, ref))
    return refs


def extract_js_refs(current_url: str, text: str) -> set[str]:
    refs: set[str] = set()
    for match in QUOTED_PATH_RE.findall(text):
        ref = normalize_ref(match)
        if not ref:
            continue
        refs.add(urljoin(current_url, ref))
    return refs


def extract_css_refs(current_url: str, text: str) -> set[str]:
    refs: set[str] = set()
    for raw in CSS_URL_RE.findall(text):
        ref = normalize_ref(raw)
        if not ref or ref.startswith(("data:", "blob:", "#")):
            continue
        refs.add(urljoin(current_url, ref))
    return refs


def extract_references_from_payload(
    current_url: str,
    local_path: Path,
    payload: bytes,
    content_type: str,
) -> set[str]:
    if not is_text_file(local_path, content_type):
        return set()

    reference_kind = determine_reference_kind(local_path, content_type)
    if reference_kind is None:
        return set()

    text = parse_text_payload(payload)
    if reference_kind == "html":
        return extract_html_refs(current_url, text)
    if reference_kind == "js":
        return extract_js_refs(current_url, text)
    if reference_kind == "css":
        return extract_css_refs(current_url, text)
    return set()


def fetch(url: str, timeout: float, retries: int, retry_delay: float) -> tuple[bytes, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    }

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(to_request_url(url), headers=headers)
            with urlopen(request, timeout=timeout) as response:
                content = response.read()
                content_type = response.headers.get("Content-Type", "").lower()
                return content, content_type
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(retry_delay)

    assert last_error is not None
    raise last_error


def is_text_file(path: Path, content_type: str) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".html", ".js", ".mjs", ".css", ".json", ".map"}:
        return True
    return any(content_type.startswith(hint) for hint in TEXT_MIME_HINTS)


def guess_content_type_from_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".html"}:
        return "text/html"
    if suffix in {".js", ".mjs"}:
        return "application/javascript"
    if suffix in {".css"}:
        return "text/css"
    if suffix in {".json", ".map"}:
        return "application/json"
    return ""


def create_progress_bar(show_progress: bool, initial_total: int) -> Any | None:
    if not show_progress or tqdm_factory is None or not sys.stderr.isatty():
        return None
    return tqdm_factory(
        total=initial_total,
        desc="Crawling",
        unit="url",
        dynamic_ncols=True,
        mininterval=0.1,
    )


def report_progress(
    progress_bar: Any | None,
    *,
    processed: int,
    discovered: int,
    downloaded: int,
    failed_count: int,
    queued_count: int,
) -> None:
    if progress_bar is None:
        if processed % 200 == 0:
            print(
                "Processed "
                f"{processed}/{discovered} queued URLs, "
                f"fetched {downloaded} files, "
                f"failed {failed_count}, "
                f"pending {queued_count}...",
                flush=True,
            )
        return

    if progress_bar.total is None or discovered > progress_bar.total:
        progress_bar.total = discovered
        progress_bar.refresh()
    progress_bar.update(1)
    progress_bar.set_postfix(
        {
            "fetched": downloaded,
            "failed": failed_count,
            "queued": queued_count,
        },
        refresh=False,
    )


def crawl(
    base_url: str,
    site_root: Path,
    timeout: float,
    retries: int,
    retry_delay: float,
    *,
    show_progress: bool = True,
) -> tuple[int, int, list[str]]:
    base_url = clean_url(base_url.rstrip("/") + "/")
    base_parts = urlsplit(base_url)
    base_netloc = base_parts.netloc

    # Seed with landing page only, then discover active entrypoints from HTML.
    seed = initial_seed_urls(base_url)
    queue: deque[str] = deque(sorted(seed))

    seen: set[str] = set()
    failed: list[str] = []
    downloaded = 0
    discovered = len(seed)
    processed = 0
    progress_bar = create_progress_bar(show_progress=show_progress, initial_total=discovered)

    try:
        while queue:
            url = queue.popleft()
            processed += 1
            url = clean_url(url)
            if url in seen:
                report_progress(
                    progress_bar,
                    processed=processed,
                    discovered=discovered,
                    downloaded=downloaded,
                    failed_count=len(failed),
                    queued_count=len(queue),
                )
                continue
            seen.add(url)

            local_path = to_local_path(site_root, url)
            if local_path.exists() and local_path.stat().st_size > 0:
                payload = local_path.read_bytes()
                content_type = infer_content_type(local_path, payload, "")
            else:
                try:
                    payload, content_type = fetch(url, timeout=timeout, retries=retries, retry_delay=retry_delay)
                except Exception as exc:  # noqa: BLE001
                    failed.append(f"{url} :: {exc}")
                    report_progress(
                        progress_bar,
                        processed=processed,
                        discovered=discovered,
                        downloaded=downloaded,
                        failed_count=len(failed),
                        queued_count=len(queue),
                    )
                    continue

                content_type = infer_content_type(local_path, payload, content_type)

                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(payload)
                downloaded += 1

            if not is_text_file(local_path, content_type):
                report_progress(
                    progress_bar,
                    processed=processed,
                    discovered=discovered,
                    downloaded=downloaded,
                    failed_count=len(failed),
                    queued_count=len(queue),
                )
                continue

            refs = extract_references_from_payload(url, local_path, payload, content_type)

            for ref in refs:
                cleaned = clean_url(ref)
                if not should_keep_url(base_netloc, cleaned):
                    continue
                if cleaned not in seen:
                    queue.append(cleaned)
                    discovered += 1

            report_progress(
                progress_bar,
                processed=processed,
                discovered=discovered,
                downloaded=downloaded,
                failed_count=len(failed),
                queued_count=len(queue),
            )
    finally:
        if progress_bar is not None:
            progress_bar.close()

    return downloaded, discovered, failed


def verify_local_references(site_root: Path, base_url: str) -> list[str]:
    """Return unresolved local static references after crawl."""
    base_url = clean_url(base_url.rstrip("/") + "/")
    base_netloc = urlsplit(base_url).netloc
    unresolved: set[str] = set()
    queue: deque[str] = deque([base_url])
    seen_urls: set[str] = set()

    while queue:
        url = clean_url(queue.popleft())
        if url in seen_urls:
            continue
        seen_urls.add(url)

        local_path = to_local_path(site_root, url)
        if not local_path.exists() or not local_path.is_file():
            unresolved.add(f"missing root reference -> {url}")
            continue

        payload = local_path.read_bytes()
        content_type = infer_content_type(local_path, payload, "")
        refs = extract_references_from_payload(url, local_path, payload, content_type)
        rel = local_path.relative_to(site_root).as_posix()

        for ref in refs:
            cleaned = clean_url(ref)
            if not should_keep_url(base_netloc, cleaned):
                continue

            local_target = to_local_path(site_root, cleaned)
            if not local_target.exists():
                unresolved.add(f"{rel} -> {cleaned}")
                continue

            if cleaned not in seen_urls:
                queue.append(cleaned)

    return sorted(unresolved)


def ensure_company_logo_aliases(site_root: Path) -> list[str]:
    """Ensure company logo paths used by web build exist locally."""
    notes: list[str] = []

    topnav_src = site_root / "topnav_logo.png"
    login_src = site_root / "login_logo.png"

    if not topnav_src.exists() and not login_src.exists():
        return notes

    company_aliases = ["EWEADNV", "EPOMAKER", "undefined"]
    copies_made = 0

    for company in company_aliases:
        company_dir = site_root / "company" / f"company_{company}"
        company_dir.mkdir(parents=True, exist_ok=True)

        if topnav_src.exists():
            for filename in ("topnav_logo.png", "default_logo.png"):
                target = company_dir / filename
                shutil.copy2(topnav_src, target)
                copies_made += 1

        if login_src.exists():
            target = company_dir / "login_logo.png"
            shutil.copy2(login_src, target)
            copies_made += 1

    if copies_made > 0:
        notes.append("Ensured company/company_* logo aliases for offline web UI assets.")

    return notes
