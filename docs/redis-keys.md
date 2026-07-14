# Redis Key Registry

All keys are namespaced by purpose and use lowercase colon-separated names.

| Pattern | Type | TTL | Purpose |
| --- | --- | --- | --- |
| `job:{job_id}` | Hash | 24 hours by default | Job metadata, state, payload, result, and timestamps |
| `queue:jobs:pending` | List | None | Job IDs waiting for a worker |
| `queue:jobs:processing` | List | None | Job IDs claimed by a worker |
| `jobs:index` | Sorted set | None | Job IDs scored by creation time for bounded newest-first listing |
| `events:jobs` | Stream | Capped length | Durable ordered job lifecycle events for history and SSE clients |
| `rate_limit:fixed:{route}:{client_id}:{bucket}` | String | Two windows | Time-bucketed request counter |
| `rate_limit:sliding:{route}:{client_id}` | Sorted set | Window length | Request timestamps in the active sliding window |
| `cache:analytics:summary` | String (JSON) | Configurable | Cached analytics summary payload |
| `metrics:cache:hits` | String | None | Successful cache read counter |
| `metrics:cache:misses` | String | None | Cache generation counter |
| `session:{session_id}` | Hash | Configurable | Temporary user context and activity timestamps |
| `leaderboard:users` | Sorted set | None | Completed-job score per user |
| `events:activity` | Stream | Capped length | Recent user-visible system activity |
| `queue:jobs:retry` | Sorted set | None | Failed job IDs scored by next retry time |
| `queue:jobs:dead-letter` | List | None | Exhausted job IDs awaiting inspection/manual retry |
| `lock:job:{job_id}` | String | Worker lease | Prevents two workers from processing the same job |

## Queue Direction

The API adds jobs with `LPUSH`. Workers atomically claim the oldest job with
`BRPOPLPUSH`, moving it from the pending list to the processing list. The worker removes
the ID from the processing list after success or failure. This gives us a visible record
of in-flight work and avoids losing a job between dequeue and processing.

The API adds every new job to `jobs:index` in the same transaction as its hash and queue
entry. Listing reads only the requested number of IDs. If an indexed job hash has expired,
the service removes that stale ID from the sorted set.

## Job Event Stream

`events:jobs` records `job.created`, `job.started`, `job.completed`, and `job.failed`.
Each entry stores the job ID, resulting status, UTC timestamp, and an optional JSON detail.
The stream is approximately capped at `JOB_EVENTS_MAX_LENGTH` entries to bound memory.

The recent-events endpoint uses `XREVRANGE`. The live endpoint uses blocking `XREAD` and
sends each Redis stream ID as the SSE event ID. Browsers can reconnect with
`Last-Event-ID` and continue after the last event they received.

## Rate Limiting

The fixed-window limiter increments one counter per route, client, and calculated time
bucket. Its implementation is cheap and fully atomic, but traffic can burst around a
bucket boundary. Old bucket keys expire automatically.

The sliding-window limiter removes expired timestamps and stores each accepted request in
a sorted set. It uses `WATCH/MULTI` optimistic transactions so concurrent requests cannot
both consume the final slot. This strategy is smoother and more precise but uses more
memory and commands per request.

## Response Cache

The analytics demo uses cache-aside behavior: read Redis first, calculate only on a miss,
then store serialized JSON with `CACHE_TTL_SECONDS`. Explicit invalidation deletes the
resource key; the next read regenerates it. Hit and miss counters remain independent of
the cached value so expiration does not erase learning metrics.

The learning version intentionally does not add cache-stampede locking yet. Worker locks
and more advanced reliability controls are addressed in Phase 8.

## Sessions

Session hashes store only typed JSON-safe user context plus UTC creation and last-seen
timestamps. `SESSION_TTL_SECONDS` enforces automatic cleanup. When rolling expiration is
enabled, successful reads update `last_seen_at` and refresh the TTL in one transaction.
Opaque UUID identifiers prevent clients from choosing or enumerating session keys.

## Leaderboard And Activity

Successful worker completion increments the submitting user's score with `ZINCRBY` in the
same transaction as the completed job state and lifecycle events. `ZREVRANGE` returns top
users and `ZREVRANK` provides a zero-based Redis rank that the API converts to one-based.

The activity Stream is approximately capped at `ACTIVITY_MAX_LENGTH`. It provides a
human-readable feed separate from the structured job lifecycle Stream and currently
records job submission and processing transitions.

## Retry And Dead-Letter Flow

Transient failures increment `retry_count` and schedule the job in `queue:jobs:retry` with
an exponential backoff score. Workers use atomic `ZPOPMIN` to claim due retries and move
them back to the pending list without blocking job processing. When `max_retries` is
exceeded, the final failed transition and dead-letter insertion happen in one transaction.

`POST /jobs/{job_id}/retry` resets retry metadata and requeues only final failed jobs.
Per-job expiring locks prevent two workers from processing the same ID concurrently.
Retry and dead-letter depths are exposed by `/metrics` for operational visibility.
