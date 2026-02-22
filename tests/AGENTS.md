# TESTS KNOWLEDGE BASE

**Generated:** 2026-02-22
**Commit:** N/A
**Branch:** N/A

## OVERVIEW
Test suite for the MAT Device Control application.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| API testing | test_api.py | Tests for health check and config endpoints |
| Configuration tests | test_config.py | Tests for config management functionality |
| Logging tests | test_logging.py | Tests for async logging system |

## CONVENTIONS
- Pytest with pytest-asyncio for async tests
- Pythonpath set to "." for module imports
- asyncio_mode set to "auto" (though "strict" is recommended)

## ANTI-PATTERNS (THIS PROJECT)
- No conftest.py for shared fixtures
- No integration tests for device controller
- Limited test coverage for async logging system

## UNIQUE STYLES
- Async testing with pytest-asyncio
- Direct testing of FastAPI endpoints
- Configuration testing with runtime updates