"""配置管理路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from modules.core.config import config_manager
from modules.core.logging import get_logger, update_log_level

router = APIRouter(prefix="/config", tags=["config"])
logger = get_logger(__name__)


class LogConfigUpdate(BaseModel):
    """日志配置更新请求"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "level": "DEBUG",
                "max_bytes": 20971520,
                "backup_count": 20
            }
        }
    )
    
    level: str | None = Field(
        None, 
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="日志级别",
        examples=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )
    max_bytes: int | None = Field(
        None, 
        gt=0, 
        description="单个日志文件最大字节数，默认 10485760 (10MB)"
    )
    backup_count: int | None = Field(
        None, 
        ge=1, 
        le=100, 
        description="最多保留的日志文件数量，范围 1-100"
    )
    retention_days: int | None = Field(
        None, 
        ge=1, 
        le=365, 
        description="日志保留天数，范围 1-365"
    )
    log_dir: str | None = Field(
        None, 
        description="日志文件存储目录"
    )
    format: str | None = Field(
        None, 
        pattern="^(json|text)$",
        description="日志格式：json 或 text"
    )


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "log": {
                    "level": "DEBUG",
                    "max_bytes": 20971520,
                    "backup_count": 20
                }
            }
        }
    )
    
    log: LogConfigUpdate | None = Field(
        None, 
        description="日志配置更新项"
    )


class AppConfigResponse(BaseModel):
    """应用配置响应"""
    name: str = Field(description="应用名称")
    debug: bool = Field(description="调试模式")


class LogConfigResponse(BaseModel):
    """日志配置响应"""
    level: str = Field(description="日志级别")
    log_dir: str = Field(description="日志目录")
    max_bytes: int = Field(description="单文件最大字节数")
    backup_count: int = Field(description="备份文件数量")
    retention_days: int = Field(description="保留天数")
    format: str = Field(description="日志格式")


class ConfigResponse(BaseModel):
    """配置响应"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "app": {
                    "name": "mat-device-control",
                    "debug": False
                },
                "log": {
                    "level": "INFO",
                    "log_dir": "logs",
                    "max_bytes": 10485760,
                    "backup_count": 10,
                    "retention_days": 7,
                    "format": "json"
                }
            }
        }
    )
    
    app: AppConfigResponse = Field(description="应用配置")
    log: LogConfigResponse = Field(description="日志配置")


@router.get(
    "",
    response_model=ConfigResponse,
    summary="获取配置",
    description="""
获取当前应用的所有配置信息。

返回应用配置和日志配置的完整信息。
""",
    responses={
        200: {
            "description": "成功获取配置",
            "content": {
                "application/json": {
                    "example": {
                        "app": {
                            "name": "mat-device-control",
                            "debug": False
                        },
                        "log": {
                            "level": "INFO",
                            "log_dir": "logs",
                            "max_bytes": 10485760,
                            "backup_count": 10,
                            "retention_days": 7,
                            "format": "json"
                        }
                    }
                }
            }
        }
    }
)
async def get_config():
    """获取当前配置
    
    返回应用的完整配置信息，包括应用配置和日志配置。
    
    Returns:
        ConfigResponse: 包含应用和日志配置的响应
    """
    config = config_manager.config
    return ConfigResponse(
        app=AppConfigResponse(
            name=config.name,
            debug=config.debug,
        ),
        log=LogConfigResponse(
            level=config.log.level,
            log_dir=str(config.log.log_dir),
            max_bytes=config.log.max_bytes,
            backup_count=config.log.backup_count,
            retention_days=config.log.retention_days,
            format=config.log.format,
        ),
    )


@router.patch(
    "",
    response_model=ConfigResponse,
    summary="更新配置",
    description="""
动态更新应用配置。

目前支持更新日志相关配置，修改后会立即生效并持久化到配置文件。

**可更新的日志配置项：**
* `level` - 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
* `max_bytes` - 单个日志文件最大字节数
* `backup_count` - 最多保留的日志文件数量
* `retention_days` - 日志保留天数
* `log_dir` - 日志文件存储目录
* `format` - 日志格式：json 或 text
""",
    responses={
        200: {
            "description": "配置更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "app": {
                            "name": "mat-device-control",
                            "debug": False
                        },
                        "log": {
                            "level": "DEBUG",
                            "log_dir": "logs",
                            "max_bytes": 10485760,
                            "backup_count": 10,
                            "retention_days": 7,
                            "format": "json"
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求参数无效",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid log level: INVALID"
                    }
                }
            }
        },
        422: {
            "description": "参数验证失败",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "string_pattern_mismatch",
                                "loc": ["body", "log", "level"],
                                "msg": "String should match pattern '^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$'",
                                "input": "INVALID"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def update_config(request: ConfigUpdateRequest):
    """更新配置
    
    动态更新应用配置并持久化。
    
    Args:
        request: 配置更新请求，包含需要更新的配置项
        
    Returns:
        ConfigResponse: 更新后的完整配置
        
    Raises:
        HTTPException: 当参数无效时返回 400 错误
    """
    if request.log:
        log_updates = request.log.model_dump(exclude_unset=True)
        
        if "level" in log_updates:
            try:
                update_log_level(log_updates["level"])
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        config_manager.update_log_config(**log_updates)
        config_manager.save_config()
        
        logger.info(f"Config updated: {log_updates}")
    
    config = config_manager.config
    return ConfigResponse(
        app=AppConfigResponse(
            name=config.name,
            debug=config.debug,
        ),
        log=LogConfigResponse(
            level=config.log.level,
            log_dir=str(config.log.log_dir),
            max_bytes=config.log.max_bytes,
            backup_count=config.log.backup_count,
            retention_days=config.log.retention_days,
            format=config.log.format,
        ),
    )
