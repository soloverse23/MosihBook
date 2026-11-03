"""Accounts: sign-up with an invite code, sign-in, and each account's own settings, keys and books."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from bookforge import author, settings
from bookforge.web import app as webapp, auth

INVITE = "family-2026"


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PATH", tmp_path / "home" / "settings.json")
    monkeypatch.setenv("MOSIBOOKS_INVITE_CODE", INVITE)
    monkeypatch.setattr(auth, "_secret_cache", None)
    for k in ("KV_REST_API_URL", "UPSTASH_REDIS_REST_URL", "MOSIBOOKS_PASSWORD", "MOSIBOOKS_SECRET"):
        monkeypatch.delenv(k, raising=False)
    return lambda: TestClient(webapp.app)


def signup(c, email, password="a-good-password", invite=INVITE):
    return c.post("/api/signup", json={"email": email, "password": password, "invite": invite})


def test_signup_needs_the_invite_code_and_a_real_password(server):
    c = server()
    st = c.get("/api/auth/status").json()
    assert (st["mode"], st["signup_open"], st["signed_in"]) == ("accounts", True, False)
    assert signup(c, "a@b.co", invite="wrong").status_code == 403
    assert signup(c, "not-an-email").status_code == 422
    assert signup(c, "a@b.co", password="short").status_code == 422
    assert signup(c, "A@B.co").status_code == 200
    assert signup(server(), "a@b.co").status_code == 409  # same email, any case


def test_pages_and_api_need_a_session(server):
    c = server()
    assert c.get("/api/books").status_code == 401
    assert c.get("/", follow_redirects=False).headers["location"] == "/login"
    signup(c, "me@x.io")
    assert c.get("/api/books").status_code == 200
    c.post("/api/logout")
    c.cookies.clear()
    assert c.get("/api/books").status_code == 401


def test_login(server):
    signup(server(), "me@x.io")
    c = server()
    assert c.post("/api/login", json={"username": "me@x.io", "password": "nope-nope"}).status_code == 401
    r = c.post("/api/login", json={"username": "ME@x.io", "password": "a-good-password"})
    assert r.status_code == 200 and c.get("/api/auth/status").json()["user"] == "me@x.io"


def test_forged_or_other_users_cookie_is_rejected(server):
    c = server()
    signup(c, "me@x.io")
    tok = c.cookies.get(auth.COOKIE)
    name, exp, sig = tok.split(".")
    forged = server()
    forged.cookies.set(auth.COOKIE, f"{auth.make_token('me@x.io').split('.')[0]}.{int(exp) + 99}.{sig}")
    assert forged.get("/api/books").status_code == 401
    ghost = server()
    ghost.cookies.set(auth.COOKIE, auth.make_token("nobody@x.io"))  # signed, but no such account
    assert ghost.get("/api/books").status_code == 401


def test_each_account_has_its_own_keys_books_and_templates(server):
    a, b = server(), server()
    signup(a, "a@x.io")
    signup(b, "b@x.io")
    a.put("/api/settings", json={"openai_api_key": "sk-aaaaaaaaaaaaaaaaaaaa", "books_dir": "/etc"})
    assert b.get("/api/settings").json()["settings"]["openai_api_key"] == ""
    sa = a.get("/api/settings").json()
    assert sa["settings"]["openai_api_key"].startswith("sk-") and sa["server"] and sa["path"] == ""
    slug = a.post("/api/books", json={"idea": "a fox"}).json()["slug"]
    assert [x["slug"] for x in a.get("/api/books").json()] == [slug]
    assert b.get("/api/books").json() == []
    assert b.get(f"/api/books/{slug}").status_code == 404
    a.post("/api/templates", json={"name": "Mine", "sections": [{"kind": "story", "pages": 4}]})
    assert "mine" in {t["id"] for t in a.get("/api/templates").json()["templates"]}
    assert "mine" not in {t["id"] for t in b.get("/api/templates").json()["templates"]}
    st = a.get("/api/setup").json()
    assert st["server"] and st["user"] == "a@x.io" and not st["claude"]["logged_in"]


def test_claude_uses_the_accounts_own_api_key(server, monkeypatch):
    seen = {}

    async def fake_api(key, model, prompt, system, schema, images):
        seen["key"] = key
        return '```json\n{"questions": [{"id": "hero", "question": "Who?"}]}\n```'
    monkeypatch.setattr(author, "_ask_api", fake_api)
    c = server()
    signup(c, "a@x.io")
    slug = c.post("/api/books", json={"idea": "a fox"}).json()["slug"]
    r = c.post(f"/api/books/{slug}/claude/questions")
    assert r.status_code == 502 and "Anthropic API key" in r.json()["detail"]  # not connected yet
    assert c.post("/api/setup/claude-login").status_code == 400  # the server's own login is never offered
    c.put("/api/settings", json={"anthropic_api_key": "sk-ant-account-a-key"})
    assert c.post(f"/api/books/{slug}/claude/questions").status_code == 200
    assert seen["key"] == "sk-ant-account-a-key"


def test_jobs_belong_to_their_account(server):
    a, b = server(), server()
    signup(a, "a@x.io")
    signup(b, "b@x.io")
    from bookforge.web import jobs
    job = jobs.Job("j1", "x", "mock", user="a@x.io")
    jobs.JOBS["j1"] = job
    assert a.get("/api/jobs/j1").status_code == 200
    assert b.get("/api/jobs/j1").status_code == 404


def test_no_invite_code_on_vercel_means_signup_closed(server, monkeypatch):
    monkeypatch.delenv("MOSIBOOKS_INVITE_CODE")
    monkeypatch.setattr(settings, "ON_VERCEL", True)
    c = server()
    s = c.get("/api/auth/status").json()
    assert s["mode"] == "accounts" and not s["signup_open"] and not s["persistent"]
    assert signup(c, "a@x.io").status_code == 403


def _serve(handler_cls):
    import http.server
    import threading
    srv = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_upstash_store(tmp_path, monkeypatch):
    """The Upstash REST protocol: POST ["CMD", ...args] with a bearer token, answer {"result": ...}."""
    import http.server
    import json as _json
    from bookforge import kv
    data, seen = {}, []

    class Fake(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(self.headers["Authorization"])
            cmd, *args = _json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if cmd == "GET":
                res = data.get(args[0])
            elif cmd == "SET":
                res = None if "NX" in args and args[0] in data else data.__setitem__(args[0], args[1]) or "OK"
            else:
                res = int(data.pop(args[0], None) is not None)
            body = _json.dumps({"result": res}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    srv = _serve(Fake)
    monkeypatch.setenv("KV_REST_API_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setenv("KV_REST_API_TOKEN", "tok")
    assert kv.persistent()
    assert kv.set("user:a", {"x": 1}) and kv.get("user:a") == {"x": 1}
    assert not kv.set("user:a", {"x": 2}, only_if_new=True) and kv.get("user:a") == {"x": 1}
    kv.delete("user:a")
    assert kv.get("user:a") is None and set(seen) == {"Bearer tok"}
    srv.shutdown()


def test_claude_api_request(monkeypatch):
    """The direct Claude API call: streamed, the account's key, Opus with images and a JSON answer."""
    import asyncio
    import http.server
    import json as _json
    got = {}

    class Fake(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            got["path"] = self.path
            got["key"] = self.headers.get("x-api-key") or (self.headers.get("Authorization") or "").removeprefix("Bearer ")
            got["beta"] = self.headers.get("anthropic-beta")
            got["body"] = _json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "content": [],
                   "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 5, "output_tokens": 0}}
            events = [("message_start", {"type": "message_start", "message": msg}),
                      ("content_block_start", {"type": "content_block_start", "index": 0,
                                               "content_block": {"type": "text", "text": ""}}),
                      ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                               "delta": {"type": "text_delta", "text": '```json\n{"ok": true}\n```'}}),
                      ("content_block_stop", {"type": "content_block_stop", "index": 0}),
                      ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                                         "usage": {"output_tokens": 7}}),
                      ("message_stop", {"type": "message_stop"})]
            body = "".join(f"event: {e}\ndata: {_json.dumps(d)}\n\n" for e, d in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    srv = _serve(Fake)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", f"http://127.0.0.1:{srv.server_port}")
    from pathlib import Path
    from PIL import Image
    img = Path(__file__).parent / "_tmp_ref.png"
    Image.new("RGB", (20, 20), "red").save(img)
    try:
        text = asyncio.run(author._ask_api("sk-ant-test", "claude-opus-5-5", "Hi", "SYS", {"type": "object"}, [img]))
    finally:
        img.unlink()
    srv.shutdown()
    assert author._fenced(text, "json") == '{"ok": true}'
    b = got["body"]
    assert got["key"] == "sk-ant-test" and "server-side-fallback-2026-07-01" in got["beta"]
    assert b["model"] == "claude-opus-5-5" and b["stream"] is True and b["system"] == "SYS"
    assert b["fallbacks"] == "default" and b["output_config"] == {"effort": "high"}
    kinds = [c["type"] for c in b["messages"][0]["content"]]
    assert kinds == ["text", "image", "text"] and "JSON schema" in b["messages"][0]["content"][-1]["text"]


def test_database_env_variants(tmp_path, monkeypatch):
    from bookforge import kv
    for k in list(__import__("os").environ):
        if any(w in k for w in ("KV_", "REDIS", "UPSTASH")):
            monkeypatch.delenv(k)
    assert kv.backend() == "file"
    # Vercel's Upstash integration with a custom prefix; the read-only token is never used for writes
    monkeypatch.setenv("STORAGE_KV_REST_API_URL", "https://x.upstash.io/")
    monkeypatch.setenv("STORAGE_KV_REST_API_READ_ONLY_TOKEN", "ro")
    assert kv.backend() == "file"
    monkeypatch.setenv("STORAGE_KV_REST_API_TOKEN", "rw")
    assert kv._upstash() == ("https://x.upstash.io", "rw") and kv.backend() == "upstash"
    assert kv.seen_env() == ["STORAGE_KV_REST_API_READ_ONLY_TOKEN", "STORAGE_KV_REST_API_TOKEN", "STORAGE_KV_REST_API_URL"]


def test_redis_url_store(monkeypatch):
    """Vercel's Redis Cloud integration gives only REDIS_URL."""
    from bookforge import kv
    for k in list(__import__("os").environ):
        if any(w in k for w in ("KV_", "REDIS", "UPSTASH")):
            monkeypatch.delenv(k)
    monkeypatch.setenv("REDIS_URL", "rediss://default:pw@example.redis.cloud:6379")

    class FakeRedis(dict):
        def get(self, k):
            return dict.get(self, k)

        def set(self, k, v, nx=False):
            if nx and k in self:
                return None
            self[k] = v
            return True

        def delete(self, k):
            self.pop(k, None)
    monkeypatch.setattr(kv, "_client", FakeRedis())
    assert kv.backend() == "redis" and kv.persistent()
    assert kv.set("user:a", {"x": 1}) and not kv.set("user:a", {"x": 2}, only_if_new=True)
    assert kv.get("user:a") == {"x": 1}
    kv.delete("user:a")
    assert kv.get("user:a") is None
