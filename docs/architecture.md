# Architecture

```mermaid
flowchart LR
    Browser["Dashboard / API client"] --> API["FastAPI"]
    API --> Hashes["Job and session hashes"]
    API --> Pending["Pending job list"]
    API --> Cache["Response cache"]
    API --> Limits["Counters and sorted sets"]
    Worker["Background worker"] --> Pending
    Worker --> Retry["Delayed retry sorted set"]
    Worker --> DLQ["Dead-letter list"]
    Worker --> Hashes
    Worker --> Board["User leaderboard"]
    API --> Streams["Lifecycle and activity streams"]
    Worker --> Streams
    Streams --> SSE["Server-Sent Events"]
    SSE --> Browser
```

## Boundaries

- Route modules validate HTTP input and translate domain errors.
- Services own business rules and async Redis operations.
- Redis helpers define keys and event serialization.
- The worker owns blocking queue consumption and processor dispatch.
- The dashboard consumes public API contracts only; it has no direct Redis access.

## Job Lifecycle

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> processing
    processing --> completed
    processing --> retrying: transient failure
    retrying --> queued: backoff elapsed
    processing --> failed: retries exhausted
    failed --> queued: manual retry
```
