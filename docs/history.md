# OpenKeeb Offline Linux History

Date started: 2026-02-25

Former project name: `reverse-zap68`

## Goal

Make the `www.qmk.top` web driver work reliably offline on Linux (localhost + WebHID), without requiring the Windows/Mac IOT driver app.

## What we did (chronological)

1. Reviewed initial artifacts.
   - Inspected `www.qmk.top.har` and `might-help/` contents.
   - Confirmed the app is chunk-heavy and original HAR alone is incomplete for full offline use.

2. Built a full offline mirror pipeline.
   - Created `build_offline_mirror.py`.
   - Implemented recursive discovery for HTML/JS/CSS references.
   - Added URL normalization and extension filtering for static assets.
   - Added retry handling and partial-resume behavior (skip existing downloaded files).

3. Fixed Unicode URL fetching in the mirror builder.
   - Added path quoting/encoding (`to_request_url`) so non-ASCII file paths download correctly.

4. Added offline integrity checks.
   - Added unresolved local reference verification (`verify_local_references`).
   - Mirror reached full local reference coverage during validation.

5. Generated offline app output.
   - Created/updated `offline-site/` with full mirrored assets/chunks.
   - Final mirror result was large (thousands of files, hundreds of MB).

6. Added local run tooling.
   - Created `run_offline.sh` for localhost serving.
   - Created `README-LINUX-OFFLINE.md` with Linux/WebHID run instructions.

7. Patched Linux IOT switch behavior in bundled app JS.
   - File: `offline-site/js/index.1c916957.js`
   - Patched `setIOTSwitch` and `getIOTSwitch` logic so Linux stays on WebHID path (IOT disabled by default like "other").

8. Investigated old-driver popup after refresh and patched fallback behavior.
   - File: `offline-site/js/index.1c916957.js`
   - Changed `DEVICE_NOT_SUPPORTED` handling so old-driver modal is only shown when IOT SDK mode is actually enabled.
   - In WebHID mode, unsupported-device event no longer forces old-driver popup.

9. Investigated "device connected but page does not advance" state.
   - Found that ID mapping path filtered out company `EWEADNV`, which blocked add-device event propagation in web offline flow.
   - Patched company filter to allow `EWEADNV` through that mapping path.
   - This unblocked ZAP68-family onboarding in the offline WebHID route.

10. Made patches persistent in rebuild workflow.
    - Updated `build_offline_mirror.py` (`apply_linux_patches`) to apply all runtime fixes automatically:
      - Linux WebHID default patch
      - DEVICE_NOT_SUPPORTED modal suppression in WebHID mode
      - EWEADNV mapping allowance

11. Updated documentation after each fix.
    - `README-LINUX-OFFLINE.md` now documents:
      - Linux patch behavior
      - stale localStorage/site data warning
      - recommendation to use Incognito or clear site data when retesting

12. Validation checks performed.
    - Verified required patch strings in `offline-site/js/index.1c916957.js`.
    - Verified `build_offline_mirror.py` syntax (`python -m py_compile build_offline_mirror.py`).

13. Audited and constrained network egress for offline safety.
    - Scanned mirrored assets for absolute `http/https` URLs and confirmed many hardcoded online endpoints still exist in optional/cloud code paths.
    - Added strict CSP in `offline-site/index.html` to allow only self/localhost network access and block online hosts.
    - Updated `build_offline_mirror.py` so CSP is auto-applied on future rebuilds.
    - Updated `run_offline.sh` to bind server to `127.0.0.1` only.

14. Cleaned up runtime console issues after CSP rollout.
    - Removed unsupported/ignored CSP directives for meta-delivered CSP (`frame-ancestors`, `navigate-to`) to eliminate browser warnings.
    - Patched company asset path helper to avoid `company/company_undefined` fallback when company is missing (`eo(e ?? Ya.currentCompany)`).
    - Added/persisted logo alias generation to `offline-site/company/company_*/` for `EWEADNV`, `EPOMAKER`, and `undefined` so `topnav_logo.png` / `login_logo.png` resolve reliably.
    - Patched WebHID mode to skip localhost IOT manager version fetches (`Kt.getVersion`) so `:6015/.../GetVersion` connection-refused noise is avoided when IOT mode is disabled.

15. Removed irrelevant external links from offline UI.
    - Hid footer section that presented outside-site links in web mode.
    - Neutralized legacy footer `window.open(...)` URL targets (`beian.miit.gov.cn`, `qmk.top/gear-lab`) to local placeholders.
    - Neutralized old-driver and installer URL properties (`iotdriver.*`, `news.rongyuan.tech`, `aka.ms`) to local placeholders.
    - Persisted these changes in `build_offline_mirror.py` patch workflow.

