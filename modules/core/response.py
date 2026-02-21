"""统一响应模块 - 响应拦截和统一格式"""

from typing import Any, Generic, TypeVar

import orjson
from fastapi import Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应模型"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "code": 200,
                "message": "success",
                "data": {"key": "value"}
            }
        }
    )
    
    success: bool = Field(description="请求是否成功")
    code: int = Field(description="业务状态码")
    message: str = Field(description="响应消息")
    data: T | None = Field(default=None, description="响应数据")


def success_response(
    data: Any = None,
    message: str = "success",
    code: int = 200,
) -> dict[str, Any]:
    """构建成功响应"""
    return {
        "success": True,
        "code": code,
        "message": message,
        "data": data,
    }


def error_response(
    message: str = "error",
    code: int = 400,
    data: Any = None,
) -> dict[str, Any]:
    """构建错误响应"""
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": data,
    }


class OrjsonResponse(JSONResponse):
    """使用 orjson 的高性能 JSON 响应"""
    
    def render(self, content: Any) -> bytes:
        return orjson.dumps(
            content,
            option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z,
        )


class ResponseMiddleware(BaseHTTPMiddleware):
    """响应拦截中间件 - 统一包装响应格式"""
    
    EXCLUDED_HEADERS = frozenset({
        "content-length",
        "content-encoding",
        "transfer-encoding",
    })
    
    async def dispatch(self, request: Request, call_next):
        # 排除不需要包装的路径
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        response = await call_next(request)
        
        if not self._should_wrap(response):
            return response
        
        # 读取响应体 (StreamingResponse 使用 body_iterator)
        response_body = b""
        body_iterator = getattr(response, "body_iterator", None)
        if body_iterator is not None:
            async for chunk in body_iterator:
                response_body += chunk
        elif hasattr(response, "body"):
            body = response.body
            if isinstance(body, bytes):
                response_body = body
            elif isinstance(body, str):
                response_body = body.encode()
            else:
                response_body = bytes(body)
        
        try:
            original_data = orjson.loads(response_body)
            
            if self._is_wrapped(original_data):
                return OrjsonResponse(
                    content=original_data,
                    status_code=response.status_code,
                    headers=self._filter_headers(response.headers),
                )
            
            return OrjsonResponse(
                content=success_response(data=original_data, code=response.status_code),
                status_code=response.status_code,
                headers=self._filter_headers(response.headers),
            )
            
        except (orjson.JSONDecodeError, UnicodeDecodeError):
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=self._filter_headers(response.headers),
                media_type=response.media_type,
            )
    
    @staticmethod
    def _should_exclude(path: str) -> bool:
        """检查路径是否需要排除包装"""
        exclude_paths = ("/docs", "/redoc", "/openapi.json", "/favicon.ico")
        return path.startswith(exclude_paths)
    
    def _filter_headers(self, headers) -> dict[str, str]:
        """过滤响应头"""
        return {
            k: v for k, v in headers.items()
            if k.lower() not in self.EXCLUDED_HEADERS
        }
    
    @staticmethod
    def _should_wrap(response) -> bool:
        """判断是否需要包装响应"""
        return (
            "application/json" in response.headers.get("content-type", "")
            and response.status_code < 400
        )
    
    @staticmethod
    def _is_wrapped(data: dict) -> bool:
        """检查响应是否已经是统一格式"""
        return {"success", "code", "message", "data"}.issubset(data.keys())
