"""MQTT路由器 - 提供MQTT相关的API端点"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from modules.core.logging import get_logger


router = APIRouter(prefix="/mqtt", tags=["mqtt"])
logger = get_logger(__name__)


class MQTTMessage(BaseModel):
    """MQTT消息模型"""
    topic: str = Field(..., description="MQTT主题")
    message: Dict[str, Any] = Field(..., description="消息内容")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "topic": "device/001/api/config",
                "message": {"log": {"level": "DEBUG"}}
            }
        }
    }


class MQTTStatus(BaseModel):
    """MQTT状态模型"""
    connected: bool = Field(..., description="MQTT连接状态")
    enabled: bool = Field(default=True, description="MQTT是否启用")
    client_id: Optional[str] = Field(None, description="客户端ID")
    broker: Optional[str] = Field(None, description="Broker地址")
    port: Optional[int] = Field(None, description="Broker端口")
    subscribed_topics: list[str] = Field(default_factory=list, description="已订阅的主题")


class MQTTConnectionResult(BaseModel):
    """MQTT连接操作结果模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    connected: bool = Field(..., description="当前连接状态")


# 全局MQTT桥接器引用（由main.py设置）
_mqtt_bridge = None


def set_mqtt_bridge(bridge):
    """设置MQTT桥接器引用"""
    global _mqtt_bridge
    _mqtt_bridge = bridge


@router.get(
    "/status",
    response_model=MQTTStatus,
    summary="获取MQTT状态",
    description="获取当前MQTT连接状态和订阅信息"
)
async def get_mqtt_status():
    """获取MQTT状态"""
    from modules.core.config import config_manager
    mqtt_config = config_manager.config.mqtt
    
    if not _mqtt_bridge:
        return MQTTStatus(
            connected=False,
            enabled=mqtt_config.enabled,
            client_id=mqtt_config.client_id,
            broker=mqtt_config.host,
            port=mqtt_config.port,
            subscribed_topics=[]
        )
    
    # 使用 bridge 的 is_connected 属性
    connected = _mqtt_bridge.is_connected
    
    # 从配置获取订阅的主题
    subscribed_topics = [
        f"{mqtt_config.topic_prefix}/api/#",
        f"{mqtt_config.topic_prefix}/device/+/api/#"
    ]
    
    return MQTTStatus(
        connected=connected,
        enabled=mqtt_config.enabled,
        client_id=mqtt_config.client_id,
        broker=mqtt_config.host,
        port=mqtt_config.port,
        subscribed_topics=subscribed_topics
    )


@router.post(
    "/connect",
    response_model=MQTTConnectionResult,
    summary="连接MQTT",
    description="手动连接到MQTT Broker"
)
async def connect_mqtt():
    """手动连接MQTT"""
    if not _mqtt_bridge:
        raise HTTPException(status_code=503, detail="MQTT服务未初始化")
    
    if _mqtt_bridge.is_connected:
        return MQTTConnectionResult(
            success=True,
            message="MQTT已连接",
            connected=True
        )
    
    success = await _mqtt_bridge.connect()
    return MQTTConnectionResult(
        success=success,
        message="MQTT连接成功" if success else "MQTT连接失败",
        connected=_mqtt_bridge.is_connected
    )


@router.post(
    "/disconnect",
    response_model=MQTTConnectionResult,
    summary="断开MQTT连接",
    description="手动断开与MQTT Broker的连接"
)
async def disconnect_mqtt():
    """手动断开MQTT连接"""
    if not _mqtt_bridge:
        raise HTTPException(status_code=503, detail="MQTT服务未初始化")
    
    if not _mqtt_bridge.is_connected:
        return MQTTConnectionResult(
            success=True,
            message="MQTT未连接",
            connected=False
        )
    
    success = await _mqtt_bridge.disconnect()
    return MQTTConnectionResult(
        success=success,
        message="MQTT已断开" if success else "MQTT断开失败",
        connected=_mqtt_bridge.is_connected
    )


@router.post(
    "/reconnect",
    response_model=MQTTConnectionResult,
    summary="重新连接MQTT",
    description="重新连接到MQTT Broker"
)
async def reconnect_mqtt():
    """重新连接MQTT"""
    if not _mqtt_bridge:
        raise HTTPException(status_code=503, detail="MQTT服务未初始化")
    
    success = await _mqtt_bridge.reconnect()
    return MQTTConnectionResult(
        success=success,
        message="MQTT重连成功" if success else "MQTT重连失败",
        connected=_mqtt_bridge.is_connected
    )


@router.post(
    "/publish",
    summary="发布MQTT消息",
    description="通过API发布MQTT消息到指定主题"
)
async def publish_mqtt_message(request: MQTTMessage):
    """发布MQTT消息"""
    if not _mqtt_bridge:
        raise HTTPException(status_code=503, detail="MQTT服务未初始化")
    
    if not _mqtt_bridge.fast_mqtt:
        raise HTTPException(status_code=503, detail="MQTT未启用或未连接")
    
    try:
        await _mqtt_bridge.publish(request.topic, request.message)
        return {
            "status": "success",
            "topic": request.topic,
            "message": "消息已发布"
        }
    except Exception as e:
        logger.error(f"发布MQTT消息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发布消息失败: {str(e)}")


@router.get(
    "/routes",
    summary="获取API路由映射",
    description="获取已发现的API端点和对应的MQTT主题映射"
)
async def get_mqtt_routes():
    """获取API路由映射"""
    if not _mqtt_bridge:
        return {"routes": {}}
    
    routes = {}
    for path, info in _mqtt_bridge.api_routes.items():
        # 转换为MQTT主题格式
        mqtt_topic = path.replace('/', '+').strip('+')
        routes[path] = {
            "mqtt_topic": f"api{mqtt_topic}",
            "methods": info['methods'],
            "name": info['name']
        }
    
    return {"routes": routes, "total": len(routes)}
