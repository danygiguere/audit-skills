# Observability

## Invariant

Every failure path logs with context, and every new endpoint or job emits
enough signal for its failures to be visible in production. If this code
breaks at 3 a.m., someone must be able to (1) notice and (2) find the
failing request or job from the logs alone — without redeploying with extra
logging first.

## Does not apply when

- The error is expected control flow handled completely at that site
  (e.g., a cache miss falling through to the source) — logging it would be
  noise, not signal.

## Why it happens

Error handling is written for the happy-path reviewer: catching the
exception makes the red test go green, and whether anything useful happens
inside the catch block is invisible. Logs get written for the developer's
local console, not for the operator grepping production — so they say
"payment failed" without saying *which* payment. Background jobs have no
user staring at a spinner, so their failures have no natural witness.

## Detection smells

- A catch/rescue block that is empty, only returns a default, or swallows
  the error and continues — the failure leaves no trace anywhere.
- A log line describing a failure with no identifiers: no request ID,
  entity ID, user/tenant ID, or correlation ID that lets an operator find
  the affected record or trace the request across services.
- An error logged at debug/info level, or logged without the exception and
  stack trace attached — present in the code, invisible in production.
- A new endpoint or background job added with no failure-path logging or
  metric at all; only an operator's absence-of-data reveals it broke.
- A job or queue consumer whose failure path acks/completes the message
  anyway — it fails silently and the work is lost without signal.
- Errors that are logged but feed no metric, alert, or error tracker —
  visible only to someone already reading the logs for another reason.
- Log statements that dump whole request bodies, models, tokens, or PII as
  "context" — this trades a data-exposure finding for an observability one.
  Log identifiers, not payloads.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the signal usually comes from                                                                                           |
|--------------|-------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Rails.logger` with tagged logging (request ID); Sentry/Honeybadger; ActiveJob `retry_on`/`discard_on` hooks                  |
| Laravel      | `Log::error()` with context array; `report()`; Horizon failed-jobs table; Telescope                                           |
| Django       | `logging` with request ID middleware; Sentry SDK; Celery task failure signals                                                 |
| Spring       | SLF4J + MDC for correlation IDs; Micrometer metrics; `@ControllerAdvice` handlers                                             |
| Node/Express | pino/winston child loggers with request ID; error-handling middleware; queue `failed` event handlers                          |
| Vapor        | `req.logger` (SwiftLog) with metadata; SwiftMetrics + Prometheus exporter; request-ID middleware adds correlation metadata    |
| .NET         | `ILogger<T>` structured logging with scopes; `LogError(ex, ...)` not just `ex.Message`; OpenTelemetry/Activity; health checks |
| Go           | `log/slog` with context fields (request ID); OpenTelemetry propagation via context; prometheus client                         |

## Example

Vulnerable shape:

```text
handler charge(request):
    try:
        gateway.charge(request.body.amount)
    catch error:
        return respond 500            # no log, no ID, no metric

job sync_inventory(item_id):
    result = api.fetch(item_id)
    if result.failed: return          # silent; job "succeeds"
```

Fixed shape — failure is findable and countable:

```text
handler charge(request):
    try:
        gateway.charge(request.body.amount)
    catch error:
        log.error("charge failed",
                  error      = error,            # exception + stack
                  request_id = request.id,
                  invoice_id = request.params.invoice_id)  # IDs, not payloads
        metrics.increment("charge.failure")      # feeds an alert
        return respond 500

job sync_inventory(item_id):
    result = api.fetch(item_id)
    if result.failed:
        log.error("inventory sync failed", item_id = item_id,
                  status = result.status)
        raise                                    # let retry/DLQ machinery see it
```

## Severity guidance

- **High** — failures in money-moving, data-mutating, or security-relevant
  paths leave no signal; in production this means silent data loss or
  corruption discovered days later by users, with no log trail to scope the
  damage.
- **Medium** — failures are logged but unfindable (no identifiers) or
  unalertable (no metric/tracker path); incidents take hours longer to
  detect and diagnose.
- **Low** — noisy or context-poor logging on non-critical paths.
- Sensitive data in logs is a **data-exposure** finding (see
  `../access-data-security/data-exposure.md`) and rates on that scale, not
  this one.

## Remediation

See `../remediation/observability-patterns.md` — structured logging with
correlation IDs, error-to-metric wiring, and job failure handling.
