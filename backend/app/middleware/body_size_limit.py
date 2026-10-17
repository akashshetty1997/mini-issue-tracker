from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.error_responses import error_response
from app.core.constants import MAX_REQUEST_BODY_BYTES, ErrorCode

_TOO_LARGE_MESSAGE = "The request body is too large."


class _BodyTooLargeError(HTTPException):
    # An HTTPException so FastAPI re-raises it as-is while reading the body (any other
    # exception there is converted into a generic 400), and the normal HTTP error
    # handler renders the 413 envelope.
    def __init__(self) -> None:
        super().__init__(status_code=413, detail=_TOO_LARGE_MESSAGE)


class BodySizeLimitMiddleware:
    """Rejects bodies larger than ``max_bytes`` with 413.

    Checks Content-Length up front, and also counts bytes as they stream in, because a
    chunked request has no Content-Length and a client can lie about it.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        received = 0
        response_started = False

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyTooLargeError()
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _BodyTooLargeError:
            # Only reached if the body was read outside FastAPI's request handling.
            if response_started:
                raise
            await self._reject(scope, receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        response = error_response(413, ErrorCode.PAYLOAD_TOO_LARGE, _TOO_LARGE_MESSAGE)
        await response(scope, receive, send)
