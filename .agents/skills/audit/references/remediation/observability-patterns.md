# Observability fixes (remediation patterns)

## Scope

Fix patterns for confirmed findings from `../operability/observability.md` —
failure paths that log nothing or log without context, errors swallowed in
catch blocks, new endpoints and jobs whose failures are invisible in
production, and alerts that fire on internals nobody can act on. The invariant
restored: every failure is visible, attributable, and traceable.

## Patterns

### 1. Structured logging with stable context fields

**When to use:** failure paths that log nothing, log bare messages
(`log("failed")`), or dump whole objects. Log key-value structure with a small
stable set of fields — request ID, principal ID, entity type and ID, operation
— and never payloads, secrets, or PII.

```text
catch e:
    log.error("invoice.update failed",
        request_id = ctx.request_id,
        principal  = ctx.principal_id,      # ID only, never email/name
        invoice_id = invoice.id,
        error      = e.class, message = e.message)
    raise   # or handle — but never swallow silently
```

Trade-off: field names must stay consistent across the codebase or they are
unsearchable; adopt the existing schema before inventing fields.

### 2. Correlation-ID propagation across services and jobs

**When to use:** a request fans out to other services or background jobs and
the resulting logs cannot be stitched back together.

```text
middleware: ctx.request_id = incoming_header("X-Request-Id") or new_id()
outbound http:   set header X-Request-Id = ctx.request_id
enqueue job:     payload.request_id = ctx.request_id
job handler:     bind ctx.request_id = payload.request_id   # before any logging
```

Trade-off: every boundary (HTTP client, queue producer, consumer) must
participate; one gap breaks the chain, so wire it at shared client/middleware
level, not per call site.

### 3. Per-endpoint RED metrics

**When to use:** a new endpoint or job ships with no signal — nobody can see
its rate, error ratio, or latency in production.

```text
middleware measure(request):
    start = now()
    response = next(request)
    metrics.count("http.requests", route = request.route, status = response.status)
    metrics.timing("http.duration", now() - start, route = request.route)
# rate and error ratio derive from the counter; duration from the histogram
```

Trade-off: label by route template, never by raw path or user ID —
high-cardinality labels melt the metrics store.

### 4. Error-tracker integration with deduplication context

**When to use:** exceptions are logged but never aggregated, or every
occurrence appears as a distinct issue (or thousands collapse into one).

```text
catch e:
    error_tracker.capture(e,
        fingerprint = [e.class, request.route],   # groups same bug, splits routes
        tags  = { request_id: ctx.request_id, entity_id: entity.id },
        user  = { id: ctx.principal_id })          # ID only
    respond 500 generic_error                      # tracker gets detail, client does not
```

Trade-off: fingerprints tuned too coarse hide distinct bugs, too fine flood
the tracker — default grouping first, customize only where it proves wrong.

### 5. Alerting on user-visible symptoms

**When to use:** alerts fire on internal causes (CPU, queue depth, one
exception) and either page nobody for real outages or page constantly for
non-issues. Alert on what users experience; let causes be diagnosis, not pages.

```text
alert "checkout failing":
    when error_ratio("POST /checkout") > 2% over 5m
    or    p95_duration("POST /checkout") > 3s over 10m
# cause-level signals (queue depth, retries) become dashboards, not pages
```

Trade-off: symptom alerts tell you *that* it is broken, not *why* — they only
work when patterns 1–3 exist to answer the why.

## Ecosystem glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Native form of these patterns                                                                                                                                        |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Rails.logger` with `tagged`/semantic logger, `config.log_tags = [:request_id]`; ActiveSupport::Notifications + StatsD/Prometheus exporters; Sentry/Honeybadger gems |
| Laravel      | `Log::withContext()` and Monolog processors; request ID middleware; Telescope/Horizon metrics, Prometheus exporters; Sentry/Flare SDK                                |
| Django       | `logging` dict config with JSON formatter + request-ID middleware (django-log-request-id); django-prometheus; sentry-sdk with `set_tag`/`set_user`                   |
| Spring       | SLF4J + MDC (`MDC.put("requestId", ...)`), Micrometer Tracing for propagation; Micrometer + Actuator `http.server.requests`; Sentry/ELK appenders                    |
| Node/Express | pino/winston child loggers with bound fields; AsyncLocalStorage for request-ID context; prom-client histograms in middleware; Sentry SDK with scopes                 |
| Vapor        | SwiftLog structured metadata; request-ID middleware for correlation; SwiftMetrics RED metrics with the Prometheus exporter                                           |
| .NET         | `ILogger` scopes for stable context fields; W3C trace context via Activity/OpenTelemetry; ProblemDetails for consistent error shape                                  |
| Go           | slog with context-derived fields; otel trace propagation; prometheus RED metrics per handler                                                                         |

## Applying fixes

- Make the smallest change that restores the invariant: add context to the
  existing log line or instrument the one endpoint; do not replace the
  logging stack.
- Match the surrounding code's logger, field names, and metric conventions —
  one inconsistent field name makes incidents harder, not easier.
- Add or extend a test demonstrating the fix where practical: assert the
  failure path emits a log entry or capture call with the expected fields.
- Never mix the fix with unrelated refactoring; instrumentation diffs must be
  obviously behavior-preserving.
