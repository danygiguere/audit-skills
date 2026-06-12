# Atomicity

## Invariant

Writes that must succeed together run inside one transaction, or each step
has explicit compensation that runs on failure. External side effects —
email, HTTP calls, queue publishes — happen after commit, never inside the
transaction. No failure mode may leave partial state behind.

## Does not apply when

- The writes are genuinely independent: any subset succeeding is a valid
  final state on its own.
- The store is a single document/row updated in one statement — the database
  already makes that atomic.

## Why it happens

Each write looks correct in isolation; the missing transaction is invisible
until a mid-sequence failure occurs in production. Side effects creep into
transactional code because "send the email when the order saves" reads
naturally as one block. Cross-request flows (wizard steps, draft-then-
publish) cannot use a database transaction at all, and developers forget
that something must still reconcile the halves.

## Detection smells

- Two or more INSERT/UPDATE/DELETE statements against related tables in one
  handler with no transaction boundary around them.
- A create-parent-then-create-children sequence where a child failure leaves
  the parent row orphaned.
- An email send, HTTP call, or queue publish between `begin` and `commit` —
  it fires even if the transaction rolls back, or stalls the transaction
  while holding locks.
- A write to the database plus a write to an external system (payment
  gateway, search index, file store) with no compensation or outbox for the
  case where the second one fails.
- Read-modify-write that spans requests: load in one handler, save in
  another, with nothing detecting that the row changed in between.
- `try/catch` around a multi-write sequence that logs the error and
  continues, leaving earlier writes in place.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the boundary usually lives                                                                                                               |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `ActiveRecord::Base.transaction do ... end`; `after_commit` callbacks                                                                          |
| Laravel      | `DB::transaction(fn () => ...)`; `afterCommit` on jobs/mail/notifications                                                                      |
| Django       | `transaction.atomic()`; `transaction.on_commit(callback)`                                                                                      |
| Spring       | `@Transactional`; `TransactionSynchronization.afterCommit`                                                                                     |
| Node/Express | client/ORM transaction APIs (`sequelize.transaction`, knex `trx`); manual after-commit hooks                                                   |
| Vapor        | `req.db.transaction { db in ... }` (all writes through the inner `db`); side effects after the closure returns — no built-in after-commit hook |
| .NET         | one `SaveChanges` call is atomic; multi-step via `Database.BeginTransaction()`/`TransactionScope`; side effects after commit                   |
| Go           | `db.BeginTx` + `defer tx.Rollback()`, commit last; sqlx/GORM `Transaction(func(tx) {...})`; side effects after commit                          |

## Example

Vulnerable shape:

```text
handler place_order(request):
    order = db.orders.insert(...)          # succeeds
    db.payments.insert(order.id, ...)      # may fail -> orphaned order
    email.send_confirmation(order)         # fires even if payment failed
```

Fixed shape — one transaction around the writes, side effects deferred to
after commit:

```text
handler place_order(request):
    order = db.transaction:
        order = db.orders.insert(...)
        db.payments.insert(order.id, ...)  # failure rolls back both
        return order
    on_commit: email.send_confirmation(order)   # only if writes persisted
```

## Severity guidance

- **High** — partial state corrupts money, inventory, or authorization data
  (order without payment, role granted without audit row), or external side
  effects fire for state that was rolled back.
- **Medium** — orphaned rows or inconsistent denormalized data that a human
  or batch job must reconcile; lost updates from cross-request
  read-modify-write.
- **Low** — partial state is self-healing (next run repairs it) or limited
  to non-authoritative caches.

## Remediation

See `../remediation/async-patterns.md` — transaction boundaries, after-commit
hooks, outbox pattern, and compensation steps.
