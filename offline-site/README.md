# offline-site

This directory is generated runtime output for the local offline mirror.

- Rebuild command: `python build_offline_mirror.py --output-dir offline-site`
- Serve command: `./run_offline.sh` (or `./run_offline.sh <port>`) via `scripts/run_offline.sh`
- Do not treat files here as primary source code.
- Any manual edits inside `offline-site/` may be overwritten by rebuilds.
- Runtime offline guard: `js/offline-runtime-guard.js` (blocks non-local network/navigation calls).
- Builder prunes unreachable stale files in `js/` and `assets/images/` by default.

Primary source code for the builder now lives in `src/offline_mirror/`.
Optional raw capture/helper artifacts can be stored in `archive/raw/` when needed.
