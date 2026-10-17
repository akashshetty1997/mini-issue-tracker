import logging

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.error_responses import error_response
from app.core.constants import ErrorCode

logger = logging.getLogger(__name__)


class UnhandledErrorsMiddleware:
    """Last line of defence: turns any unexpected exception into a generic 500 envelope.

    The traceback is logged (with the request id) but never sent to the client.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            logger.exception("Unhandled error", extra={"path": scope.get("path")})
            if response_started:
                # Headers are already on the wire; nothing sensible can be sent now.
                raise
            response = error_response(
                500, ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."
            )
            await response(scope, receive, send)
