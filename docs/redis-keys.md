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
