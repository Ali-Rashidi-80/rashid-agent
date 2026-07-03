import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Response-Time-Ms"] = str(int((time.perf_counter() - start) * 1000))
        return response
