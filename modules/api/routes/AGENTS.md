# API ROUTES KNOWLEDGE BASE

**Generated:** 2026-02-22
**Commit:** N/A
**Branch:** N/A

## OVERVIEW
Individual API route modules implementing the application endpoints.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Health monitoring | health.py | Service health check with status response |
| Config management | config.py | Runtime config updates with validation |

## CONVENTIONS
- FastAPI routers with explicit response models
- Pydantic models for request/response validation
- Comprehensive API documentation with examples
- Centralized logging for all requests
- HTTPException for error handling with proper status codes

## ANTI-PATTERNS (THIS PROJECT)
- No input sanitization beyond Pydantic validation
- Direct access to config manager without additional validation layers

## UNIQUE STYLES
- Detailed API documentation with JSON examples
- Request/response models with JSON schema examples
- Structured logging with context for each endpoint
- Config updates with immediate persistence to TOML