"""The core middleware."""

import re
import time
from collections.abc import Iterable
from uuid import uuid4

import structlog
from fastapi import status
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.constants import REQUEST_ID_HEADER, REQUEST_ID_PATTERN

logger = structlog.get_logger(__name__)


def get_request_id_from_scope(scope: Scope) -> str:
    """Return the request id sent by the client when valid, otherwise a new one."""
    request_id = Headers(scope=scope).get(REQUEST_ID_HEADER)
    if request_id is not None and re.fullmatch(REQUEST_ID_PATTERN, request_id):
        return request_id
    return uuid4().hex


class RequestContextMiddleware:
    """
    Give every request an id, and log one line when it is over.

    The id comes from the ``X-Request-ID`` header when a proxy or another service
    already assigned one, so a request can be followed across services, and is
    generated otherwise. It is returned in the same header and added to every log
    line written while the request is handled.
    """

    def __init__(self, app: ASGIApp, quiet_paths: Iterable[str] = ()) -> None:
        """Initialize the instance: requests to ``quiet_paths`` log at debug level."""
        self.app = app
        self.quiet_paths = frozenset(quiet_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle a request within its own logging context."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = get_request_id_from_scope(scope)
        # Why: the context is not reset at the end, so the 500 handler and the
        # server's error log, which run after this middleware, still see it. The
        # server runs each request in its own task, so it never leaks to another.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        start = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            """Add the request id to the response headers."""
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            log = logger.debug if scope["path"] in self.quiet_paths else logger.info
            log(
                "http_request",
                method=scope["method"],
                path=scope["path"],
                status_code=status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )
