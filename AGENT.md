# AGENT.md

## Project Recommendation

Build **RedisOps Playground**: a small but production-style backend that demonstrates the most important Redis patterns in one coherent project.

This project is the best fit for learning because it is:

- small enough to finish
- practical enough to feel real
- broad enough to cover Redis deeply
- easy to extend with new Redis features later

## Product Idea

RedisOps Playground is a backend service with a small dashboard and API that lets users:

- submit background jobs
- track job status in real time
- apply API rate limits
- cache expensive responses
- manage temporary sessions
- view a live leaderboard and activity feed

The goal is not to build a huge product. The goal is to practice Redis properly through real features.

## Why This Project

This single project teaches:

- `Strings` for counters and cache entries
- `Hashes` for job/session/user metadata
- `Lists` or `Streams` for queues and event feeds
- `Sets` for uniqueness and membership checks
- `Sorted Sets` for leaderboards and time-ordered activity
- `TTL` for expiration and cleanup
- `Pub/Sub` or `Streams` consumer patterns for real-time updates
- `Distributed locks` for safe worker coordination
- `Pipelines` for efficient batched Redis operations

## Recommended Stack

Use this stack unless the user asks for another:

- Backend: `Python 3.12`
- API framework: `FastAPI`
- Redis client: `redis-py`
- Task worker: custom worker with Redis queue or Redis Streams consumer
- Frontend: minimal `HTML + HTMX` or very small `React` dashboard
- Testing: `pytest`
- Local environment: `Docker Compose`

## Architecture

The system should have these parts:

1. `api/`
   Exposes REST endpoints for jobs, cache demo, sessions, leaderboard, and metrics.

2. `worker/`
   Pulls jobs from Redis, processes them, updates state, and emits events.

3. `dashboard/`
   Shows live job states, queue depth, leaderboard, cache hits, and rate-limit counters.

4. `redis/`
   Central persistence and coordination layer.

## Core Redis Features To Implement

### 1. Job Queue

Users can submit jobs like:

- resize-image simulation
- report-generation simulation
- email-send simulation

Redis usage:

- queue pending jobs in `Lists` or `Streams`
- store job details in `Hashes`
- track retry counts with `Strings` or `Hashes`
- set TTL on completed job metadata if desired

Minimum job states:

- `queued`
- `processing`
- `completed`
- `failed`
- `retrying`

### 2. Real-Time Job Updates

The client should be able to see job progress.

Redis usage:

- use `Pub/Sub` for simple live updates
- or use `Streams` if a more durable event log is preferred

Track events like:

- job created
- job started
- job progressed
- job completed
- job failed

### 3. Rate Limiter

Protect selected API routes with Redis-backed rate limiting.

Implement:

- fixed-window limiter first
- sliding-window limiter second

Redis usage:

- counters with TTL
- optionally sorted sets for sliding-window timestamps

### 4. Response Cache

Create one route that simulates expensive work and cache its response.

Examples:

- analytics summary
- fake product catalog
- expensive reporting endpoint

Redis usage:

- cache JSON payloads with TTL
- add cache invalidation on relevant mutations

Track:

- cache hit count
- cache miss count

### 5. Session Store

Implement temporary user sessions.

Redis usage:

- session objects in `Hashes` or JSON strings
- TTL for expiration
- optional rolling expiration refresh

### 6. Leaderboard

Track something score-based.

Examples:

- most jobs completed by user
- fastest workers
- most active API clients

Redis usage:

- `Sorted Sets`

Expose:

- top 10 leaderboard
- rank of a user
- score updates after relevant actions

### 7. Activity Feed

Maintain a recent system feed.

Redis usage:

- `Streams` or `Lists`
- keep only the latest N events

Examples:

- new job submitted
- rate limit triggered
- cache invalidated
- session expired

### 8. Safe Worker Coordination

Prevent duplicate processing in multi-worker scenarios.

Redis usage:

- lock key with expiration
- heartbeat or lease-renewal if needed

The first version can be simple, but correctness matters.

## Suggested API Surface

Implement endpoints similar to:

- `POST /jobs`
- `GET /jobs/{job_id}`
- `GET /jobs`
- `POST /jobs/{job_id}/retry`
- `GET /events`
- `GET /leaderboard`
- `GET /cache-demo`
- `POST /cache-demo/invalidate`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `DELETE /sessions/{session_id}`
- `GET /metrics`

## Folder Structure

Use a structure close to:

```text
.
├── AGENT.md
├── README.md
├── docker-compose.yml
├── .env.example
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   ├── services/
│   ├── redis/
│   ├── models/
│   └── utils/
├── worker/
│   ├── main.py
│   └── processors/
├── dashboard/
├── tests/
└── docs/
```

## Implementation Order

Follow this exact sequence unless the user asks to change priorities.

### Phase 1: Foundation

- initialize the project
- configure FastAPI
- add Docker Compose with Redis
- create app config and environment loading
- create Redis connection module
- add health check endpoint
- add README with setup instructions

### Phase 2: Job Queue MVP

- create job submission endpoint
- persist jobs in Redis
- build one worker that processes jobs
- expose job status endpoint
- add basic tests for enqueue and status transitions

### Phase 3: Real-Time Updates

- emit job lifecycle events
- surface those events to the dashboard or SSE endpoint
- show queue depth and recent job events

### Phase 4: Rate Limiting

- protect selected endpoints
- implement fixed-window limiter
- add tests for allowed and blocked requests

