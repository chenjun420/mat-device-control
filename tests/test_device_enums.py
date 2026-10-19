"""设备枚举类型单元测试"""


from modules.device.enums import (
    ConnectionType,
    DeviceCategory,
    DeviceState,
    ProtocolType,
)


class TestDeviceCategory:
    """DeviceCategory 测试类"""

    def test_device_categories_exist(self):
        """测试设备类别枚举值"""
        assert DeviceCategory.POWER_SUPPLY == "power_supply"
        assert DeviceCategory.ELECTRONIC_LOAD == "electronic_load"
        assert DeviceCategory.POWER_METER == "power_meter"
        assert DeviceCategory.SIGNAL_GENERATOR == "signal_generator"
        assert DeviceCategory.SPECTRUM_ANALYZER == "spectrum_analyzer"
        assert DeviceCategory.MULTIMETER == "multimeter"
        assert DeviceCategory.OSCILLOSCOPE == "oscilloscope"
        assert DeviceCategory.GENERIC == "generic"

    def test_device_category_string_conversion(self):
        """测试设备类别字符串转换"""
        # Use .value to get the string value
        assert DeviceCategory.POWER_SUPPLY.value == "power_supply"
        assert DeviceCategory.ELECTRONIC_LOAD.value == "electronic_load"

    def test_device_category_from_string(self):
        """测试从字符串创建设备类别"""
        category = DeviceCategory("power_supply")
        assert category == DeviceCategory.POWER_SUPPLY

    def test_device_category_all_values(self):
        """测试所有设备类别值"""
        categories = [c.value for c in DeviceCategory]
        assert len(categories) == 8
        assert "power_supply" in categories
        assert "electronic_load" in categories


class TestConnectionType:
    """ConnectionType 测试类"""

    def test_connection_types_exist(self):
        """测试连接类型枚举值"""
        assert ConnectionType.TCPIP == "tcpip"
        assert ConnectionType.USB == "usb"
        assert ConnectionType.SERIAL == "serial"
        assert ConnectionType.GPIB == "gpib"
        assert ConnectionType.VXI11 == "vxi11"
        assert ConnectionType.HISLIP == "hislip"
        assert ConnectionType.VIRTUAL == "virtual"

    def test_connection_type_string_conversion(self):
        """测试连接类型字符串转换"""
        assert ConnectionType.TCPIP.value == "tcpip"
        assert ConnectionType.USB.value == "usb"

    def test_connection_type_from_string(self):
        """测试从字符串创建连接类型"""
        conn_type = ConnectionType("serial")
        assert conn_type == ConnectionType.SERIAL

    def test_connection_type_all_values(self):
        """测试所有连接类型值（新增 VIRTUAL 后为 7 个）"""
        conn_types = [c.value for c in ConnectionType]
        assert len(conn_types) == 7
        assert "virtual" in conn_types


class TestProtocolType:
    """ProtocolType 测试类"""

    def test_protocol_types_exist(self):
        """测试协议类型枚举值"""
        assert ProtocolType.VISA == "visa"
        assert ProtocolType.SCPI == "scpi"
        assert ProtocolType.MODBUS == "modbus"
        assert ProtocolType.MODBUS_TCP == "modbus_tcp"
        assert ProtocolType.MODBUS_RTU == "modbus_rtu"
        assert ProtocolType.CUSTOM == "custom"

    def test_protocol_type_string_conversion(self):
        """测试协议类型字符串转换"""
        assert ProtocolType.VISA.value == "visa"
        assert ProtocolType.SCPI.value == "scpi"

    def test_protocol_type_from_string(self):
        """测试从字符串创建协议类型"""
        protocol = ProtocolType("modbus")
        assert protocol == ProtocolType.MODBUS

    def test_protocol_type_all_values(self):
        """测试所有协议类型值"""
        protocols = [p.value for p in ProtocolType]
        assert len(protocols) == 6


class TestDeviceState:
    """DeviceState 测试类"""

    def test_device_states_exist(self):
        """测试设备状态枚举值"""
        assert DeviceState.DISCONNECTED == "disconnected"
        assert DeviceState.CONNECTING == "connecting"
        assert DeviceState.CONNECTED == "connected"
        assert DeviceState.READY == "ready"
        assert DeviceState.BUSY == "busy"
        assert DeviceState.ERROR == "error"
        assert DeviceState.UNKNOWN == "unknown"

    def test_device_state_string_conversion(self):
        """测试设备状态字符串转换"""
        assert DeviceState.CONNECTED.value == "connected"
        assert DeviceState.ERROR.value == "error"

    def test_device_state_from_string(self):
        """测试从字符串创建设备状态"""
        state = DeviceState("ready")
        assert state == DeviceState.READY

    def test_device_state_all_values(self):
        """测试所有设备状态值"""
        states = [s.value for s in DeviceState]
        assert len(states) == 7

    def test_device_state_is_connected(self):
        """测试设备状态判断方法"""
        assert DeviceState.CONNECTED.is_connected()
        assert DeviceState.READY.is_connected()
        assert DeviceState.BUSY.is_connected()
        assert not DeviceState.DISCONNECTED.is_connected()
        assert not DeviceState.ERROR.is_connected()

    def test_device_state_is_error(self):
        """测试设备错误状态判断方法"""
        assert DeviceState.ERROR.is_error()
        assert not DeviceState.CONNECTED.is_error()
        assert not DeviceState.READY.is_error()
