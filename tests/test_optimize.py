from __future__ import annotations

from importlib import import_module
from pathlib import Path

prune_orphan_runtime_assets = import_module("offline_mirror.optimize").prune_orphan_runtime_assets


def test_prune_orphan_runtime_assets_removes_unreachable_js(tmp_path: Path) -> None:
    site_root = tmp_path / "offline-site"
    (site_root / "js").mkdir(parents=True)

    (site_root / "index.html").write_text(
        '<!doctype html><script type="module" src="./js/index.js"></script>',
        encoding="utf-8",
    )
    (site_root / "js" / "index.js").write_text("console.log('ok')", encoding="utf-8")
    orphan = site_root / "js" / "orphan.js"
    orphan.write_text("console.log('orphan')", encoding="utf-8")

    removed_count, _, _ = prune_orphan_runtime_assets(site_root, "https://www.qmk.top/")

    assert removed_count == 1
    assert not orphan.exists()
    assert (site_root / "js" / "index.js").exists()
