# DEVICE MODULE KNOWLEDGE BASE

**Generated:** 2026-02-23
**Commit:** N/A
**Branch:** N/A

## OVERVIEW
Device control framework with unified device access interface, protocol abstraction, and automatic device loading.

## STRUCTURE
```
modules/device/
├── __init__.py           # Module exports
├── base.py               # Base driver and data classes
├── enums.py              # Device enumerations
├── capabilities.py       # Device capability interfaces
├── controller.py         # Unified device access controller
├── factory.py            # Driver factory with lazy loading
├── loader.py             # Device initialization from config
├── manager.py            # Legacy device manager (deprecated)
├── registry.py           # Legacy driver registry (deprecated)
├── protocols/            # Communication protocols
│   ├── base_protocol.py  # Protocol abstraction
│   ├── scpi.py           # SCPI protocol handler
│   └── modbus.py         # Modbus protocol handler
├── families/             # Device family implementations
│   └── scpi_devices.py   # SCPI device base class
└── drivers/              # Specific device drivers
    ├── keysight/         # Keysight devices
    │   └── e36312a.py    # E36312A power supply
    └── siglent/          # Siglent devices
        └── sds1000x.py   # SDS1000X oscilloscope
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Device operations | controller.py | Unified access interface |
| Create devices | factory.py | Driver factory with caching |
| Load from config | loader.py | Auto-load from devices.toml |
| Protocol implementation | protocols/ | SCPI, Modbus handlers |
| Specific devices | drivers/ | Keysight, Siglent drivers |

## CONVENTIONS
- All devices accessed via `DeviceController` using `device_id`
- Use `controller.call(device_id, method, *args)` for unified access
- Use `controller.methods(device_id)` to query available methods
- Drivers are loaded lazily via `DriverFactory`

## UNIQUE STYLES
- Unified device access via single interface
- Python introspection for method discovery
- Lazy driver loading with caching
- Automatic device initialization from TOML config