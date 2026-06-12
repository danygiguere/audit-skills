# State management

## Invariant

No check-then-act on shared mutable state unless something atomic backs it:
a database constraint, an atomic primitive (single-statement increment,
compare-and-swap), or a lock held across both the check and the act. A read
followed by a dependent write is a race unless the store enforces the rule.

## Does not apply when

- The state is request-local or owned by a single writer (one process, one
  thread, no concurrent mutation path).
- The check is advisory only — a friendlier error message — and a
  constraint or atomic operation underneath still enforces correctness.

## Why it happens

Check-then-act reads as obviously correct: "if no row exists, insert it."
The interleaving where two requests both pass the check exists only under
concurrency, so it never fires in development or single-threaded tests.
Application code cannot serialize concurrent requests by itself — only the
shared store can — but the check *looks* like enforcement, so the constraint
or lock is never added.

## Detection smells

- Query for existence, then INSERT if absent — two concurrent requests both
  see "absent" and both insert; no unique constraint exists as backstop.
- Read a value, modify it in application memory, write it back
  (`x = read(); write(x + 1)`) instead of a single atomic
  increment/decrement at the store.
- A balance, quota, stock, or rate check (`if remaining >= amount`) followed
  by a deduction in a separate statement, with no lock or conditional update
  — concurrent requests each pass the check and overspend.
- Two requests load the same row, both edit, both save — last write wins
  silently; no version column or row lock detects the conflict.
- A value read from a cache drives a decision, then the cache is written
  back from possibly-stale data, re-publishing old state.
- A uniqueness or limit rule enforced only in application code, with
  nothing in the schema that would reject the racing duplicate.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the atomic backstop usually lives                                                                                                              |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | unique index + rescue `RecordNotUnique`; `increment_counter`; `lock` (FOR UPDATE); `lock_version`                                                    |
| Laravel      | unique index; `increment()`; `lockForUpdate()`; atomic cache `lock()`                                                                                |
| Django       | unique constraint + `IntegrityError`; `F()` expressions; `select_for_update()`                                                                       |
| Spring       | unique constraint; `@Version` optimistic locking; `@Lock(PESSIMISTIC_WRITE)`                                                                         |
| Node/Express | unique index + `ON CONFLICT`; `UPDATE ... SET x = x + 1 WHERE ...`; `SELECT ... FOR UPDATE`; Redis `INCR`/`SETNX`                                    |
| Vapor        | unique constraints in migrations as the backstop; atomic updates via SQLKit; version-field optimistic locking is manual; actors for in-process state |
| .NET         | `[Timestamp]` rowversion + `DbUpdateConcurrencyException` for optimistic locking; `Interlocked` for counters; unique constraints in migrations       |
| Go           | `sync.Mutex`/`atomic` in-process; cross-goroutine check-then-act found by `go test -race`; DB constraints as the backstop                            |

## Example

Vulnerable shape:

```text
handler redeem_coupon(request):
    uses = db.redemptions.count(coupon = request.coupon)   # check
    if uses >= coupon.limit: respond 409
    db.redemptions.insert(coupon, request.principal)       # act — racy gap
```

Fixed shape — the store enforces the rule in one atomic statement; the
application check, if kept, is only for the error message:

```text
handler redeem_coupon(request):
    claimed = db.execute(
        "UPDATE coupons SET uses = uses + 1
         WHERE id = ? AND uses < limit")                   # check and act, atomic
    if claimed == 0: respond 409
    db.redemptions.insert(coupon, request.principal)       # unique(coupon, user) backstop
```

Choose optimistic locking (version column, retry on conflict) when
contention is rare; pessimistic locking (row lock across check and act) when
contention is common or retries are expensive.

## Severity guidance

- **High** — the race lets invariants over money or scarce resources break:
  overspent balances, oversold stock, quota or limit bypass, duplicate
  rows where uniqueness is a business rule.
- **Medium** — lost updates between concurrent editors, drifting counters,
  stale cache values driving decisions — wrong data, recoverable from
  source.
- **Low** — races on advisory or display-only state that the next read
  recomputes correctly.
- State reachable by unauthenticated or high-volume traffic rates one level
  higher: the race is triggerable on demand, not just by accident.

## Remediation

See `../remediation/async-patterns.md` — unique constraints as backstop,
atomic store operations, conditional updates, and optimistic vs pessimistic
locking.
