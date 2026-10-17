from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.constants import REQUEST_ID_HEADER, REQUEST_ID_PATTERN
from app.core.context import request_id_var


class RequestIdMiddleware:
    """Assigns every request an id, exposes it to logs/error bodies via a context variable
    and returns it in the ``X-Request-ID`` response header.

    An incoming id is reused (so ids can be traced across services) only if it matches
    ``REQUEST_ID_PATTERN``; otherwise a new one is generated.

    Written as pure ASGI rather than ``BaseHTTPMiddleware``, which adds overhead and has
    known issues with context variables and streaming responses.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        valid = incoming is not None and REQUEST_ID_PATTERN.fullmatch(incoming)
        request_id = incoming if valid and incoming else uuid4().hex

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        token = request_id_var.set(request_id)
        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_var.reset(token)