16. Removed AI helper floating widget from runtime UI.
    - Disabled the AI helper lazy import path in `offline-site/js/index.1c916957.js` by replacing the `AiFloat` lazy loader with a no-op component.
    - Disabled the AI floating-button render path condition so the bottom-right "Need help" bubble no longer appears.
    - Deleted stale widget files from offline output (`offline-site/js/0afe9811.js` and `offline-site/assets/css/AiFloat.db6806a6.css`).
    - Persisted all of the above in `build_offline_mirror.py` so future mirrors keep the widget removed.

17. Added modern UI theme system with default matte-dark profile.
    - Added offline theme bootstrap (`offline-site/js/theme-init.js`) that defaults to `matte-dark` and persists user choice.
    - Added runtime theme selector dropdown (`offline-site/js/theme-switcher.js`) with `Matte Dark` and `Classic` options.
    - Added style layer (`offline-site/assets/css/theme-overrides.css`) implementing material matte dark look with subtle cyan/electric-blue glow.
    - Updated `offline-site/index.html` to load the theme bootstrap, theme stylesheet, and switcher script.
    - Persisted theme asset generation and HTML hook injection in `build_offline_mirror.py` for rebuild safety.

18. Improved matte-dark coverage inside inner pages.
    - Added runtime style adapter (`offline-site/js/theme-runtime-adapter.js`) to remap legacy hardcoded inline colors to theme variables at DOM/runtime level.
    - Hooked runtime adapter into `index.html` and rebuild pipeline so theme changes propagate beyond the welcome/device-selection surface.
    - Re-synced JS chunks from upstream mirror source and re-applied Linux/offline/runtime patches to keep behavior and compatibility intact.

19. Stabilized theme rollout after deeper-page validation.
    - User reported that only the device-selection surface changed theme while inner pages still looked classic.
    - Expanded runtime adapter usage and verified it is loaded after the main app bundle.
    - A broad one-off color replacement attempt across all JS chunks was rolled back by restoring affected chunk files from upstream, then reapplying the official patch pipeline.
    - Added a regex fallback in `build_offline_mirror.py` for AI widget lazy-import removal so future bundle signature drift does not reintroduce `0afe9811.js` references.
    - Re-verified mirror integrity (`verify_local_references` unresolved count returned to `0`).

20. Hardened permanent removal enforcement for AI widget and external links.
    - Added `PERMANENT_BLOCKED_MARKERS` + runtime-file scanning in `build_offline_mirror.py` to enforce stripping of:
      - AI helper markers/chunk references (`AiFloat`, `0afe9811.js`, old render condition markers)
      - External footer/download link domains (`beian.miit.gov.cn`, `qmk.top/gear-lab`, `iotdriver.*`, `news.rongyuan.tech`, `aka.ms`)
    - Rebuild now fails with a hard error if blocked markers are still present in mirrored runtime HTML/JS/CSS files.

21. Rebuilt and smoke-tested permanent stripping enforcement.
    - Ran `python build_offline_mirror.py` successfully against current output (incremental run: `Downloaded files: 0`, `Discovered URLs: 4904`, `Unresolved local refs: 0`, `Failed URLs: 0`).
    - Confirmed enforcement note: `Verified AI helper and external links are permanently stripped from runtime files.`
    - Launched localhost server and confirmed app shell responds (`HTTP 200` at `http://127.0.0.1:4173/`).
    - Re-scanned runtime files and confirmed no matches for blocked AI/widget markers (`AiFloat`, `0afe9811.js`) or blocked external domains (`beian.miit.gov.cn`, `qmk.top/gear-lab`, `iotdriver.*`, `news.rongyuan.tech`, `aka.ms`).

22. Refactored tooling layout and archived raw artifacts for cleaner repository structure.
    - Split the monolithic mirror builder into modular package files under `offline_mirror/` (`cli.py`, `crawl.py`, `patches.py`, `constants.py`, `theme_assets.py`) while keeping `build_offline_mirror.py` as a compatibility entrypoint.
    - Moved theme payload sources out of Python string literals into `offline_mirror/assets/` and updated patch flow to consume these files.
    - Archived non-runtime raw artifacts to `archive/raw/` (including `www.qmk.top.har` and `might-help/`) instead of deleting them.
    - Added `.gitignore` for transient Python/cache outputs.

23. Marked runtime mirror folder as generated output.
    - Added `offline-site/README.md` documenting that `offline-site/` is build output and may be overwritten on rebuild.
    - Linked this generated-output note from `README-LINUX-OFFLINE.md`.

