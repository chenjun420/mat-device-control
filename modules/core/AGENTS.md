# CORE MODULE KNOWLEDGE BASE

**Generated:** 2026-02-22
**Commit:** N/A
**Branch:** N/A

## OVERVIEW
Core utilities including configuration management, logging system, and response handling.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Configuration management | config.py | Thread-safe config manager with TOML persistence |
| Logging system | logging.py | Async logging with JSON formatter and file rotation |
| Response handling | response.py | Custom response classes and middleware |
| Exception handling | exceptions.py | Custom exception classes |

## CONVENTIONS
- Singletons for shared state (ConfigManager, AsyncLogHandler)
- Thread-safe design for concurrent access
- TOML-based configuration with runtime updates
- JSON-formatted logs with structured data
- Async logging via QueueHandler/QueueListener pattern

## ANTI-PATTERNS (THIS PROJECT)
- Circular import risks if not careful with imports between core modules
- Singleton pattern may complicate testing

## UNIQUE STYLES
- Async logging with queue-based non-blocking writes
- Runtime-configurable log settings
- Thread-safe config manager with persistence
- JSON-formatted logs with orjson for performance