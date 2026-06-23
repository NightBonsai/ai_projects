from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import logging


logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that adds a unique request ID to each request."""

    async def dispatch(self, request: Request, call_next):
        
        request_id = str(uuid.uuid4())          # 生成 request_id

        request.state.request_id = request_id   # 保存 request_id
        logger.info(f"Request started: {request.method} {request.url.path} (request_id: {request_id})")

        response = await call_next(request)     # 运行接口: 调用真正业务

        response.headers["X-Request-ID"] = request_id
        logger.info(f"Request completed: {request.method} {request.url.path} (request_id:{request_id})")
        
        return response

