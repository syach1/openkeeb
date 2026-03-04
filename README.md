# OpenKeeb

OpenKeeb is an offline Linux-friendly mirror and patch tool for the `https://www.qmk.top/` web driver.

This project was previously named `reverse-zap68`. For compatibility, some internal module and command names still use legacy `offline_mirror` naming.

## Quick start for new users

Follow these steps in order.

### 1) Install requirements

- `git`
- Python `3.10+`
- A Chromium-based browser with WebHID support (Chrome, Chromium, or Edge)

### 2) Clone this repository

```bash
git clone <YOUR_REPO_URL> OpenKeeb
cd OpenKeeb
```

Example URL format:

```text
https://github.com/<your-username>/OpenKeeb.git
```

### 3) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4) Install project dependencies

```bash
pip install --upgrade pip
pip install -e .
```

### 5) Build the local offline site

```bash
python build_offline_mirror.py
```

### 6) Run the local server

```bash
./run_offline.sh
```

Open this URL in your browser:

```text
http://127.0.0.1:4173/
```

### 7) Connect your keyboard

- Click `Add Device` in the web UI.
- Select your keyboard in the browser dialog.
- Grant permission when prompted.

## Daily commands

- Rebuild mirror output: `python build_offline_mirror.py`
- Serve default port: `./run_offline.sh`
- Serve custom port: `./run_offline.sh 8080`
- Keep orphaned files for diagnostics: `python build_offline_mirror.py --no-prune-orphans`
- Disable crawl progress output: `python build_offline_mirror.py --no-progress`

## CLI command aliases

After `pip install -e .`, both new and legacy command names are available:

- New OpenKeeb aliases: `openkeeb-build`, `openkeeb-serve`
- Legacy aliases (kept for compatibility): `offline-mirror-build`, `offline-mirror-serve`

Direct Python entrypoints also work:

```bash
python build_offline_mirror.py
python -m offline_mirror
python serve_offline.py
```

## Linux WebHID permissions (udev)

If your keyboard appears in `lsusb` but not in `Add Device`, add a udev rule.

1. Check USB IDs:

```bash
lsusb
```

2. Create a rule file:

```bash
sudo nano /etc/udev/rules.d/50-openkeeb.rules
```

3. Add this line and save:

```text
KERNEL=="hidraw*", ATTRS{idVendor}=="3151", ATTRS{idProduct}=="502f", MODE="0666", TAG+="uaccess"
```

If your board uses different IDs, replace `3151` and `502f` with your values from `lsusb`.

4. Reload rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

5. Replug the keyboard and fully restart the browser.

## Troubleshooting

- `offline-site` missing: run `python build_offline_mirror.py` first.
- WebHID still unavailable: verify udev rules and replug the device.
- Ubuntu Snap Chromium may still block `hidraw`: use non-Snap Chrome/Chromium.
- Always use `http://127.0.0.1:<port>/`, not `file://`.
- If behavior looks stale, clear site data for `127.0.0.1:<port>` or use Incognito.

## Project layout

- Source code: `src/offline_mirror/`, `build_offline_mirror.py`, `serve_offline.py`, `scripts/run_offline.sh`
- Generated output: `offline-site/` (recreated by build)
- Optional local diagnostics storage: `archive/raw/`

## License and non-affiliation

- MIT applies to original tooling code and docs in this repository.
- This project is independent and not affiliated with EPOMAKER, Rongyuan, GearHub, or qmk.top.
- `offline-site/` is generated locally; upstream third-party assets remain under their original licenses/terms.
- You are responsible for complying with upstream terms and local laws.

## Additional docs

- Project history and chronology: `docs/history.md`
- Generated-output note for mirror root: `offline-site/README.md`
- Legal/compliance details: `LEGAL.md`