### Phase 5: Cache Layer

- implement expensive endpoint
- cache responses with TTL
- track hit and miss metrics
- add invalidation endpoint

### Phase 6: Sessions

- create session create/read/delete flows
- add session expiration behavior
- test TTL-based expiry

### Phase 7: Leaderboard and Activity Feed

- add sorted-set leaderboard
- add recent activity feed
- expose both via API and dashboard

### Phase 8: Reliability

- retries with backoff
- dead-letter strategy for failed jobs
- worker locking or ownership protection
- structured logging
- better error handling

### Phase 9: Polish

- cleaner dashboard
- docs for Redis patterns used
- architecture diagram
- developer scripts
- final integration tests

## Development Rules For The Agent

The agent must behave as a pragmatic senior engineer and teacher.

### General Rules

- always explain what feature is being built and which Redis concept it teaches
- prefer small, reviewable increments
- keep the project runnable at every stage
- do not add unnecessary complexity early
- write clean code with clear names
- document every Redis key pattern in one place

### Redis Key Naming Rules

Use consistent key names such as:

- `job:{job_id}`
- `queue:jobs:pending`
- `queue:jobs:processing`
- `session:{session_id}`
- `rate_limit:{route}:{client_id}`
- `cache:{resource}:{id}`
- `leaderboard:users`
- `events:activity`
- `lock:job:{job_id}`

Document each key in `docs/redis-keys.md`.

### Engineering Rules

- keep business logic out of route handlers
- create a service layer for Redis operations
- wrap Redis access behind small reusable helpers
- use typed request and response models
- add tests for each feature before calling it done
- prefer configuration from env vars
- log meaningful state transitions
- follow SOLID principles where they improve clarity, without adding abstractions prematurely
- keep functions focused and modules cohesive
- validate all input at the API boundary
- never hardcode secrets or environment-specific values
- use UTC timestamps and structured, machine-readable logs
- handle expected failures explicitly and return useful API errors
- pin dependency versions and keep dependencies minimal

### Agent Ownership Rules

- perform required setup, file creation, dependency installation, migrations, and verification yourself
- do not ask the user to manually edit generated project files
- ask before actions that need credentials, publish externally, cost money, or destroy data
- inspect existing code before editing and preserve unrelated user changes
- run formatting, linting, and tests before declaring a feature complete
- if a tool is unavailable locally, provide and verify a Docker-based path where practical
- leave the repository in a runnable state after every completed phase
- report blockers honestly and include the exact command or permission needed to continue

### Feature Delivery Process

For every feature, follow this sequence:

1. restate the user-visible behavior and acceptance criteria
2. inspect the affected architecture and Redis key contracts
3. implement the smallest end-to-end vertical slice
4. add or update automated tests, including failure cases
5. run formatter, linter, tests, and a startup smoke check
6. update README and Redis key documentation
7. summarize the implementation, verification, and next logical feature

### Testing Rules

For each completed feature:

- add happy-path tests
- add failure-path tests
- test Redis state changes where meaningful
- test expiration behavior for TTL-based features

### Documentation Rules

After each major feature:

- update `README.md`
- update `docs/redis-keys.md`
- add a short explanation of the Redis concept used

## Non-Goals

Do not turn this into:

- a huge microservices system
- a complex auth product
- a full enterprise dashboard
- an over-engineered event platform

This is a learning-first project with real engineering discipline.

## Definition Of Done

The project is complete when:

- all core Redis features above are implemented
- the app runs locally with Docker Compose
- a worker can process jobs end-to-end
- rate limiting works
- caching works
- sessions expire correctly
- leaderboard updates correctly
- activity feed is visible
- tests pass
- README explains setup, architecture, and Redis concepts

## Implementation Status

- Phase 1: complete - foundation and Docker Compose
- Phase 2: complete - Redis job queue MVP
- Phase 3: complete - durable events and SSE
- Phase 4: complete - fixed and sliding-window rate limiting
- Phase 5: complete - response cache and invalidation
- Phase 6: complete - expiring session store
- Phase 7: complete - leaderboard and activity feed
- Phase 8: complete - retries, dead letters, and worker reliability
- Phase 9: complete - dashboard, CI, architecture docs, scripts, and integration tests

## What The Agent Should Do In Every Session

At the start of each work session:

1. inspect current project state
2. identify the next unfinished phase
3. explain the Redis concept being practiced
4. implement the smallest complete slice
5. run tests or verification
6. summarize what changed and what comes next

## First Task For The Agent

Start by building Phase 1 and Phase 2 only:

- scaffold FastAPI project
- add Docker Compose with Redis
- implement Redis connection module
- create `POST /jobs`
- create `GET /jobs/{job_id}`
- implement a basic worker
- process one demo job type end-to-end
- add README setup steps
- add initial tests

Do not start rate limiting, caching, sessions, or leaderboard until the queue MVP works cleanly.

## How To Collaborate With The User

The user is learning agentic development and Redis. The agent should:

- explain tradeoffs simply
- avoid giant rewrites without discussion
- propose the next 2 or 3 sensible steps
- keep the project educational, not just functional
- point out which parts are beginner-friendly and which are more advanced

## Recommended Repo Names

Pick one of these:

- `redisops-playground`
- `redis-lab`
- `redis-patterns-workshop`
- `redis-queue-and-cache-lab`
- `learn-redis-by-building`

## Final Recommendation

Use `redisops-playground`.

It sounds practical, flexible, and strong enough for both learning and portfolio use.
