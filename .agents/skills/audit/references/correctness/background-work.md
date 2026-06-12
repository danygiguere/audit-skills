# Background work

## Invariant

Every job has bounded retries with backoff, a dead-letter destination for
permanent failures, and timeouts on the work it performs — and its handler
tolerates duplicate and out-of-order delivery, because the queue guarantees
neither exactly-once nor ordering.

## Does not apply when

- The job is a pure, cheap, idempotent computation whose loss or repetition
  is harmless (cache warming, metrics rollup that recomputes from source).

## Why it happens

Queues are tested with one worker and a healthy network, where delivery
looks exactly-once and ordered. Retry policy is a framework default nobody
reads until a poison message has been crashing the worker for hours. Jobs
get enqueued with a snapshot of the data because passing the whole object is
convenient — and the snapshot is stale by the time the job runs after a
retry delay.

## Detection smells

- A job with no retry limit, or retries with no backoff — a permanently
  failing message retries forever or hammers a downstream dependency.
- No dead-letter path: a message that always throws is either dropped
  silently or redelivered indefinitely, blocking the queue.
- The job payload carries full entity state (user record, order body)
  instead of an ID — the job acts on data that changed between enqueue and
  execution, or between retries.
- An HTTP call, database query, or lock acquisition inside a job with no
  timeout — one hung dependency stalls the worker pool.
- Handler logic that breaks if the same message arrives twice (increments,
  plain INSERTs, "send email then mark sent" ordered wrong).
- Logic that assumes job B runs after job A because it was enqueued later —
  ordering across workers is not guaranteed.
- A failed job is caught, logged, and acknowledged as success, so the retry
  machinery never sees the failure.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the policy usually lives                                                                                                                                    |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `retry_on`/`discard_on` in ActiveJob; Sidekiq `sidekiq_options retry:`, dead set                                                                                  |
| Laravel      | `$tries`, `$backoff`, `retryUntil()`, `failed()` method; `failed_jobs` table                                                                                      |
| Django       | Celery `max_retries`, `retry_backoff`, `acks_late`, dead-letter queues                                                                                            |
| Spring       | `@Retryable`/listener retry config; DLQ on RabbitMQ/Kafka error topics                                                                                            |
| Node/Express | BullMQ `attempts`/`backoff`, failed queue; SQS redrive policy + DLQ                                                                                               |
| Vapor        | Queues package: `maxRetryCount`, delayed retries; failure hooks via `JobEventDelegate` — no built-in dead-letter queue                                            |
| .NET         | `BackgroundService` has no built-in retries — an unhandled exception in `ExecuteAsync` silently stops the worker; Hangfire/Quartz for retries and poison handling |
| Go           | worker goroutines + a queue lib (asynq has retries and DLQ); `context.WithTimeout` on every external call; errgroup for propagation                               |

## Example

Vulnerable shape:

```text
job sync_subscription(user_snapshot):        # full state, frozen at enqueue
    result = billing_api.fetch(user_snapshot.plan)   # no timeout
    db.subscriptions.insert(user_snapshot.id, result) # duplicate on redelivery
    # no retry bound, no dead-letter: a bad payload loops forever
```

Fixed shape — ID-only payload, re-fetch at run time, bounded work, duplicate-
safe write:

```text
job sync_subscription(user_id):              # ID only; re-fetch fresh state
    retries: max 5, exponential backoff, then dead-letter
    user = db.users.find(user_id)
    if user is null: discard                 # entity gone -> not an error
    result = billing_api.fetch(user.plan, timeout = 10s)
    db.subscriptions.upsert(key = user.id, result)   # redelivery is a no-op
```

## Severity guidance

- **High** — duplicate or stale-payload execution corrupts authoritative
  data (double effects, old state overwriting new), or a poison message
  blocks the queue so other work stops processing.
- **Medium** — unbounded or immediate retries that degrade a downstream
  dependency; jobs lost without a dead-letter trace, requiring manual
  replay.
- **Low** — missing timeouts or bounds on jobs whose failure is visible and
  whose work is idempotent and low-volume.

## Remediation

See `../remediation/async-patterns.md` — retry/backoff policy, dead-letter
queues, ID-only payloads with re-fetch, and duplicate-tolerant handlers.
