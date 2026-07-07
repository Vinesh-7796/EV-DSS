"""Request logging middleware for the Application Layer."""

import sys
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        response = await call_next(request)

        duration = (time.time() - start) * 1000.0
        print(
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration:.1f}ms)",
            file=sys.stderr,
        )
        return response
