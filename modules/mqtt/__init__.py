"""MQTT模块 - 自动API端点映射到MQTT主题"""

from .bridge import MQTTBridge
from .router import router as mqtt_router, set_mqtt_bridge

__all__ = ["MQTTBridge", "mqtt_router", "set_mqtt_bridge"]
