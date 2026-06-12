# Exception Handling

## Invariant

Every error is either handled meaningfully or propagated — never silently
swallowed. A catch is as narrow as the failure it knows how to handle, sits
at a boundary that can actually respond (retry, translate, report), and
preserves the original cause when it rethrows. Failure paths release
everything the success path acquired.

## Does not apply when

- The language signals errors through return values instead of exceptions
  (Go, Rust). The invariants still map — an ignored error return is an empty
  catch, a lost cause is an unwrapped error — but the smells below are
  phrased for exception-based code.

## Why it happens

Catch blocks get added to silence crashes during development and never
revisited. Blanket catch-alls are wrapped around large blocks "to be safe,"
and from then on hide every unrelated bug that occurs inside. Exceptions get
raised for expected outcomes (lookup miss, invalid input), forcing callers
into catch-based control flow. And rethrowing as a new exception without
chaining feels equivalent to propagation — until production, where the
original stack trace is gone.

## Detection smells

- A catch block that is empty, only logs at debug level, or returns a
  default (`null`, `false`, empty list) — the caller proceeds as if the
  operation succeeded.
- A catch-all (the base exception type) around a large block, giving one
  response to failures that need different handling — a parse error and a
  database outage treated identically.
- A catch that rethrows a new exception without attaching the original as
  its cause — the stack trace dies at the boundary.
- Exceptions as control flow for expected outcomes: a raise that the
  immediate caller always catches as a normal branch.
- Resources acquired outside the protected block, or released only on the
  success path — a failure leaks the connection, handle, or lock.
- The same error caught, logged, and rethrown at every layer on its way up —
  one failure, five log entries, duplicate alerts. Handle once, at the
  boundary (see `../operability/observability.md`).
- Errors thrown inside async callbacks, promise chains, or event handlers
  with no rejection handler attached — they vanish or kill the process.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the discipline usually lives                                                                                                                |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `rescue StandardError` not `rescue Exception`; `ensure`; `rescue_from` at controller boundary                                                     |
| Laravel      | narrow `catch` types; `finally`; the exception `Handler` / `report()` as the boundary                                                             |
| Django       | `except Specific` not bare `except`; `finally` / context managers; DRF exception handlers                                                         |
| Spring       | `@ControllerAdvice` / `@ExceptionHandler` boundary; try-with-resources; constructor cause chaining                                                |
| Node/Express | `try/await/catch` + error middleware via `next(err)`; `finally`; `unhandledRejection` hooks                                                       |
| Vapor        | narrow `do/catch`; `try?` is the silent swallow; `Abort(.notFound)`/`AbortError` map errors to statuses; `ErrorMiddleware` is the boundary        |
| .NET         | `UseExceptionHandler` + `ProblemDetails` boundary; `throw;` not `throw ex;` (keeps the stack); broad `catch (Exception)` mid-stack is the smell   |
| Go           | errors are values: empty `if err != nil {}` or `_ =` discard is the swallow; wrap with `fmt.Errorf("...: %w", err)`; map to status at the handler |

## Example

Vulnerable shape:

```text
handler import_orders(file):
    conn = storage.open(file)               # acquired outside the try
    try:
        for row in conn.rows():
            orders.insert(parse(row))
    catch any:
        return []                           # parse bug, DB outage, and bad
                                            # file all become "no orders"
```

Fixed shape — narrow catch, chained cause, guaranteed release; everything
the handler can't meaningfully handle propagates to the boundary:

```text
handler import_orders(file):
    conn = storage.open(file)
    try:
        for row in conn.rows():
            orders.insert(parse(row))
    catch ParseError as e:
        raise ImportFailed("invalid row in " + file.name, cause = e)
    finally:
        conn.close()
    # infrastructure errors propagate; the boundary handler logs once
```

## Error-to-status mapping

At HTTP boundaries, the error must translate to the status the condition
actually means — clients, caches, and monitors all branch on it:

- An expected lookup miss → **404**, not a 500 from an exception nobody
  caught.
- No/invalid credentials → **401**; valid credentials but no permission →
  **403**. The two are routinely conflated.
- Resource exists but belongs to another principal → **404, not 403** — a
  403 confirms the resource exists (see `../access-data-security/idor.md`).
- Validation failure → **400/422** with field-level detail — never a 500,
  and never a **200 with an error payload** (the worst case: clients are
  forced to parse body text to detect failure).
- Duplicate submission or optimistic-lock conflict → **409**.
- A boundary handler that maps *every* exception to one status erases all of
  these distinctions — same smell as the blanket catch, one level up.

## Severity guidance

- **High** — a swallowed error lets the caller proceed as if a write,
  payment, or delivery succeeded; failure is reported as success.
- **Medium** — blanket catches masking unrelated bugs; lost causes that make
  production failures undiagnosable; failure paths leaking connections,
  handles, or locks.
- **Low** — log-and-rethrow duplication; exceptions as control flow with
  purely local impact.
- Rate one level higher in background jobs and webhook handlers, where
  nobody is watching the response (silent failure — see
  `../operability/observability.md`). Partial state left behind by the
  failure itself is an `atomicity.md` finding; report it there.
