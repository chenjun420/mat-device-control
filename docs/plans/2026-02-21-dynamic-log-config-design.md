# 日志动态配置功能设计

## 概述

增加日志级别动态控制，支持启动时通过 TOML 配置文件设置初始值，支持通过 API 动态修改并持久化。

## 需求

- 启动时从 TOML 配置文件读取日志设置
- 支持 API 动态修改日志级别、文件大小、个数、保留时间
- API 修改后持久化到配置文件

## 配置文件 (config.toml)

```toml
[app]
name = "mat-device-control"
debug = false

[log]
level = "INFO"
log_dir = "logs"
max_bytes = 10485760
backup_count = 10
retention_days = 7
format = "json"
```

## API 端点

### GET /api/config

获取当前配置

**响应:**
```json
{
  "app": {
    "name": "mat-device-control",
    "debug": false
  },
  "log": {
    "level": "INFO",
    "log_dir": "logs",
    "max_bytes": 10485760,
    "backup_count": 10,
    "retention_days": 7,
    "format": "json"
  }
}
```

### PATCH /api/config

更新配置（仅支持 log 相关字段）

**请求体:**
```json
{
  "log": {
    "level": "DEBUG",
    "max_bytes": 20971520,
    "backup_count": 20
  }
}
```

**响应:**
```json
{
  "success": true,
  "config": { ... }
}
```

## 文件改动

| 文件 | 改动 |
|------|------|
| `config.toml` | 新建 - 配置文件 |
| `modules/core/config.py` | 重构 - 支持文件加载/保存/动态修改 |
| `modules/core/logging.py` | 新增 `update_log_level()` 函数 |
| `modules/api/routes/config.py` | 新建 - 配置 API 路由 |
| `main.py` | 注册配置路由 |

## 数据流

```
启动 → 读取 config.toml → 初始化配置 → 配置日志系统

API PATCH → 验证参数 → 更新内存配置 → 更新日志级别 → 写入 config.toml → 返回响应
```
