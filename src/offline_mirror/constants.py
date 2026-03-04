from __future__ import annotations

import re


ALLOWED_EXTENSIONS = {
    ".js",
    ".mjs",
    ".css",
    ".html",
    ".ico",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".avif",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".json",
    ".wasm",
    ".map",
    ".mp3",
    ".wav",
    ".ogg",
    ".webm",
    ".mp4",
}

TEXT_MIME_HINTS = (
    "text/",
    "application/javascript",
    "application/x-javascript",
    "application/json",
)

HTML_ATTR_REF_RE = re.compile(r"(?:src|href)=[\"']([^\"']+)[\"']", re.IGNORECASE)
CSS_URL_RE = re.compile(r"url\(([^)]+)\)", re.IGNORECASE)

OFFLINE_CSP_CONTENT = (
    "default-src 'self' data: blob:; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "connect-src 'self' http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:*; "
    "img-src 'self' data: blob:; "
    "media-src 'self' data: blob:; "
    "font-src 'self' data: blob:; "
    "script-src 'self' 'unsafe-eval' blob:; "
    "style-src 'self' 'unsafe-inline'; "
    "worker-src 'self' blob:; "
    "form-action 'self';"
)

OFFLINE_CONNECT_SRC_ALLOWED_TOKENS = {
    "'self'",
    "http://127.0.0.1:*",
    "http://localhost:*",
    "ws://127.0.0.1:*",
    "ws://localhost:*",
}

EXTERNAL_URL_RE = re.compile(r"\b(?:https?|wss?)://[^\s\"'<>`\\]+", re.IGNORECASE)

BALANCED_ALLOWED_EXTERNAL_REFERENCE_HOSTS = {
    "www.w3.org",
    "reactjs.org",
    "fb.me",
    "github.com",
    "raw.github.com",
    "stuk.github.io",
    "stuartk.com",
    "feross.org",
}

BALANCED_BLOCKED_EXTERNAL_HOST_SUFFIXES = (
    "qmk.top",
    "rongyuan.tech",
    "gearhub.top",
    "aka.ms",
    "miit.gov.cn",
)

THEME_COLOR_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("#3E3E3E", "var(--color-key-background-default)"),
    ("#3e3e3e", "var(--color-key-background-default)"),
    ("#74EBD5", "var(--color-highlight-2)"),
    ("#74ebd5", "var(--color-highlight-2)"),
    ("#71A4F1", "var(--color-highlight-3)"),
    ("#58BAA8", "var(--color-key-background-changed)"),
    ("#989898", "var(--color-cell-border-default)"),
    ("#D5D5D5", "var(--color-text-disabled)"),
    ("#d5d5d5", "var(--color-text-disabled)"),
    ("#F9F9F9", "var(--color-background-white)"),
    ("#f9f9f9", "var(--color-background-white)"),
    ("#E5E5E5", "var(--border-color)"),
    ("#e5e5e5", "var(--border-color)"),
    ("#E0E0E0", "var(--border-color)"),
    ("#e0e0e0", "var(--border-color)"),
    ("#606060", "var(--color-background-dark)"),
    ("#d8d8d8", "var(--color-background-default)"),
    ("#FE4545", "var(--color-key-system)"),
    ("#FAFF00", "var(--color-key-background-forbidden)"),
)

PERMANENT_BLOCKED_MARKERS: tuple[str, ...] = (
    "AiFloat",
    "0afe9811.js",
    "AiFloat.db6806a6.css",
    "children:!vt&&(",
    "!v.isNoAIAssistant()&&d.jsx(y.Suspense",
    "beian.miit.gov.cn",
    "qmk.top/gear-lab",
    "api3.rongyuan.tech:3816",
    "api2.qmk.top:3816",
    "api2.rongyuan.tech:3816",
    "api.rongyuan.tech:3814",
    "iotdriver.qmk.top",
    "iotdriver.gearhub.top",
    "news.rongyuan.tech/iot_driver",
    "aka.ms/vs/17/release/vc_redist.x86.exe",
    "aka.ms/vs/17/release/vc_redist.x64.exe",
)

PERMANENT_BLOCKED_SCAN_SUFFIXES = {".html", ".js", ".mjs", ".css"}

# Quoted path references commonly seen in minified bundles.
QUOTED_PATH_RE = re.compile(
    r"[\"']((?:\.{1,2}[\\/]|/)[^\"'\s]+?"
    r"(?:\.js|\.mjs|\.css|\.html|\.ico|\.png|\.jpe?g|\.gif|\.svg|\.webp|\.avif|\.woff2?|\.ttf|\.otf|\.eot|\.json|\.wasm|\.map|\.mp3|\.wav|\.ogg|\.webm|\.mp4)"
    r"(?:\?[^\"']*)?)"
    r"[\"']",
    re.IGNORECASE,
)
