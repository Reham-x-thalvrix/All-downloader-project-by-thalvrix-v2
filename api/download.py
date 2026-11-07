
import json
import socket
import ipaddress

from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

import yt_dlp


def validate_url(raw):
    if not raw or len(raw) > 4096:
        raise ValueError("Please provide a valid video URL.")

    parsed = urlparse(raw)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only HTTP and HTTPS URLs are accepted.")

    host = parsed.hostname.lower()

    if host == "localhost" or host.endswith(
        (".localhost", ".local", ".internal")
    ):
        raise ValueError("Local network URLs are not allowed.")

    try:
        addresses = socket.getaddrinfo(host, None)

        for item in addresses:
            ip = ipaddress.ip_address(item[4][0])

            if not ip.is_global:
                raise ValueError("Private network URLs are not allowed.")

    except socket.gaierror:
        raise ValueError("Unable to resolve video host.")

    return raw


def clean_format(f):
    return {
        "format_id": f.get("format_id"),
        "ext": f.get("ext"),
        "resolution": f.get("resolution") or f.get("format_note"),
        "format_note": f.get("format_note"),
        "filesize": f.get("filesize"),
        "filesize_approx": f.get("filesize_approx"),
        "vcodec": f.get("vcodec"),
        "acodec": f.get("acodec"),
        "url": f.get("url")
    }


class handler(BaseHTTPRequestHandler):

    def _send(self, status, payload):
        body = json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))

        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    def do_GET(self):
        try:
            query = parse_qs(urlparse(self.path).query)

            raw_url = query.get("url", [""])[0]

            target = validate_url(raw_url)

            options = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "socket_timeout": 15,
                "retries": 1,
                "format": "best"
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    target,
                    download=False
                )

            if not info:
                raise ValueError("No video information found.")

            if info.get("_type") in ("playlist", "multi_video"):
                raise ValueError("Playlist URLs are not supported.")

            formats = []

            for f in info.get("formats", []):
                direct = f.get("url")

                if direct and f.get("protocol") not in (
                    "m3u8",
                    "m3u8_native",
                    "http_dash_segments"
                ):
                    formats.append(clean_format(f))

            formats.sort(
                key=lambda f: (
                    0 if f.get("vcodec") not in (
                        None, "none"
                    ) and f.get("acodec") not in (
                        None, "none"
                    ) else 1
                )
            )

            formats = formats[:20]

            best = next(
                (
                    f for f in formats
                    if f.get("vcodec") not in (
                        None, "none"
                    ) and f.get("acodec") not in (
                        None, "none"
                    )
                ),
                None
            )

            if not best:
                best = formats[0] if formats else None

            if not best:
                raise ValueError(
                    "No direct downloadable format available."
                )

            payload = {
                "success": True,
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader") or info.get("channel"),
                "webpage_url": info.get("webpage_url"),
                "id": info.get("id"),
                "ext": best.get("ext"),
                "resolution": best.get("resolution"),
                "download_url": best.get("url"),
                "formats": formats
            }

            self._send(200, payload)

        except ValueError as exc:
            self._send(
                400,
                {
                    "success": False,
                    "error": str(exc)
                }
            )

        except Exception:
            self._send(
                502,
                {
                    "success": False,
                    "error": "Could not extract this video. It may be unsupported, private, restricted, or temporarily unavailable."
                }
            )
