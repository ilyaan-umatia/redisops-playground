# Redis Patterns Practiced

| Pattern | Redis structure | Project example |
| --- | --- | --- |
| Durable object state | Hash | Jobs and sessions |
| FIFO work queue | List | Pending and processing jobs |
| Delayed scheduling | Sorted set | Retry timestamps |
| Ranking | Sorted set | Completed jobs per user |
| Durable event log | Stream | Job lifecycle and activity |
| Cache-aside | Expiring string | Analytics summary |
| Fixed-window limit | Expiring counter | Demo route protection |
| Sliding-window limit | Sorted set + transaction | Precise demo limiter |
| Ownership lease | Expiring lock | Per-job worker lock |
| Batched atomic update | Pipeline transaction | Job state plus events |

See [redis-keys.md](redis-keys.md) for the exact key contracts and retention rules.
