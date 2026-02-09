# TASK-009: Integration Config

**Phase**: 3 - Overlays + Config
**Status**: [ ] Not Started
**Priority**: P1 - High
**Depends On**: TASK-008, TASK-000 (parity harness for status mapping)
**Service**: **admin-service**

## Objective

Implement client API integration configuration with encrypted credentials.

## Files to Create

```
admin-service/api/app/
├── core/
│   └── crypto.py
├── schemas/
│   └── integration.py
├── api/
│   └── integration.py
└── services/
    └── integration_service.py
```

## Authentication Types

| Type | Header | Description |
|------|--------|-------------|
| `none` | - | No authentication |
| `bearer` | `Authorization: Bearer {token}` | OAuth/JWT token |
| `api_key` | `{header}: {key}` | Configurable header name |
| `basic` | `Authorization: Basic {base64}` | Username:password |

## Update Methods

| Method | Description |
|--------|-------------|
| `polling` | Fetch status at intervals |
| `sse` | Server-sent events stream |
| `webhook` | Client pushes updates |

## Status Mapping

Maps client's arbitrary status values to canonical 5-status taxonomy (per STATUS-TAXONOMY.md):

| Canonical | Example Client Values |
|-----------|----------------------|
| `available` | Available, AVAILABLE, Open, OPEN |
| `reserved` | Reserved, Hold, OnHold, Pending |
| `sold` | Sold, SOLD, Purchased |
| `hidden` | Hidden, Unavailable, NotForSale |
| `unreleased` | Unreleased, Future, ComingSoon |

Default behavior: if client status not in mapping, defaults to `hidden`.

## API Endpoints

### GET /projects/{slug}/integration

Get current integration config.

**Response:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "api_base_url": "https://client.api.com",
  "auth_type": "bearer",
  "status_endpoint": "/api/units/status",
  "status_mapping": { ... },
  "update_method": "polling",
  "polling_interval_seconds": 30,
  "timeout_seconds": 10,
  "retry_count": 3,
  "has_credentials": true
}
```

Note: `has_credentials` indicates if credentials are stored, but actual values are never exposed.

### PUT /projects/{slug}/integration

Update integration config.

**Request:**
```json
{
  "api_base_url": "https://client.api.com",
  "auth_type": "bearer",
  "auth_credentials": {
    "token": "secret-token-value"
  },
  "status_endpoint": "/api/units/status",
  "status_mapping": {
    "available": ["Available", "Open"],
    "reserved": ["Reserved", "Hold"],
    "sold": ["Sold", "Purchased"],
    "hidden": ["Hidden"],
    "unreleased": ["Future"]
  },
  "update_method": "polling",
  "polling_interval_seconds": 30
}
```

### POST /projects/{slug}/integration/test

Test connection to client API.

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response_time_ms": 145,
  "sample_data": [...]
}
```

Or on failure:
```json
{
  "success": false,
  "error": "Connection timeout"
}
```

## Config Fields

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| `api_base_url` | string | null | Valid URL |
| `auth_type` | enum | none | none/bearer/api_key/basic |
| `status_endpoint` | string | null | Relative path |
| `status_mapping` | object | defaults | See mapping section |
| `update_method` | enum | polling | polling/sse/webhook |
| `polling_interval_seconds` | int | 30 | 5-300 |
| `timeout_seconds` | int | 10 | 1-60 |
| `retry_count` | int | 3 | 0-10 |

## Credential Fields (per auth_type)

| Auth Type | Fields |
|-----------|--------|
| `bearer` | `token` |
| `api_key` | `api_key`, `api_key_header` (default: X-API-Key) |
| `basic` | `username`, `password` |

## Encryption Requirements

All credential values must be:
1. Encrypted before storage using Fernet symmetric encryption
2. Derived key from application SECRET_KEY
3. Decrypted only when making actual API calls
4. Never returned in API responses

## Service Methods

| Method | Description |
|--------|-------------|
| `get_config(project_id)` | Get integration config |
| `update_config(project_id, data)` | Create/update config |
| `test_connection(project_id)` | Test API connectivity |
| `map_status(config, client_status)` | Map to canonical status |

## Acceptance Criteria

- [ ] Can save integration config
- [ ] Credentials encrypted in database
- [ ] Can test connection to client API
- [ ] Status mapping works correctly (5-status taxonomy)
- [ ] Different auth types supported (none, bearer, api_key, basic)
- [ ] Credentials never exposed in responses
- [ ] Connection test returns response time and sample data
