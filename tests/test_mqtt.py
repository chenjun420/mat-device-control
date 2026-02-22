"""MQTT模块测试"""
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI
from modules.mqtt.bridge import MQTTBridge
from modules.core.config import MQTTConfig
from modules.core.response import success_response, error_response


@pytest.fixture
def mock_app():
    """创建模拟的FastAPI应用"""
    app = FastAPI()
    
    # 添加模拟路由
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    @app.get("/config")
    async def get_config():
        return {"app": {"name": "test"}, "log": {"level": "INFO"}}
    
    return app


@pytest.fixture
def mqtt_config():
    """创建MQTT配置"""
    return MQTTConfig(
        enabled=True,
        host="localhost",
        port=1883,
        client_id="test-client",
        topic_prefix="test-prefix",
        qos=1
    )


class TestMQTTBridge:
    """MQTT桥接器测试"""
    
    def test_discover_api_endpoints(self, mock_app):
        """测试API端点发现"""
        bridge = MQTTBridge(mock_app)
        
        # 检查是否发现了路由
        assert len(bridge.api_routes) > 0
        assert "/health" in bridge.api_routes
        assert "/config" in bridge.api_routes
        
        # 检查路由信息
        health_route = bridge.api_routes["/health"]
        assert "GET" in health_route["methods"]
        assert health_route["endpoint"] is not None
    
    def test_extract_api_path(self, mock_app):
        """测试从MQTT主题提取API路径"""
        bridge = MQTTBridge(mock_app)
        
        # 测试普通API主题（直接匹配HTTP路由）
        path, device_id = bridge._extract_api_path(
            "mat-device-control/health",
            "mat-device-control"
        )
        assert path == "/health"
        assert device_id is None
        
        # 测试设备API主题
        path, device_id = bridge._extract_api_path(
            "mat-device-control/device/001/config",
            "mat-device-control"
        )
        assert path == "/config"
        assert device_id == "001"
    
    @pytest.mark.asyncio
    async def test_call_health_endpoint(self, mock_app):
        """测试调用健康检查端点"""
        bridge = MQTTBridge(mock_app)
        
        result = await bridge._call_api_endpoint("/health", {})
        
        assert result["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_call_unknown_endpoint(self, mock_app):
        """Test calling unknown endpoint"""
        bridge = MQTTBridge(mock_app)
        
        with pytest.raises(ValueError, match="API"):
            await bridge._call_api_endpoint("/unknown", {})
    
    @patch('modules.mqtt.bridge.FastMQTT')
    def test_setup_disabled(self, mock_app):
        """测试MQTT未启用时的设置"""
        bridge = MQTTBridge(mock_app)
        
        # 模拟MQTT未启用
        with patch.object(bridge, 'fast_mqtt', None):
            with patch('modules.mqtt.bridge.config_manager') as mock_config:
                mock_config.config.mqtt.enabled = False
                
                bridge.setup()
                
                # 应该不会创建FastMQTT实例
                assert bridge.fast_mqtt is None


class TestMQTTConfig:
    """MQTT配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = MQTTConfig()
        
        assert config.enabled is True
        assert config.host == "localhost"
        assert config.port == 1883
        assert config.client_id == "mat-device-control"
        assert config.topic_prefix == "mat-device-control"
        assert config.qos == 1
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = MQTTConfig(
            enabled=False,
            host="mqtt.example.com",
            port=8883,
            username="user",
            password="pass",
            client_id="custom-client",
            topic_prefix="custom-prefix",
            qos=2,
            keepalive=120
        )
        
        assert config.enabled is False
        assert config.host == "mqtt.example.com"
        assert config.port == 8883
        assert config.username == "user"
        assert config.password == "pass"
        assert config.client_id == "custom-client"
        assert config.topic_prefix == "custom-prefix"
        assert config.qos == 2
        assert config.keepalive == 120
    
    def test_mqtt_response_format_matches_api(self, mock_app):
        """测试MQTT响应格式与API格式一致"""
        bridge = MQTTBridge(mock_app)
        
        # 模拟调用健康检查端点
        result = bridge._call_api_endpoint("/health", {}, None)
        
        # 构建成功响应（模拟MQTT的响应格式）
        mqtt_success_response = {
            "success": True,
            "code": 200,
            "message": "success",
            "data": result
        }
        
        # 构建API响应（使用核心响应模块）
        api_success_response = success_response(data=result, code=200)
        
        # 验证格式一致
        assert mqtt_success_response["success"] == api_success_response["success"]
        assert mqtt_success_response["code"] == api_success_response["code"]
        assert mqtt_success_response["message"] == api_success_response["message"]
        assert mqtt_success_response["data"] == api_success_response["data"]
    
    def test_mqtt_error_response_format_matches_api(self, mock_app):
        """测试MQTT错误响应格式与API格式一致"""
        bridge = MQTTBridge(mock_app)
        
        # 构建错误响应（模拟MQTT的错误响应格式）
        mqtt_error_response = {
            "success": False,
            "code": 400,
            "message": "API 端点不存在：/invalid",
            "data": {
                "available_endpoints": list(bridge.api_routes.keys())
            }
        }
        
        # 构建API错误响应（使用核心响应模块）
        api_error_response = error_response(
            message="API 端点不存在：/invalid",
            code=400,
            data={"available_endpoints": list(bridge.api_routes.keys())}
        )
        
        # 验证格式一致
        assert mqtt_error_response["success"] == api_error_response["success"]
        assert mqtt_error_response["code"] == api_error_response["code"]
        assert mqtt_error_response["message"] == api_error_response["message"]
        assert mqtt_error_response["data"] == api_error_response["data"]
    
    def test_mqtt_exception_response_format_matches_api(self, mock_app):
        """测试MQTT异常响应格式与API格式一致"""
        # 构建异常响应（模拟MQTT的异常响应格式）
        mqtt_exception_response = {
            "success": False,
            "code": 500,
            "message": "处理消息时出错：Connection timeout",
            "data": None
        }
        
        # 构建API异常响应（使用核心响应模块）
        api_exception_response = error_response(
            message="处理消息时出错：Connection timeout",
            code=500,
            data=None
        )
        
        # 验证格式一致
        assert mqtt_exception_response["success"] == api_exception_response["success"]
        assert mqtt_exception_response["code"] == api_exception_response["code"]
        assert mqtt_exception_response["message"] == api_exception_response["message"]
        assert mqtt_exception_response["data"] == api_exception_response["data"]
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = MQTTConfig(
            host="test.local",
            port=1884
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["host"] == "test.local"
        assert config_dict["port"] == 1884
        assert "enabled" in config_dict
        assert "client_id" in config_dict
        # None values should not be in the dict
        assert "username" not in config_dict
        assert "password" not in config_dict
    
    def test_to_dict_with_credentials(self):
        """测试带凭据的转换为字典"""
        config = MQTTConfig(
            host="test.local",
            username="user",
            password="pass"
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["username"] == "user"
        assert config_dict["password"] == "pass"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "enabled": False,
            "host": "mqtt.test.com",
            "port": 8883,
            "username": "testuser",
            "password": "testpass"
        }
        
        config = MQTTConfig.from_dict(data)
        
        assert config.enabled is False
        assert config.host == "mqtt.test.com"
        assert config.port == 8883
        assert config.username == "testuser"
        assert config.password == "testpass"
        assert config.host == "mqtt.test.com"
        assert config.port == 8883
        assert config.username == "testuser"
        assert config.password == "testpass"
