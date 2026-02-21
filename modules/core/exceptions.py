"""全局异常处理模块"""

from typing import Any, Sequence

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from pydantic import ValidationError

from .logging import get_logger
from .response import OrjsonResponse, error_response

logger = get_logger(__name__)


class BusinessException(Exception):
    """业务异常基类"""
    
    def __init__(self, message: str = "业务错误", code: int = 400, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(self.message)


class NotFoundException(BusinessException):
    """资源未找到异常"""
    def __init__(self, message: str = "资源未找到", data: Any = None):
        super().__init__(message, 404, data)


class BadRequestException(BusinessException):
    """请求参数错误异常"""
    def __init__(self, message: str = "请求参数错误", data: Any = None):
        super().__init__(message, 400, data)


class UnauthorizedException(BusinessException):
    """未授权异常"""
    def __init__(self, message: str = "未授权访问", data: Any = None):
        super().__init__(message, 401, data)


class ForbiddenException(BusinessException):
    """禁止访问异常"""
    def __init__(self, message: str = "禁止访问", data: Any = None):
        super().__init__(message, 403, data)


class InternalServerException(BusinessException):
    """服务器内部错误异常"""
    def __init__(self, message: str = "服务器内部错误", data: Any = None):
        super().__init__(message, 500, data)


def _format_errors(errors: Sequence[Any]) -> list[dict]:
    """格式化验证错误列表"""
    return [
        {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"], "type": e["type"]}
        for e in errors
    ]


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""
    
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        logger.warning(f"Business exception: {exc.message}", extra={
            "code": exc.code, "path": request.url.path, "method": request.method,
        })
        return OrjsonResponse(
            status_code=status.HTTP_200_OK,
            content=error_response(exc.message, exc.code, exc.data),
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP exception: {exc.detail}", extra={
            "status_code": exc.status_code, "path": request.url.path, "method": request.method,
        })
        return OrjsonResponse(
            status_code=status.HTTP_200_OK,
            content=error_response(str(exc.detail), exc.status_code),
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = _format_errors(exc.errors())
        logger.warning(f"Validation error: {errors}", extra={
            "path": request.url.path, "method": request.method,
        })
        return OrjsonResponse(
            status_code=status.HTTP_200_OK,
            content=error_response("请求参数验证失败", status.HTTP_422_UNPROCESSABLE_CONTENT, {"errors": errors}),
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        errors = _format_errors(exc.errors())
        logger.warning(f"Pydantic validation error: {errors}", extra={
            "path": request.url.path, "method": request.method,
        })
        return OrjsonResponse(
            status_code=status.HTTP_200_OK,
            content=error_response("数据验证失败", status.HTTP_422_UNPROCESSABLE_CONTENT, {"errors": errors}),
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", extra={
            "path": request.url.path, "method": request.method, "exc_type": type(exc).__name__,
        })
        return OrjsonResponse(
            status_code=status.HTTP_200_OK,
            content=error_response("服务器内部错误", status.HTTP_500_INTERNAL_SERVER_ERROR),
        )
