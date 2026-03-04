from __future__ import annotations

import sys

from offline_mirror.cli import main as cli_main


def run() -> int:
    return cli_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(run())
