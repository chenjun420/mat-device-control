"""健康检查路由"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from modules.core.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "service": "mat-device-control"
            }
        }
    )
    
    status: str = "healthy"
    service: str = "mat-device-control"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="""
检查服务是否正常运行。

返回服务状态和服务名称。用于负载均衡器、监控系统或 Kubernetes 探针检测服务健康状态。
""",
    responses={
        200: {
            "description": "服务正常",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "mat-device-control"
                    }
                }
            }
        }
    }
)
async def health_check():
    """健康检查端点
    
    用于检测服务是否正常运行。
    
    Returns:
        HealthResponse: 包含状态和服务名称的响应
    """
    logger.info("Health check requested")
    return HealthResponse()
