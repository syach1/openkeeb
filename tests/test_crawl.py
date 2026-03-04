from __future__ import annotations

from importlib import import_module
from pathlib import Path

crawl = import_module("offline_mirror.crawl")
clean_url = crawl.clean_url
determine_reference_kind = crawl.determine_reference_kind
initial_seed_urls = crawl.initial_seed_urls
media_type_from_content_type = crawl.media_type_from_content_type
sniff_payload_content_type = crawl.sniff_payload_content_type
should_keep_url = crawl.should_keep_url
to_local_path = crawl.to_local_path
verify_local_references = crawl.verify_local_references


def test_clean_url_drops_query_and_fragment() -> None:
    assert clean_url("https://www.qmk.top/js/app.js?x=1#k") == "https://www.qmk.top/js/app.js"


def test_to_local_path_maps_root_to_index_html(tmp_path: Path) -> None:
    out = to_local_path(tmp_path, "https://www.qmk.top/")
    assert out == tmp_path / "index.html"


def test_should_keep_url_only_allows_same_host_assets() -> None:
    assert should_keep_url("www.qmk.top", "https://www.qmk.top/js/index.js")
    assert not should_keep_url("www.qmk.top", "https://example.com/js/index.js")


def test_initial_seed_urls_only_uses_base_landing_page() -> None:
    assert initial_seed_urls("https://www.qmk.top") == {"https://www.qmk.top/"}


def test_should_keep_url_rejects_recursive_js_segments() -> None:
    assert not should_keep_url("www.qmk.top", "https://www.qmk.top/js/js/index.f14a36ae.js")


def test_should_keep_url_rejects_repeated_assets_ico_chain() -> None:
    assert not should_keep_url(
        "www.qmk.top",
        "https://www.qmk.top/assets/css/font/assets/ico/assets/ico/favicon.f2182f19.ico",
    )


def test_media_type_from_content_type_strips_charset() -> None:
    assert media_type_from_content_type("text/html; charset=utf-8") == "text/html"


def test_sniff_payload_content_type_detects_html() -> None:
    payload = b"\n\n<!DOCTYPE html><html><head></head><body></body></html>"
    assert sniff_payload_content_type(payload) == "text/html"


def test_determine_reference_kind_skips_html_fallback_on_js_path() -> None:
    kind = determine_reference_kind(Path("index.fallback.js"), "text/html; charset=utf-8")
    assert kind is None


def test_determine_reference_kind_skips_html_fallback_on_ico_path() -> None:
    kind = determine_reference_kind(Path("favicon.f2182f19.ico"), "text/html; charset=utf-8")
    assert kind is None


def test_determine_reference_kind_prefers_content_type_when_available() -> None:
    assert determine_reference_kind(Path("styles.css"), "application/javascript") == "js"


def test_verify_local_references_scans_only_reachable_runtime_files(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<!doctype html><html><head><script type="module" src="./js/index.f14a36ae.js"></script></head></html>',
        encoding="utf-8",
    )

    js_dir = tmp_path / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "index.f14a36ae.js").write_text('const a="./missing.js";', encoding="utf-8")

    poisoned_dir = tmp_path / "assets" / "css" / "font" / "assets" / "ico"
    poisoned_dir.mkdir(parents=True)
    (poisoned_dir / "index.f14a36ae.js").write_text(
        'const x="./assets/ico/favicon.f2182f19.ico";',
        encoding="utf-8",
    )

    unresolved = verify_local_references(tmp_path, "https://www.qmk.top/")

    assert any(entry.endswith("js/index.f14a36ae.js -> https://www.qmk.top/js/missing.js") for entry in unresolved)
    assert not any(entry.startswith("assets/css/font/") for entry in unresolved)
