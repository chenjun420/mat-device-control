# MODULES KNOWLEDGE BASE

**Generated:** 2026-02-22
**Commit:** N/A
**Branch:** N/A

## OVERVIEW
Application modules containing core functionality, API endpoints, and device control logic.

## STRUCTURE
```
modules/
├── core/               # Core utilities (config, logging, response)
├── api/                # API routes and handlers  
├── device/             # Device control logic
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Configuration management | core/config.py | Thread-safe config manager with TOML persistence |
| Logging system | core/logging.py | Async logging with JSON formatter |
| API endpoints | api/routes/ | Health check and config management endpoints |
| Device operations | device/controller.py | Device connection management |

## CONVENTIONS
- All modules use thread-safe singletons for shared state
- Async logging used throughout all modules
- Pydantic models for request/response validation
- TOML-based configuration with runtime updates

## ANTI-PATTERNS (THIS PROJECT)
- Direct imports between modules without clear boundaries
- No clear separation between business logic and API layer

## UNIQUE STYLES
- Config manager singleton pattern
- Async logging with queue-based handlers
- Runtime configuration updates via API