"""MQTT 桥接器 - 自动发现 API 端点并映射到 MQTT 主题"""
import json
from typing import Dict, Any, Optional

from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig
from gmqtt.mqtt.constants import MQTTv311

from modules.core.logging import get_logger
from modules.core.config import config_manager


logger = get_logger(__name__)


class MQTTBridge:
    """MQTT 与 FastAPI 的桥接器"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.fast_mqtt: Optional[FastMQTT] = None
        self.api_routes: Dict[str, Dict[str, Any]] = {}
        self._connected: bool = False
        
        # 初始化 API 路由映射
        self._discover_api_endpoints()
        
    def _discover_api_endpoints(self):
        """自动发现所有 API 端点"""
        for route in self.app.routes:
            try:
                path = getattr(route, 'path', None)
                methods = getattr(route, 'methods', None)
                endpoint = getattr(route, 'endpoint', None)
                
                if path and methods and endpoint:
                    self.api_routes[path] = {
                        'methods': list(methods) if methods else [],
                        'endpoint': endpoint,
                        'name': getattr(route, 'name', str(endpoint))
                    }
                    logger.info(f"发现 API 端点：{path} [{', '.join(methods)}]")
            except AttributeError:
                continue
        
        logger.info(f"共发现 {len(self.api_routes)} 个 API 端点")
    
    def setup(self):
        """设置 MQTT 连接（仅配置，不主动连接）"""
        mqtt_config = config_manager.config.mqtt
        
        if not mqtt_config.enabled:
            logger.info("MQTT 未启用，跳过初始化")
            return
        
        config = MQTTConfig(
            host=mqtt_config.host,
            port=mqtt_config.port,
            username=mqtt_config.username,
            password=mqtt_config.password,
            keepalive=mqtt_config.keepalive,
            version=MQTTv311
        )
        
        self.fast_mqtt = FastMQTT(
            config=config,
            client_id=mqtt_config.client_id
        )
        
        self.fast_mqtt.init_app(self.app)
        logger.info(f"MQTT 已配置：{mqtt_config.host}:{mqtt_config.port}")
        self._register_handlers()
    
    async def connect(self) -> bool:
        """
        主动连接 MQTT Broker
        
        Returns:
            bool: 连接是否成功
        """
        if not self.fast_mqtt:
            logger.warning("MQTT 未初始化，无法连接")
            return False
        
        if self._connected:
            logger.info("MQTT 已连接，跳过重复连接")
            return True
        
        try:
            await self.fast_mqtt.mqtt_startup()
            self._connected = True
            logger.info("MQTT 连接成功")
            return True
        except Exception as e:
            logger.error(f"MQTT 连接失败: {e}", exc_info=True)
            return False
    
    async def disconnect(self) -> bool:
        """
        断开 MQTT 连接
        
        Returns:
            bool: 断开是否成功
        """
        if not self.fast_mqtt:
            logger.warning("MQTT 未初始化，无需断开")
            return True
        
        if not self._connected:
            logger.info("MQTT 未连接，跳过断开操作")
            return True
        
        try:
            await self.fast_mqtt.mqtt_shutdown()
            self._connected = False
            logger.info("MQTT 已断开连接")
            return True
        except Exception as e:
            logger.error(f"MQTT 断开连接失败: {e}", exc_info=True)
            return False
    
    async def reconnect(self) -> bool:
        """
        重新连接 MQTT Broker
        
        Returns:
            bool: 重连是否成功
        """
        logger.info("正在重新连接 MQTT...")
        await self.disconnect()
        return await self.connect()
    
    @property
    def is_connected(self) -> bool:
        """检查 MQTT 是否已连接"""
        if not self.fast_mqtt:
            return False
        
        # 优先使用内部状态
        if not self._connected:
            return False
        
        # 尝试从客户端获取实际连接状态
        try:
            if hasattr(self.fast_mqtt, 'mqtt_client'):
                mqtt_client = self.fast_mqtt.mqtt_client
                if mqtt_client and hasattr(mqtt_client, 'is_connected'):
                    return mqtt_client.is_connected
        except Exception:
            pass
        
        return self._connected
    
    def _register_handlers(self):
        """注册 MQTT 消息处理器"""
        if not self.fast_mqtt:
            return
        
        mqtt_client = self.fast_mqtt
        mqtt_config = config_manager.config.mqtt
        topic_prefix = mqtt_config.topic_prefix
        
        @mqtt_client.on_connect()
        def on_connect(client, _flags, _rc, _properties):
            logger.info(f"MQTT 已连接：{mqtt_config.client_id}")
            # 订阅所有直接路径（匹配HTTP路由）
            client.subscribe(f"{topic_prefix}/#", qos=mqtt_config.qos)
            logger.info(f"已订阅主题：{topic_prefix}/#")
            # 订阅设备相关路径
            client.subscribe(f"{topic_prefix}/device/+/+#", qos=mqtt_config.qos)
            logger.info(f"已订阅主题：{topic_prefix}/device/+/+#")
        
        @mqtt_client.on_disconnect()
        def on_disconnect(client, _packet, _exc=None):
            logger.info(f"MQTT 已断开：{mqtt_config.client_id}")
        
        @mqtt_client.on_message()
        async def on_message(client, topic, payload, _qos, _properties):
            # 忽略响应消息，避免无限循环
            if topic.startswith('response/'):
                return
            
            try:
                logger.info(f"收到 MQTT 消息：{topic}")
                
                try:
                    message_data = json.loads(payload.decode('utf-8'))
                except json.JSONDecodeError:
                    message_data = {"raw_payload": payload.decode('utf-8')}
                
                api_path, device_id = self._extract_api_path(topic, topic_prefix)
                
                if api_path in self.api_routes:
                    result = await self._call_api_endpoint(api_path, message_data, device_id)
                    
                    # 使用与API相同的统一响应格式
                    response_payload = json.dumps({
                        "success": True,
                        "code": 200,
                        "message": "success",
                        "data": result
                    }, ensure_ascii=False)
                    
                    mqtt_client.publish(f"response/{topic}", response_payload, qos=mqtt_config.qos)
                    logger.info(f"已发布响应到：response/{topic}")
                else:
                    # 错误响应也使用统一格式
                    response_payload = json.dumps({
                        "success": False,
                        "code": 400,
                        "message": f"API 端点不存在：{api_path}",
                        "data": {
                            "available_endpoints": list(self.api_routes.keys())
                        }
                    }, ensure_ascii=False)
                    
                    mqtt_client.publish(f"response/{topic}", response_payload, qos=mqtt_config.qos)
                    logger.warning(f"API 端点不存在：{api_path}")
                    
            except Exception as e:
                logger.error(f"处理 MQTT 消息时出错：{e}", exc_info=True)
                response_payload = json.dumps({
                    "success": False,
                    "code": 500,
                    "message": f"处理消息时出错：{str(e)}",
                    "data": None
                }, ensure_ascii=False)
                mqtt_client.publish(f"response/{topic}", response_payload, qos=mqtt_config.qos)
    
    @staticmethod
    def _extract_api_path(topic: str, topic_prefix: str) -> tuple[str, Optional[str]]:
        """
        从MQTT主题提取API路径
        
        Args:
            topic: MQTT主题，如 "mat-device-control/health" 或 "mat-device-control/device/001/config"
            topic_prefix: 主题前缀，如 "mat-device-control"
        
        Returns:
            tuple: (api_path, device_id)
        """
        parts = topic.split('/')
        
        # 移除主题前缀
        if parts[0] == topic_prefix:
            parts = parts[1:]
        
        device_id = None
        
        # 处理设备相关路径: topic_prefix/device/{device_id}/{path}
        if len(parts) >= 3 and parts[0] == 'device':
            device_id = parts[1]
            parts = parts[2:]  # 移除 "device/{device_id}"
        
        # 剩余部分就是API路径
        api_path = '/' + '/'.join(parts) if parts else '/'
        return api_path, device_id
    
    async def _call_api_endpoint(
        self, 
        path: str, 
        data: Dict[str, Any],
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用 API 端点
        
        Args:
            path: API 路径
            data: 请求数据
            device_id: 设备 ID（可选，用于日志记录）
        
        Returns:
            API 响应数据
        """
        route_info = self.api_routes.get(path)
        if not route_info:
            raise ValueError(f"API 端点不存在：{path}")
        
        endpoint = route_info['endpoint']
        if not endpoint:
            raise ValueError(f"API 端点没有处理函数：{path}")
        
        try:
            endpoint_name = endpoint.__name__
            
            if endpoint_name in ('health_check', 'get_config'):
                result = await endpoint()
                return result.model_dump() if hasattr(result, 'model_dump') else result
            
            elif endpoint_name == 'update_config':
                from modules.api.routes.config import ConfigUpdateRequest
                request_obj = ConfigUpdateRequest(**data)
                result = await endpoint(request_obj)
                return result.model_dump() if hasattr(result, 'model_dump') else result
            
            else:
                logger.warning(f"未知的 API 端点类型：{endpoint_name}")
                return {"message": f"已处理 {endpoint_name}", "data": data}
                
        except Exception as e:
            logger.error(f"调用 API 端点 {path} 时出错：{e}", exc_info=True)
            raise
    
    async def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        发布 MQTT 消息
        
        Args:
            topic: MQTT 主题
            message: 消息内容
        
        Returns:
            bool: 发布是否成功
        """
        if not self.fast_mqtt:
            logger.warning("MQTT 未初始化，无法发布消息")
            return False
        
        if not self._connected:
            logger.warning("MQTT 未连接，无法发布消息")
            return False
        
        mqtt_client = self.fast_mqtt
        mqtt_config = config_manager.config.mqtt
        full_topic = f"{mqtt_config.topic_prefix}/{topic}"
        
        payload = json.dumps(message, ensure_ascii=False)
        mqtt_client.publish(full_topic, payload, qos=mqtt_config.qos)
        logger.info(f"已发布 MQTT 消息到：{full_topic}")
        return True
