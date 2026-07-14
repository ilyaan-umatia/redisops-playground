# RedisOps Playground

RedisOps Playground is a learning-first, production-style FastAPI project. Its first
vertical slice implements a Redis-backed background job queue with a separate worker.

## Features implemented:

- Redis hashes for durable job state
- Redis lists for FIFO queueing
- atomic pipelines for storing and enqueueing a job together
- `BRPOPLPUSH` for safe pending-to-processing handoff
- expiring keys with TTL
- Redis locks for worker ownership
- sorted sets for newest-first job indexing
- Redis Streams for durable real-time lifecycle events
- Server-Sent Events (SSE) with reconnect support
- fixed-window counters and sliding-window sorted-set rate limiting
- cache-aside JSON responses with TTL, metrics, and invalidation
- expiring Redis Hash sessions with rolling expiration
- sorted-set completion leaderboard and bounded activity feed
- delayed exponential retries, dead-letter queue, and manual recovery

## Architecture

```text
Client -> FastAPI -> Redis pending list -> Worker
              |              |              |
              `-> job hash <-+--------------'
```

The API validates requests and delegates Redis operations to `JobService`. The worker
runs independently, claims queued IDs, updates the corresponding job hash, and stores a
demo result.

## Run With Docker (Recommended)

Docker Desktop is the only prerequisite.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open the interactive API docs at <http://localhost:8000/docs>. Redis is exposed on port
`6379` for learning and inspection. The live operations dashboard is available at
<http://localhost:8000/>.

Create a demo job:

```powershell
$body = @{ user_id = "learner-1"; payload = @{ month = 7 } } | ConvertTo-Json
$job = Invoke-RestMethod -Method Post -Uri http://localhost:8000/jobs -ContentType application/json -Body $body
$job
Invoke-RestMethod -Uri "http://localhost:8000/jobs/$($job.id)"
```

The status moves from `queued` to `processing` and then `completed`.

Stop the stack with `docker compose down`. Add `-v` only when you intentionally want to
delete the Redis learning data.

## Run Tests

Tests use an in-memory fake Redis, so no Redis server is needed:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

If Python is not installed locally, run all checks during a Docker build:

```powershell
docker build --target test -t redisops-tests .
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Verify API and Redis connectivity |
| `POST` | `/jobs` | Validate, persist, and enqueue a demo job |
| `GET` | `/jobs?limit=20` | List recent jobs, newest first |
| `GET` | `/jobs/{job_id}` | Read current job status and result |
| `GET` | `/events?limit=20` | Read recent durable job events |
| `GET` | `/events/stream` | Subscribe to live job events over SSE |
| `GET` | `/metrics` | Read pending, processing, and event counts |
| `GET` | `/rate-limit-demo/fixed` | Exercise fixed-window limiting |
| `GET` | `/rate-limit-demo/sliding` | Exercise sliding-window limiting |
| `GET` | `/cache-demo` | Read or generate a cached analytics summary |
| `POST` | `/cache-demo/invalidate` | Explicitly invalidate the summary cache |
| `POST` | `/sessions` | Create an expiring user session |
| `GET` | `/sessions/{session_id}` | Read and refresh a session |
| `DELETE` | `/sessions/{session_id}` | Delete a session |
| `GET` | `/leaderboard` | List top users by completed jobs |
| `GET` | `/leaderboard/{user_id}` | Read a user's score and rank |
| `GET` | `/activity` | Read recent human-readable activity |
| `GET` | `/jobs/dead-letter` | Inspect jobs that exhausted retries |
| `POST` | `/jobs/{job_id}/retry` | Manually requeue a final failed job |

view of queue health, jobs, rankings, and activity; architecture and Redis-pattern guides
turn the repository into a reusable learning reference.