24. Hardened offline enforcement after full runtime URL audit.
    - Audited runtime text assets under `offline-site/` for non-local URL hosts and identified remaining cloud API base URLs in the main bundle.
    - Extended patching to rewrite cloud API base URLs (`api*.rongyuan.tech`, `api2.qmk.top`) to local `/offline-disabled/*` placeholders.
    - Added runtime offline guard asset (`offline-runtime-guard.js`) and injected it in `index.html` before the main bundle.
    - Guard now blocks non-local `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon`, `window.open`, and anchor navigation at runtime.
    - Extended permanent blocked-marker enforcement list so rebuild fails if cloud API domains reappear in runtime files.

25. Added runtime asset pruning and compression-aware local serving.
    - Added orphan-pruning step in builder to remove unreachable files under `offline-site/js/` and `offline-site/assets/images/`.
    - Added `--no-prune-orphans` flag for troubleshooting cases where a full mirror snapshot is preferred.
    - Added `serve_offline.py`, a local-only HTTP server with on-the-fly brotli/gzip for compressible text assets.
    - Updated `run_offline.sh` to launch the new compression-aware server instead of `python -m http.server`.

26. Disabled More-tab firmware upgrade and IOT-enable actions.
    - Patched More-tab runtime chunks to disable the `Firmware Upgrade` button action.
    - Patched More-tab IOT toggle so `Enable IOT Driver` cannot be triggered when IOT mode is currently off.
    - Persisted this behavior in `offline_mirror/patches.py` so future rebuilds keep these actions disabled.

27. Updated Linux README guidance for local WebHID permissions.
    - Added a dedicated `udev` setup section to `README-LINUX-OFFLINE.md` for Linux users.
    - Documented ZAP68-family vendor ID (`3151`) with a copy-paste-ready rule template for `hidraw` access.
    - Added rule reload/apply commands (`udevadm control --reload-rules` + `udevadm trigger`) and replug/browser-restart guidance.
    - Added a Snap Chromium caveat note to avoid common WebHID permission failures on Ubuntu.

28. Added git-push-ready project scaffolding at repository root.
    - Added root `README.md` with quick-start commands, source/generated folder guidance, and doc links.
    - Added `LICENSE` (MIT), `pyproject.toml`, and package module entrypoint `offline_mirror/__main__.py`.
    - Added Python package script entrypoints (`offline-mirror-build`, `offline-mirror-serve`) in `pyproject.toml`.
    - Expanded `.gitignore` to cover Python/tool caches and generated runtime/archive content while keeping `offline-site/README.md` tracked.

29. Consolidated Linux/offline documentation into root README.
    - Merged the full Linux offline run + WebHID `udev` guidance into `README.md` as the comprehensive primary document.
    - Converted `README-LINUX-OFFLINE.md` into a compatibility alias that points readers to `README.md`.
    - Kept path-level doc references (`history.md`, `offline-site/README.md`, `archive/README.md`) in the root README for maintainability.

30. Applied the suggested final repository structure.
    - Moved Python package sources to `src/offline_mirror/` (including assets) and switched to setuptools `src` layout in `pyproject.toml`.
    - Moved server implementation to `src/offline_mirror/server.py`; kept root `build_offline_mirror.py` and `serve_offline.py` as compatibility entrypoints.
    - Moved launcher script to `scripts/run_offline.sh` and kept root `run_offline.sh` as a compatibility wrapper.
    - Moved canonical work log to `docs/history.md` and kept root `history.md` as a compatibility alias.
    - Added baseline tests under `tests/` and GitHub Actions CI workflow at `.github/workflows/ci.yml`.

31. Removed non-related/generated local artifacts from the workspace.
    - Deleted generated runtime payload files under `offline-site/` while keeping `offline-site/README.md`.
    - Removed `archive/raw/` capture dumps and local `__pycache__/` directories.
    - Removed local `.venv/` from the repository workspace and switched test validation to temporary environments.
    - Updated docs to describe `archive/raw/` as optional local diagnostics storage.

32. Added balanced egress and CSP validation gates to the patch pipeline.
    - Introduced build-time `connect-src` validation to enforce localhost-only network policy in runtime CSP.
    - Added balanced external-host auditing for runtime files (blocked vendor suffixes fail builds, reference-only allowlist remains permitted).
    - Wired these checks into `apply_linux_patches` so regressions fail fast during rebuild.

33. Made runtime patching resilient to bundle hash/minifier drift.
    - Switched active bundle targeting to resolve from `index.html` instead of relying on sorted `index.*.js` names.
    - Added regex-based fallbacks for AI widget removal, old-driver popup suppression, footer external-link hiding, and EWEADNV mapping allowance.
    - Added enforcement checks that fail builds if unguarded old-driver modal logic or visible external footer-link sections reappear.
    - Expanded AI artifact cleanup to remove dynamically detected lazy-import chunk/css paths.

