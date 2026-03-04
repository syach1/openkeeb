#!/usr/bin/env python3
"""Compatibility entrypoint for the offline mirror builder."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

main = import_module("offline_mirror.cli").main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
