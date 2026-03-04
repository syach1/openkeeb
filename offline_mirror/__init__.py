from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC_PACKAGE = _HERE.parent / "src" / "offline_mirror"

if _SRC_PACKAGE.exists():
    __path__.append(str(_SRC_PACKAGE))