34. Fixed crawler recursion/path-poisoning edge cases and stale failure logs.
    - Removed hardcoded legacy entry-script seed; crawler now seeds from landing page only.
    - Added content-type-aware parsing so HTML fallback payloads on non-HTML asset paths are ignored for reference extraction.
    - Added URL recursion guards for repeated `js/js/...` and `assets/ico/assets/ico/...` chain patterns.
    - Updated CLI to clear stale `_mirror_failures.txt` on successful runs.

35. Updated unresolved-reference verification to reachable-runtime scope.
    - Reworked `verify_local_references` into a reachable graph walk from `index.html` instead of scanning every file in output.
    - This avoids false positives from poisoned/orphan paths while still surfacing real missing assets used by the live runtime.
    - Fresh full mirror builds now complete with `Unresolved local refs: 0` and `Failed URLs: 0` in clean output directories.

36. Applied safe public rebrand to OpenKeeb and improved newcomer onboarding.
    - Updated root README branding to `OpenKeeb` while keeping legacy internal naming for compatibility.
    - Rewrote README quick start with beginner-friendly step-by-step clone/install/build/run instructions.
    - Added OpenKeeb CLI aliases (`openkeeb-build`, `openkeeb-serve`) while retaining legacy command aliases.

## Current status

- User-confirmed: "everything seems works for now".
- Offline Linux WebHID flow is currently working for the target device.
- Offline page now enforces CSP egress restrictions (self/localhost only).
- Console warning/error cleanup patches are applied for CSP/logo/IOT-version-check paths.
- Irrelevant external footer links are removed from interface in offline mode.
- AI helper floating widget and its online-link menu are removed from the active runtime path.
- AI helper/external-link removals are now enforced by build-time marker scanning (rebuild fails if they reappear).
- Latest rebuild + localhost smoke test passed (HTTP 200), with permanent AI/external-link stripping still enforced.
- Theme system now defaults to `Matte Dark`, while preserving a switchable `Classic` mode.
- Matte-dark style now applies across deeper UI surfaces through runtime color adaptation.
- Patch pipeline has been re-synced after theme stabilization and remains rebuild-safe.
- Builder code is now modularized under `src/offline_mirror/`, with `build_offline_mirror.py` preserved as a stable entrypoint.
- Non-related/generated workspace artifacts were removed; `archive/raw/` is now optional local-only diagnostics storage.
- `offline-site/` now includes a local README marking it as generated runtime output.
- Runtime now has layered offline controls: CSP egress restrictions, cloud API URL neutralization, and a JS offline guard for non-local network/navigation calls.
- Build now performs low-risk orphan cleanup for stale JS/image artifacts, and local serving uses HTTP compression for faster chunk transfer.
- More-tab `Firmware Upgrade` and `Enable IOT Driver` actions are now disabled in runtime output.
- README now includes Linux `udev` setup guidance for WebHID (`hidraw`) permissions, including ZAP68-family vendor-ID examples.
- README now warns that Snap Chromium may block `hidraw` access even when udev rules are correct.
- Root repository now includes baseline project metadata/docs (`README.md`, `LICENSE`, `pyproject.toml`) for cleaner sharing and future git push.
- Root `README.md` is now the single comprehensive Linux/offline guide; `README-LINUX-OFFLINE.md` is retained as a compatibility pointer only.
- Suggested target structure is now in place (`src/`, `scripts/`, `docs/`, `tests/`, `.github/workflows/`).
- Runtime patching is now resilient to upstream hash/symbol drift for the Linux WebHID path, old-driver modal suppression, EWEADNV mapping, and footer-link hiding.
- Crawl and unresolved-ref checks now guard against recursive path poisoning (`js/js`, repeated `assets/ico`) and avoid false positives from non-reachable files.
- Latest clean rebuild validation reports `Unresolved local refs: 0` and `Failed URLs: 0` while preserving offline enforcement and UI behavior.
- Public-facing branding now uses `OpenKeeb`, with compatibility names retained for existing scripts/modules.

## Important files

- `build_offline_mirror.py`
- `src/offline_mirror/`
- `scripts/run_offline.sh`
- `src/offline_mirror/server.py`
- `serve_offline.py` (compatibility entrypoint)
- `docs/history.md`
- `offline-site/README.md`
- `archive/README.md`

## Rebuild + run quick reference

```bash
python build_offline_mirror.py
./run_offline.sh
```

Open in browser:

```text
http://127.0.0.1:4173/
```

If behavior seems stale, clear site data for `127.0.0.1:<port>` or retest in Incognito.

## Known caveats

- Core device flow works offline; cloud/community/download features are effectively blocked by offline CSP/network policy.
- Browser must support WebHID (Chromium-based browsers recommended).
- Use `http://127.0.0.1:<port>/` (not `file://`).

## Maintenance policy

- Keep appending new changes to `docs/history.md` as work continues, in chronological order.
