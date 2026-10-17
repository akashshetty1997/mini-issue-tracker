"""Reproduce: slowapi re-raises a storage error from header injection even after it
has switched to its in-memory fallback.

Evidence for ENGINEERING.md only: not part of the application, and CI doesn't run it.

Simulates Redis failing between the hit (succeeds) and get_window_stats (fails).
Tested with slowapi 0.1.10, limits 5.8.0, fastapi 0.143.3, starlette 1.8.0 (Python 3.12):

    python3 -m venv .venv
    .venv/bin/pip install slowapi==0.1.10 limits==5.8.0 fastapi==0.143.3 httpx
    .venv/bin/python slowapi_header_fallback.py

Expected: status 500, _storage_dead True. The fallback kicked in, yet the request
still failed, because _inject_headers re-raises unless swallow_errors=True
(slowapi/extension.py, the bare `except:` in _inject_headers).
"""

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    in_memory_fallback_enabled=True,
    # The header path only switches to memory when fallback limits are listed.
    in_memory_fallback=["5/minute"],
    headers_enabled=True,
)

app = FastAPI()
app.state.limiter = limiter


@app.get("/ping")
@limiter.limit("5/minute")
def ping(request: Request, response: Response) -> dict[str, str]:
    return {"ok": "yes"}


def storage_down(*_args, **_kwargs):
    raise ConnectionError("simulated Redis outage")


limiter._limiter.get_window_stats = storage_down  # hit() still works, stats fail

client = TestClient(app, raise_server_exceptions=False)
response = client.get("/ping")
print("status:", response.status_code)
print("fallback active (_storage_dead):", limiter._storage_dead)
print("rate-limit headers:", {k: v for k, v in response.headers.items() if "ratelimit" in k})
