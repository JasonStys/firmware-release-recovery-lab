"""File: Serves the actual rehearsal editor and fixed engine API on one owned loopback listener.

Host owns the server thread and its finite worker slots. Handler validates exact authority,
capability, Origin and input bounds. No filesystem URL, remote URL, shell or plugin is accepted.
State and exact symbol locations are indexed in docs/code-index.md.
"""

import hmac
import json
import secrets
import sqlite3
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from firmware_studio import __version__
from firmware_studio.engine import Engine
from firmware_studio.store import Profile

MAX_BODY = 256 * 1024
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "connect-src 'self'; font-src 'none'; object-src 'none'; frame-src 'none'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


class BoundedServer(ThreadingHTTPServer):
    """Bound slow connection threads as well as expensive engine operations."""

    def __init__(self, address, handler):
        self.connections = threading.BoundedSemaphore(8)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self.connections.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.connections.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.connections.release()

    def handle_error(self, request, client_address):
        "A disconnected/invalid client never causes a source/path-bearing traceback in native logs."


class Host:
    "Own an ephemeral socket and all handlers until normal drain completes; never adopt a service."

    def __init__(self, profile: Profile, engine: Engine, assets: dict[str, tuple[str, bytes]]):
        "Prebind loopback port zero; all static bytes were verified before profile initialization."
        self.profile, self.engine, self.assets = profile, engine, assets
        self.capability = secrets.token_urlsafe(32)
        self.nonce = secrets.token_hex(16)
        self.stop_requested = threading.Event()
        self.slots = threading.BoundedSemaphore(4)
        self.server = BoundedServer(("127.0.0.1", 0), Handler)
        self.server.host = self
        self.server.daemon_threads = False
        self.authority = f"127.0.0.1:{self.server.server_port}"
        self.origin = f"http://{self.authority}"
        self.url = f"{self.origin}/#native={self.capability}"
        self.thread = threading.Thread(target=self.server.serve_forever, name="firmware-loopback")
        self.closed = False

    def start(self):
        "Start only this bound socket; readiness never comes from probing/reusing another server."
        try:
            self.thread.start()
        except BaseException:
            self.server.server_close()
            raise

    def close(self):
        """Retain profile ownership until every fixed engine/HTTP operation has really finished."""
        if not self.closed:
            self.server.shutdown()
            self.thread.join()
            self.server.server_close()
            self.profile.close()
            self.closed = True


