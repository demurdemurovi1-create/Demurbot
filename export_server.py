"""Tiny download server so -updatexport works without Dropbox.

Serves  /export/<guild_id>/<token>.json.gz  where token is an HMAC of the guild id
(keyed by the Discord token), so links can't be guessed.
"""
import gzip, hashlib, hmac, os, shutil, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from data_dir import data_path


def _secret():
    s = os.environ.get("DISCORD_TOKEN")
    if not s:
        try:
            s = open("token.txt").read().strip()
        except Exception:
            s = "dev"
    return s.encode()


def make_token(guild_id):
    return hmac.new(_secret(), str(guild_id).encode(), hashlib.sha256).hexdigest()[:24]


def public_url(guild_id):
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if not domain:
        return None
    return f"https://{domain}/export/{guild_id}/{make_token(guild_id)}.json.gz"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_text(self, code, text):
        body = text.encode()
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = self.path.split("?")[0].strip("/").split("/")
        if parts == [""] or parts == ["health"]:
            return self._send_text(200, "DemurBot")
        if len(parts) != 3 or parts[0] != "export" or not parts[2].endswith(".json.gz"):
            return self._send_text(404, "not found")
        gid, token = parts[1], parts[2][:-len(".json.gz")]
        if not gid.isdigit() or not hmac.compare_digest(token, make_token(gid)):
            return self._send_text(404, "not found")
        src = data_path(f"exports/{gid}-export.json")
        if not os.path.exists(src):
            return self._send_text(404, "no export for this server")
        with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with open(src, "rb") as f_in, gzip.open(tmp_path, "wb", compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
            size = os.path.getsize(tmp_path)
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", f'attachment; filename="{gid}-export.json.gz"')
            self.end_headers()
            with open(tmp_path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def start():
    port = int(os.environ.get("PORT", "8080"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Export download server on :{port}")
