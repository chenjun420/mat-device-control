# MQTT MODULE KNOWLEDGE BASE

**Generated:** 2026-02-22
**Commit:** N/A
**Branch:** N/A

## OVERVIEW
MQTT integration module with automatic API endpoint discovery and topic mapping.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| MQTT bridge | bridge.py | Automatic API endpoint discovery and MQTT topic mapping |
| MQTT router | router.py | MQTT-related API endpoints for status and message publishing |
| MQTT config | core/config.py | MQTTConfig dataclass with broker settings |

## CONVENTIONS
- Use fastapi-mqtt for async MQTT integration
- Automatic discovery of FastAPI endpoints at startup
- MQTT topics follow pattern: `{prefix}/api/{path}` or `{prefix}/device/{device_id}/api/{path}`
- Responses published to `{original_topic}/response`
- JSON message format for all MQTT payloads
- QoS 1 (at least once) by default

## ANTI-PATTERNS (THIS PROJECT)
- No authentication/authorization for MQTT messages
- No message validation beyond JSON parsing
- Direct API endpoint calls without request context mocking

## UNIQUE STYLES
- Automatic API endpoint discovery from FastAPI routes
- Async message handling with FastAPI integration
- Unified logging between HTTP and MQTT interfaces
- Runtime-configurable MQTT broker settings via config.toml
- Support for both general and device-specific API topics

## MQTT TOPIC PATTERNS

### General API Topics
- `mat-device-control/api/health` - Health check
- `mat-device-control/api/config` - Get/Patch config

### Device-Specific Topics
- `mat-device-control/device/{device_id}/api/health` - Device health check
- `mat-device-control/device/{device_id}/api/config` - Device config

### Response Topics
- `{original_topic}/response` - All responses published here

## MESSAGE FORMAT

### Request
```json
{
  "log": {
    "level": "DEBUG"
  }
}
```

### Success Response
```json
{
  "status": "success",
  "result": {...},
  "original_topic": "mat-device-control/api/config"
}
```

### Error Response
```json
{
  "status": "error",
  "error": "Error message",
  "available_endpoints": [...]
}
```

## TESTING
Run MQTT tests: `uv run pytest tests/test_mqtt.py -v`

## USAGE EXAMPLE

```bash
# Subscribe to responses
mosquitto_sub -h localhost -t "mat-device-control/#" -v

# Health check via MQTT
mosquitto_pub -h localhost -t "mat-device-control/api/health" -m "{}"

# Update config via MQTT
mosquitto_pub -h localhost -t "mat-device-control/api/config" \
  -m '{"log": {"level": "DEBUG"}}'
```
