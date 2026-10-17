import logging
import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.constants import PROCESS_TIME_HEADER

logger = logging.getLogger("app.access")


class AccessLogMiddleware:
    """One structured log line per request (method, path, status, duration). The request
    id is attached by the JSON formatter, so a client-reported id finds the line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status_code = 500  # if the app fails before responding, that's what the client sees

        async def send_with_timing(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                elapsed_ms = (time.perf_counter() - started) * 1000
                MutableHeaders(scope=message)[PROCESS_TIME_HEADER] = f"{elapsed_ms:.1f}ms"
            await send(message)

        try:
            await self.app(scope, receive, send_with_timing)
        finally:
            client = scope.get("client")
            logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "client_ip": client[0] if client else None,
                },
            )
