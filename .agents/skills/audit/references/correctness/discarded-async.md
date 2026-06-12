# Discarded Async Work (fire-and-forget)

## Invariant

Every async producer the code creates — promise, future, task, reactive
publisher — is either awaited, returned, composed into a pipeline, or
*deliberately* detached with error handling and a comment saying so. A
discarded producer is a bug with two flavors, set by the ecosystem's
semantics: **lazy/cold** producers (Reactor, Rust futures) silently never
execute; **eager** producers (JS promises, .NET tasks) run, but their
errors, ordering, and ambient context are lost.

## Does not apply when

- The code is synchronous, or the concurrency is eager and explicit (Go
  goroutines: `go f()` runs — the analogous smell there is an ignored error
  channel or a missing `wg.Wait()`).
- The detachment is intentional, rare, commented, and error-handled
  (best-effort metrics, cache warm-ups).

## Why it happens

The sync and async versions of a call look identical at the call site, so a
statement-position call reads as "done" when it is only "described." In lazy
ecosystems nothing fails loudly — the write simply doesn't happen, and tests
that assert on the response rather than the side effect stay green. In eager
ecosystems the happy path works, so the missing error handling is invisible
until the first failure. Sync-to-async refactors leave old
statement-position calls behind.

## Detection smells

- A call returning a promise/future/publisher used as a bare statement: not
  `return`ed, not assigned, not awaited, no continuation (`.then`,
  `.flatMap`, composition into the returned chain).
- In lazy ecosystems: repository writes or service calls (`save`, `delete`,
  `update`) standing on their own line — the operation never runs.
- A bare subscribe/spawn that runs the work but discards failures:
  `.subscribe()` with no error consumer, an unstructured task with no error
  handling, a created task with no kept reference or done-callback.
- An async function that creates a producer and reaches its end without a
  terminal operation on it.
- Side-effect producers detached from the response path — the handler can
  return success while the detached work fails.
- Fire-and-forget that needs ambient context it no longer has: transaction,
  correlation ID, request scope (the work outlives or escapes them).
- Tests that assert only on the returned value of code with async side
  effects — a discarded producer is invisible to them.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name
the concept in common ecosystems.*

| Ecosystem    | Where the discipline usually lives                                                                                                                                             |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | largely N/A (synchronous) — the closest analog is `load_async` queries whose results are never read                                                                            |
| Laravel      | largely N/A (sync PHP); under Octane/amphp, promises must be awaited; queued `dispatch()` is eager and fine                                                                    |
| Django       | asyncio's "coroutine was never awaited" warning; `asyncio.create_task` with no kept reference (GC may drop it) or done-callback                                                |
| Spring       | Reactor `Mono`/`Flux` are cold — nothing happens until subscribe; statement-position `repository.save(...)`; bare `.subscribe()` loses errors and reactive context (tx, trace) |
| Node/Express | floating promises — `@typescript-eslint/no-floating-promises`; unhandled rejections crash modern Node; `void promise` as the explicit opt-out                                  |
| Vapor        | unstructured `Task { }` swallows thrown errors unless awaited; prefer structured concurrency (`async let`, task groups)                                                        |
| .NET         | unawaited `Task` → compiler warning CS4014; exceptions go unobserved; `async void` is the related smell                                                                        |
| Go           | does not apply as such — goroutines are eager and explicit; the analog is ignoring an error channel or forgetting `wg.Wait()`                                                  |

## Example

Vulnerable shape (lazy semantics — the severe flavor):

```text
async handler complete_order(request):
    order = await orders.find(request.params.id)
    order.status = "complete"
    await orders.save(order)
    audit.record(order)        # returns a cold publisher: never subscribed,
    return order               # never awaited -> the audit row is NEVER written
```

Fixed shape — awaited, or composed into the returned pipeline:

```text
async handler complete_order(request):
    order = await orders.find(request.params.id)
    order.status = "complete"
    await orders.save(order)
    await audit.record(order)
    return order
```

## Severity guidance

- **High** — a discarded *cold* producer performing a write: the operation
  silently never happens. Data loss with green tests.
- **Medium** — floating *eager* producers: the work runs but errors,
  ordering, and context are lost; bare subscribe/spawn with no error
  consumer.
- **Low** — best-effort work that is legitimately detached but lacks the
  comment and error handling that make the intent explicit.
- Raise one level when the discarded work is the only record of an action —
  audit logs, outbox inserts (see also `atomicity.md`).
