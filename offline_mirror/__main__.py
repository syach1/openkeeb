from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

cli_main = import_module("offline_mirror.cli").main


def run(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(run())