class Handler(BaseHTTPRequestHandler):
    "No external origins, cookies, proxy headers or arbitrary paths grant private workspace access."

    server_version = "FirmwareStudio"
    sys_version = ""

    def setup(self):
        """Slow/unfinished client uploads cannot retain a handler indefinitely."""
        super().setup()
        self.connection.settimeout(5)

    @property
    def host(self) -> Host:
        return self.server.host

    def log_message(self, *_args):
        """Never print submitted source, titles, bearer capabilities or workspace paths."""

    def send_error(self, code, message=None, explain=None):
        """Policy-bound unsupported methods/errors never echo supplied request bytes."""
        self.reply(code, {"error": "Unsupported or malformed HTTP request"})

    def reply(self, status: int, value: object):
        """Encode JSON with safe content type; never interpolate user data into executable HTML."""
        self.bytes(status, "application/json; charset=utf-8", json.dumps(value).encode())

    def bytes(self, status: int, content_type: str, raw: bytes):
        "Apply the same restrictive browser policy to errors, exports and all fixed static assets."
        self.send_response(status)
        for key, value in {
            "Content-Type": content_type,
            "Content-Length": str(len(raw)),
            "Content-Security-Policy": CSP,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Cache-Control": "no-store",
            "Connection": "close",
        }.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)
        self.close_connection = True

    def allowed(self, private: bool = False, mutation: bool = False) -> bool:
        """Fail before body reads on wrong/multiple authority, capability or mutation Origin."""
        if self.headers.get_all("Host") != [self.host.authority]:
            self.reply(403, {"error": "Wrong listener authority"})
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.reply(403, {"error": "Cross-site access refused"})
            return False
        capabilities = self.headers.get_all("X-Firmware-Capability") or []
        if private and (
            len(capabilities) != 1
            or not capabilities[0].isascii()
            or not hmac.compare_digest(capabilities[0], self.host.capability)
        ):
            self.reply(403, {"error": "Open this app from its native owner window"})
            return False
        if mutation and self.headers.get_all("Origin") != [self.host.origin]:
            self.reply(403, {"error": "Wrong Origin"})
            return False
        return True

    def do_GET(self):
        """Fixed preloaded assets and capability-bound history; no untrusted filename is opened."""
        try:
            parsed = urlsplit(self.path)
            path = parsed.path
            if not self.allowed(private=path.startswith("/api/")):
                return
            if path == "/health" and not parsed.query:
                self.reply(
                    200,
                    {
                        "product": "firmware-release-recovery-lab",
                        "version": __version__,
                        "nonce": self.host.nonce,
                        "engine": self.host.engine.identity,
                    },
                )
            elif path == "/api/history":
                fields = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=3)
                if set(fields) - {"q", "kind", "page"} or any(
                    len(value) != 1 for value in fields.values()
                ):
                    raise ValueError("Invalid search fields")
                page = int(fields.get("page", ["0"])[0])
                self.reply(
                    200,
                    self.host.profile.store.history(
                        fields.get("q", [""])[0], fields.get("kind", [""])[0], page
                    ),
                )
            elif path.startswith("/api/history/") and not parsed.query:
                self.reply(200, self.host.profile.store.get(path.removeprefix("/api/history/")))
            elif path in self.host.assets and not parsed.query:
                content_type, raw = self.host.assets[path]
                self.bytes(200, content_type, raw)
            else:
                self.reply(404, {"error": "Not found"})
        except KeyError:
            self.reply(404, {"error": "History record not found"})
        except ValueError, UnicodeError:
            self.reply(400, {"error": "Invalid search or identifier"})
        except TimeoutError, BrokenPipeError, ConnectionResetError:
            self.close_connection = True

    def body(self) -> dict:
        "One exact bounded UTF-8 JSON object; no compression, chunking, ambiguous length or NaN."
        lengths = self.headers.get_all("Content-Length") or []
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal():
            raise ValueError("Provide one decimal Content-Length")
        length = int(lengths[0])
        if (
            not 1 <= length <= MAX_BODY
            or self.headers.get("Transfer-Encoding")
            or self.headers.get("Content-Encoding")
        ):
            raise ValueError("JSON body exceeds 256 KiB or uses unsupported framing")
        if self.headers.get_all("Content-Type") != ["application/json"]:
            raise ValueError("Use application/json")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValueError("Incomplete input")

        def pairs(items):
            value = {}
            for key, entry in items:
                if key in value:
                    raise ValueError("Duplicate JSON field")
                value[key] = entry
            return value

        def invalid_constant(_value):
            raise ValueError("Non-finite JSON is unsupported")

        try:
            value = json.loads(
                raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant
            )
        except RecursionError as error:
            raise ValueError("JSON nesting exceeds the supported input depth") from error
        if not isinstance(value, dict):
            raise ValueError("Provide one JSON object")
        pending = [(value, 1)]
        while pending:
            node, depth = pending.pop()
            if depth > 64:
                raise ValueError("JSON nesting exceeds the supported input depth")
            if isinstance(node, dict):
                pending.extend((entry, depth + 1) for entry in node.values())
            elif isinstance(node, list):
                pending.extend((entry, depth + 1) for entry in node)
        return value

    def do_POST(self):
        "Execute the fixed kernel or delete/quit; bound concurrency without a growing queue."
        if not self.allowed(private=True, mutation=True):
            return
        acquired = False
        try:
            value = self.body()
            # Consume authorized bounded uploads before HTTP429 to avoid an unread-body reset.
            # Wrong capability/Origin still fails before any body is read.
            acquired = self.host.slots.acquire(blocking=False)
            if not acquired:
                self.reply(
                    429, {"error": "Four experiments are already active; wait for completion"}
                )
                return
            if self.path == "/api/run":
                if set(value) != {"title", "input"}:
                    raise ValueError("Provide title and input only")
                title = value["title"]
                if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
                    raise ValueError("Give this experiment a title of 1-100 characters")
                report = self.host.engine.run(value["input"])
                if report.get("status") == "error":
                    self.reply(422, {"diagnostic": report})
                else:
                    identity = {**self.host.engine.identity, "sha256": self.host.engine.sha256}
                    self.reply(
                        201, self.host.profile.store.save(title, value["input"], report, identity)
                    )
            elif self.path == "/api/delete" and set(value) == {"id"}:
                self.host.profile.store.delete(value["id"])
                self.reply(200, {"deleted": value["id"]})
            elif self.path == "/api/quit" and value == {"quit": True}:
                self.host.stop_requested.set()
                self.reply(200, {"closing": True})
            else:
                self.reply(404, {"error": "Unknown operation"})
        except KeyError:
            self.reply(404, {"error": "History record not found"})
        except (ValueError, UnicodeError, json.JSONDecodeError) as error:
            self.reply(400, {"error": str(error)})
        except TimeoutError:
            self.reply(408, {"error": "Incomplete request body"})
        except OSError, sqlite3.Error, subprocess.SubprocessError:
            # Never expose source/secrets in logs. A failure is never a saved success.
            self.reply(
                500, {"error": "Experiment could not complete; prior saved evidence is unchanged"}
            )
        finally:
            if acquired:
                self.host.slots.release()
