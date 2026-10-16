"""
Mock attacker server for the build harness.

Listens on 127.0.0.1:<port> inside the container and logs every request
(method, path, and up to 2 KB of any request body) to a file. Operators point
"attacker" URLs at http://127.0.0.1:8000/... so the validator can prove a
mutant really reached out, without any real network access.

Usage: python3 mock_server.py <port> <log_file>
"""
import http.server
import sys

PORT = int(sys.argv[1])
LOG = sys.argv[2]
BODY = b"mock-attacker-payload\n"


class Handler(http.server.BaseHTTPRequestHandler):
    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(min(length, 2048)) if length else b""
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{self.command} {self.path} "
                    f"{data.decode('utf-8', 'replace')!r}\n")
        self.send_response(200)
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(BODY)

    do_GET = do_POST = do_PUT = do_HEAD = _handle

    def log_message(self, *args):  # keep stdout quiet
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
