#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import io
from functools import lru_cache, partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import brotli  # type: ignore
except ImportError:
    brotli = None


COMPRESSIBLE_EXTENSIONS = {
    ".html",
    ".css",
    ".js",
    ".mjs",
    ".json",
    ".map",
    ".svg",
    ".xml",
    ".txt",
}

MIN_COMPRESS_SIZE_BYTES = 1024


@lru_cache(maxsize=512)
def _get_compressed_payload(path_str: str, encoding: str, mtime_ns: int, file_size: int) -> bytes:
    _ = mtime_ns, file_size
    payload = Path(path_str).read_bytes()
    if encoding == "br":
        if brotli is None:
            raise RuntimeError("brotli module not available")
        return brotli.compress(payload, quality=5)
    return gzip.compress(payload, compresslevel=6, mtime=0)


class OfflineRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _can_compress(self, path: Path) -> bool:
        return path.suffix.lower() in COMPRESSIBLE_EXTENSIONS and path.stat().st_size >= MIN_COMPRESS_SIZE_BYTES

    def _preferred_encoding(self) -> str | None:
        accepted = (self.headers.get("Accept-Encoding") or "").lower()
        if brotli is not None and "br" in accepted:
            return "br"
        if "gzip" in accepted:
            return "gzip"
        return None

    def send_head(self):
        path_str = self.translate_path(self.path)
        path = Path(path_str)

        if path.is_dir():
            for index in ("index.html", "index.htm"):
                candidate = path / index
                if candidate.exists():
                    path = candidate
                    break
            else:
                return self.list_directory(str(path))

        if not path.exists() or not path.is_file():
            self.send_error(404, "File not found")
            return None

        stat_result = path.stat()
        content_type = self.guess_type(str(path))
        encoding = self._preferred_encoding()

        if encoding is not None and self._can_compress(path):
            compressed = _get_compressed_payload(
                str(path),
                encoding,
                stat_result.st_mtime_ns,
                stat_result.st_size,
            )
            if len(compressed) < stat_result.st_size:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Encoding", encoding)
                self.send_header("Vary", "Accept-Encoding")
                self.send_header("Content-Length", str(len(compressed)))
                self.send_header("Last-Modified", self.date_time_string(stat_result.st_mtime))
                self.end_headers()
                return io.BytesIO(compressed)

        file_handle = path.open("rb")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(stat_result.st_size))
        self.send_header("Last-Modified", self.date_time_string(stat_result.st_mtime))
        self.end_headers()
        return file_handle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve offline-site with local-only compression-aware HTTP")
    parser.add_argument("port", nargs="?", type=int, default=4173, help="Port to bind (default: 4173)")
    parser.add_argument(
        "--directory",
        default="offline-site",
        help="Directory to serve (default: offline-site)",
    )
    parser.add_argument(
        "--bind",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    directory = Path(args.directory).resolve()

    handler = partial(OfflineRequestHandler, directory=str(directory))

    with ThreadingHTTPServer((args.bind, args.port), handler) as server:
        server.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
