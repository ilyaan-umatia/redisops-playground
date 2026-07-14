# Redis Key Registry

All keys are namespaced by purpose and use lowercase colon-separated names.

| Pattern | Type | TTL | Purpose |
| --- | --- | --- | --- |
| `job:{job_id}` | Hash | 24 hours by default | Job metadata, state, payload, result, and timestamps |
| `queue:jobs:pending` | List | None | Job IDs waiting for a worker |
| `queue:jobs:processing` | List | None | Job IDs claimed by a worker |
| `jobs:index` | Sorted set | None | Job IDs scored by creation time for bounded newest-first listing |
| `lock:job:{job_id}` | String | Worker lease | Prevents two workers from processing the same job |

## Queue Direction

The API adds jobs with `LPUSH`. Workers atomically claim the oldest job with
`BRPOPLPUSH`, moving it from the pending list to the processing list. The worker removes
the ID from the processing list after success or failure. This gives us a visible record
of in-flight work and avoids losing a job between dequeue and processing.

The API adds every new job to `jobs:index` in the same transaction as its hash and queue
entry. Listing reads only the requested number of IDs. If an indexed job hash has expired,
the service removes that stale ID from the sorted set.
