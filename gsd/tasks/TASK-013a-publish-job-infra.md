# TASK-013a: Publish Job Infrastructure

**Phase**: 4 - Build Pipeline
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-002 (database schema)
**Blocks**: TASK-013b (publish workflow)
**Service**: **admin-service**

## Objective

Create the job infrastructure for the publish workflow, including the job model, SSE streaming, and status tracking.

> **Scope**: This task covers job infrastructure ONLY. The actual publish logic is in TASK-013b.

## Files to Create

```
admin-service/api/app/
├── models/
│   └── job.py
├── services/
│   └── job_service.py
├── api/
│   └── jobs.py
└── core/
    └── sse.py
```

## Job Model

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `job_type` | string(50) | tile_generation, svg_import, publish |
| `status` | string(20) | queued, running, completed, failed, cancelled |
| `progress` | int | 0-100 |
| `message` | text | Current step message |
| `result` | JSONB | Result on completion |
| `error` | text | Error message on failure |
| `logs` | JSONB | Array of log entries |
| `project_id` | FK → projects | Related project |
| `version_id` | FK → versions | Related version (nullable) |
| `created_by` | FK → users | Creator |
| `created_at` | timestamp | Creation time |
| `started_at` | timestamp | When job started running |
| `completed_at` | timestamp | When job finished |

### Log Entry Format
```json
{
  "timestamp": "2024-01-15T12:00:00Z",
  "level": "info",
  "message": "Processing overlays..."
}
```

## Job Service

Singleton service managing job lifecycle:

| Method | Description |
|--------|-------------|
| `create_job(db, type, project_id, created_by, ...)` | Create new job |
| `get_job(db, job_id)` | Get job by ID |
| `update_progress(db, job_id, progress, message)` | Update progress + broadcast SSE |
| `complete_job(db, job_id, result)` | Mark completed |
| `fail_job(db, job_id, error)` | Mark failed |
| `add_log(db, job_id, message, level)` | Add log entry |

All state changes broadcast via SSE to `job:{job_id}` channel.

## SSE Manager

Shared utility for Server-Sent Events (used by both job streaming and status proxy).

### SSEMessage Format
```
id: <message_id>
event: <event_type>
retry: <reconnect_ms>
data: <json_payload>

```
(blank line terminates message)

### SSEManager Methods
| Method | Description |
|--------|-------------|
| `subscribe(channel)` | Returns asyncio.Queue for receiving messages |
| `unsubscribe(channel, queue)` | Remove subscriber |
| `broadcast(channel, message)` | Send to all channel subscribers |
| `get_subscriber_count(channel)` | Count active subscribers |

## API Endpoints

### GET /jobs/{job_id}
Returns full job state including all logs.

### GET /jobs/{job_id}/stream
SSE stream for real-time job updates.

**Behavior:**
1. Send current job state immediately
2. Stream updates from SSE manager
3. Send ping every 30s for keepalive
4. Stop streaming when status is `completed` or `failed`

**Headers:**
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no`

## SSE Event Types

| Event | When | Data |
|-------|------|------|
| `job_update` | Progress change | `{id, status, progress, message, logs}` |
| `ping` | Every 30s | `{}` |

## Database Migration

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'queued',
    progress INTEGER DEFAULT 0,
    message TEXT,
    result JSONB,
    error TEXT,
    logs JSONB DEFAULT '[]',
    project_id UUID REFERENCES projects(id),
    version_id UUID REFERENCES versions(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_jobs_project ON jobs(project_id);
CREATE INDEX idx_jobs_status ON jobs(status);
```

## Acceptance Criteria

- [ ] Job model created with all fields
- [ ] Job service handles create, update, complete, fail operations
- [ ] Progress updates broadcast via SSE
- [ ] Logs captured with timestamp and level
- [ ] GET /jobs/{id} returns full job state
- [ ] GET /jobs/{id}/stream returns SSE
- [ ] Streaming stops when job completes/fails
- [ ] Ping keepalive sent every 30s
