# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-22
**Commit:** N/A
**Branch:** N/A

## OVERVIEW
MAT Device Control - FastAPI-based device control service with async logging and dynamic config management.

## STRUCTURE
```
./
├── main.py                 # Application entry point (FastAPI app)
├── config.toml             # Runtime configuration (app/log/mqtt settings)
├── pyproject.toml          # Project dependencies and metadata
├── README.md               # Project documentation
├── .python-version         # Python version requirement
├── modules/                # Application modules
│   ├── core/               # Core utilities (config, logging, response)
│   ├── api/                # API routes and handlers
│   ├── mqtt/               # MQTT integration (bridge, router)
│   └── device/             # Device control logic
├── tests/                  # Test suite
└── docs/                   # Documentation
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Application startup | main.py | FastAPI app with lifespan management |
| Configuration | modules/core/config.py | TOML-based config with dynamic updates |
| Logging system | modules/core/logging.py | Async logging with JSON formatter |
| API endpoints | modules/api/routes/ | Health check and config management |
| MQTT integration | modules/mqtt/ | MQTT bridge and router for device communication |
| Device control | modules/device/controller.py | Device connection management |
| Tests | tests/ | Pytest-based test suite |

## CONVENTIONS
- Python 3.14+ (unusual - ensure compatible runtime)
- FastAPI with Pydantic v2 models
- TOML for configuration files
- JSON formatted logs with orjson
- Async logging via QueueHandler/QueueListener
- Dynamic config updates via API + persistence
- MQTT integration using fastapi-mqtt for async communication

## ANTI-PATTERNS (THIS PROJECT)
- Python 3.14 requirement (does not exist yet - likely should be 3.12/3.13)
- No pre-commit hooks or automated linting
- No CI/CD pipeline configuration
- Root-level main.py instead of src/ layout

## UNIQUE STYLES
- Async logging system with file rotation
- Runtime-configurable log settings
- Thread-safe config manager with persistence
- Automatic API endpoint discovery and MQTT topic mapping
- Async MQTT message handling with FastAPI integration

## COMMANDS
```bash
# Development
uv run uvicorn main:app --reload

# Tests
uv run pytest
uv run pytest -v
uv run pytest --cov=modules

# Format/Type check (recommended)
uv run ruff format .
uv run mypy modules/
```

## NOTES
- Application uses advanced async logging with queue-based non-blocking writes
- Configuration can be modified at runtime via API and persists to config.toml
- Python version in pyproject.toml (3.14) appears to be incorrect - Python 3.14 doesn't exist yet
- MQTT support automatically discovers API endpoints and maps them to MQTT topics
- MQTT message format follows topic pattern: `{prefix}/api/{path}` or `{prefix}/device/{device_id}/api/{path}`
- Responses are published to `{original_topic}/response`