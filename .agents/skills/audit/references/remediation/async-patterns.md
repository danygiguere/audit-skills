# Atomicity, idempotency & concurrency fixes (remediation patterns)

## Scope

Fix patterns for confirmed findings from `../correctness/atomicity.md`,
`../correctness/idempotency.md`, `../correctness/background-work.md`, and
`../correctness/state-management.md` — multi-write operations that can fail
halfway, handlers that misbehave when run twice, unbounded or unsafe retries,
and check-then-act races on shared state. Each pattern makes one failure mode
impossible rather than unlikely.

## Patterns

### 1. Transaction boundary around multi-write operations

**When to use:** two or more writes must succeed together (order + line items,
debit + credit) and currently run as separate statements.

```text
with db.transaction():
    order = db.orders.create(...)
    db.line_items.create_all(order, items)
    db.inventory.decrement(items)
# all committed or all rolled back; partial state never survives
```

Trade-off: keep the boundary tight — no network calls or slow work inside, or
lock contention and held connections follow.

### 2. After-commit hooks / transactional outbox for side effects

**When to use:** a side effect (email, queue publish, external API call) is
fired from inside a transaction — it runs even if the transaction rolls back,
or the commit succeeds and the publish is lost.

```text
with db.transaction():
    order = db.orders.create(...)
    db.outbox.insert(event = "order_created", payload = order.id)  # same txn
# separate relay reads outbox rows, publishes, marks them sent
# (lighter variant: framework after-commit hook to enqueue the job)
```

Trade-off: outbox guarantees at-least-once delivery but adds a relay process;
after-commit hooks are simpler but lose the event if the enqueue itself fails.

### 3. Idempotency key store

**When to use:** a handler with side effects can be invoked twice — webhooks,
payment submissions, client retries. Key on the caller-supplied idempotency
key or the event's external ID.

```text
handler process(request):
    key = request.idempotency_key or request.event_id
    prior = db.processed.insert_if_absent(key)      # atomic check-and-record
    if prior exists: respond prior.stored_response  # replay, do not re-execute
    result = do_side_effects(request)
    db.processed.update(key, stored_response = result)
    respond result
```

Trade-off: needs a retention policy for the key store, and the record must be
written atomically with (or before) the side effect, never after.

### 4. Unique constraint + UPSERT as race-proof dedupe

**When to use:** "create if not exists" logic implemented as a read followed by
a write — two concurrent requests both pass the read and both insert.

```text
# before: if not db.exists(email): db.insert(email)   # race window
# after: the database is the arbiter
db.upsert(table, conflict_key = email, ...)            # or insert + catch unique violation
```

Trade-off: requires the unique constraint to actually exist in the schema;
application-level checks alone never close the window.

### 5. Atomic update / optimistic locking instead of read-modify-write

**When to use:** counters, balances, or status fields updated by reading a
value, computing in memory, and writing back — concurrent writers lose updates.

```text
# counters: push the arithmetic into the store
db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?", ...)

# multi-field state: version column, retry on conflict
rows = db.update_where(id = id, version = read_version,
                       set = {..., version: read_version + 1})
if rows == 0: reload and retry, or fail
```

Trade-off: optimistic locking needs a bounded retry-on-conflict loop in
callers; pessimistic `SELECT FOR UPDATE` is simpler but serializes throughput.

### 6. Bounded retry with backoff + dead-letter queue

**When to use:** jobs or consumers that retry forever, retry instantly, or
silently drop failures.

```text
job handler(payload):
    try: process(payload)        # process must be idempotent (patterns 3/4)
    catch e:
        if attempt < MAX_ATTEMPTS: retry after backoff(attempt) + jitter
        else: dead_letter.push(payload, error = e); alert
```

Trade-off: dead-lettered work needs an owner and a replay path, or the DLQ
becomes a silent data graveyard.

## Ecosystem glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Native form of these patterns                                                                                                                                                                |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `ActiveRecord::Base.transaction`; `after_commit`; `upsert`/`create_or_find_by`; `lock_version` optimistic locking; Sidekiq retries + dead set                                                |
| Laravel      | `DB::transaction()`; `DB::afterCommit` / `dispatch()->afterCommit()`; `upsert()`; `lockForUpdate()`; queue `tries`/`backoff` + `failed_jobs`                                                 |
| Django       | `transaction.atomic()`; `transaction.on_commit()`; `update_or_create`/`bulk_create(ignore_conflicts)`; `F()` expressions + `select_for_update()`; Celery `max_retries` + dead-letter routing |
| Spring       | `@Transactional`; `TransactionSynchronization.afterCommit` / outbox libs; `ON CONFLICT` via JDBC/JPA; `@Version` optimistic locking; Spring Retry + AMQP DLQ                                 |
| Node/Express | `knex.transaction()`/Prisma `$transaction`; outbox table + relay; `ON CONFLICT DO UPDATE`; `UPDATE ... WHERE version = ?`; BullMQ `attempts`/`backoff` + failed queue                        |
| Vapor        | `req.db.transaction`; `.unique(on:)` + constraint-violation catch; Queues `maxRetryCount`/delays; the outbox is hand-rolled                                                                  |
| .NET         | `Database.BeginTransaction`; unique index + `DbUpdateException` catch; rowversion concurrency tokens; Hangfire retries; outbox via CAP or hand-rolled                                        |
| Go           | `BeginTx` + deferred rollback; unique index + `ON CONFLICT`; `SELECT ... FOR UPDATE` or atomic UPDATE; asynq retries/DLQ                                                                     |

## Applying fixes

- Make the smallest change that restores the invariant: wrap the existing
  writes in a transaction or swap the read-then-write for one atomic
  statement; do not rearchitect the job pipeline for one handler.
- Match surrounding code style — use the transaction and queue idioms the
  codebase already has, not a new library.
- Add or extend a test demonstrating the fix: run the handler twice (or fail
  it mid-sequence) and assert single-execution outcome / no partial state.
- Never mix the fix with unrelated refactoring; concurrency fixes are hard
  enough to review on their own.
