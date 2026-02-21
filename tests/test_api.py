"""API 路由单元测试"""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client():
    """同步测试客户端"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """异步测试客户端"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


class TestHealthEndpoint:
    """健康检查端点测试类"""

    def test_health_check(self, client):
        """测试健康检查返回正确响应"""
        response = client.get("/health")
        
        assert response.status_code == 200
        result = response.json()
        # 统一响应格式
        assert result["success"] is True
        assert result["code"] == 200
        data = result["data"]
        assert data["status"] == "healthy"
        assert data["service"] == "mat-device-control"

    def test_health_check_content_type(self, client):
        """测试健康检查返回 JSON 内容类型"""
        response = client.get("/health")
        
        assert response.headers["content-type"] == "application/json"


class TestConfigEndpoints:
    """配置端点测试类"""

    def test_get_config(self, client):
        """测试获取配置"""
        response = client.get("/api/config")
        
        assert response.status_code == 200
        result = response.json()
        # 统一响应格式
        assert result["success"] is True
        data = result["data"]
        
        assert "app" in data
        assert "log" in data
        assert data["app"]["name"] == "mat-device-control"
        assert "level" in data["log"]
        assert "max_bytes" in data["log"]
        assert "backup_count" in data["log"]

    def test_update_log_level(self, client):
        """测试更新日志级别"""
        # 先设置为 INFO
        client.patch("/api/config", json={"log": {"level": "INFO"}})
        
        # 更新为 DEBUG
        response = client.patch(
            "/api/config",
            json={"log": {"level": "DEBUG"}}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        data = result["data"]
        assert data["log"]["level"] == "DEBUG"

    def test_update_multiple_fields(self, client):
        """测试更新多个字段"""
        response = client.patch(
            "/api/config",
            json={
                "log": {
                    "level": "WARNING",
                    "max_bytes": 20971520,
                    "backup_count": 15
                }
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        data = result["data"]
        assert data["log"]["level"] == "WARNING"
        assert data["log"]["max_bytes"] == 20971520
        assert data["log"]["backup_count"] == 15

    def test_update_invalid_log_level(self, client):
        """测试更新无效日志级别"""
        response = client.patch(
            "/api/config",
            json={"log": {"level": "INVALID"}}
        )
        
        # 统一响应格式，HTTP 200，业务码表示错误
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert result["code"] == 422

    def test_update_invalid_backup_count(self, client):
        """测试更新无效的备份数量"""
        response = client.patch(
            "/api/config",
            json={"log": {"backup_count": 0}}  # 最小值为 1
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert result["code"] == 422

    def test_update_backup_count_too_large(self, client):
        """测试备份数量超出最大值"""
        response = client.patch(
            "/api/config",
            json={"log": {"backup_count": 150}}  # 最大值为 100
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert result["code"] == 422

    def test_update_invalid_retention_days(self, client):
        """测试更新无效的保留天数"""
        response = client.patch(
            "/api/config",
            json={"log": {"retention_days": 0}}  # 最小值为 1
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert result["code"] == 422

    def test_update_invalid_format(self, client):
        """测试更新无效的日志格式"""
        response = client.patch(
            "/api/config",
            json={"log": {"format": "xml"}}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert result["code"] == 422

    def test_update_empty_body(self, client):
        """测试空请求体"""
        response = client.patch("/api/config", json={})
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True  # 空更新应该成功

    @pytest.mark.asyncio
    async def test_get_config_async(self, async_client):
        """测试异步获取配置"""
        response = await async_client.get("/api/config")
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        data = result["data"]
        assert "app" in data
        assert "log" in data
