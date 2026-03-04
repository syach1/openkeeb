from __future__ import annotations

from pathlib import Path


ASSET_MAP: tuple[tuple[str, str], ...] = (
    ("js/offline-runtime-guard.js", "offline-runtime-guard.js"),
    ("js/theme-init.js", "theme-init.js"),
    ("js/theme-switcher.js", "theme-switcher.js"),
    ("js/theme-runtime-adapter.js", "theme-runtime-adapter.js"),
    ("assets/css/theme-overrides.css", "theme-overrides.css"),
)


def assets_root() -> Path:
    return Path(__file__).resolve().parent / "assets"


def load_asset(name: str) -> str:
    asset_path = assets_root() / name
    return asset_path.read_text(encoding="utf-8")


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if existing == content:
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def ensure_theme_assets(site_root: Path) -> list[str]:
    notes: list[str] = []
    changed = False

    for relative_output, asset_name in ASSET_MAP:
        output_path = site_root / relative_output
        content = load_asset(asset_name)
        if write_if_changed(output_path, content):
            changed = True

    if changed:
        notes.append("Ensured offline classic theme assets are present.")

    return notes
