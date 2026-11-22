# Downstream failure

## Invariant

Every call to a remote dependency — HTTP API, RPC, database, cache, broker —
is written for the case where that dependency is slow, erroring, or down. The
call has a timeout that fits inside its caller's own deadline; retries are
bounded, backed off with jitter, and limited to idempotent operations and
retryable errors; a failed security decision denies; an optional dependency
degrades the response instead of failing it; and a failure is never mistaken
for an answer.

## Does not apply when

- The call is in-process or to a local resource (function call, local file,
  in-memory structure) — nothing remote can hang or partially fail.
- The code is a one-off script or CLI a human watches and reruns, where a
  hang or crash is visible and harmless.
- The retry policy belongs to a queue or job framework — that is
  `../correctness/background-work.md`. Report it there, not here.
- The complaint is a blocking call on an event loop — that is
  `blocking-io-async.md`. A missing timeout on any runtime, sync or async,
  is reported here, once.
- The only observation is "there is no circuit breaker". That is a possible
  fix, not a finding: report the concrete failure (pool drained, every
  request waiting a full timeout), never the missing pattern.

## Why it happens

The happy path is the only path anyone exercises: in development and tests
the dependency answers in milliseconds or is mocked to succeed. Client
libraries ship with no timeout, or one measured in minutes, and the call site
gives no hint. Retries get added to cure flakiness, without asking whether
the operation is safe to repeat or what happens when every caller retries at
once. A `catch` around a permission or rate-limit lookup returns the
convenient default so the feature "keeps working". And a nice-to-have call
(analytics, email, recommendations) is written inline with the critical one,
so its outage becomes everyone's outage.

## Detection smells

- A remote call with no explicit timeout — HTTP client, database query,
  cache command, RPC, or waiting for a pooled connection — relying on a
  library default that is infinite or minutes long.
- A timeout budget that does not add up: an inner timeout longer than the
  caller's, or attempts × per-attempt timeout exceeding the request's
  deadline. The caller has given up; the work continues and holds resources.
- The caller's deadline or cancellation signal is not passed down, so
  abandoned requests keep running downstream.
- A retry around a non-idempotent operation (create, charge, send) with no
  idempotency key — a timeout after the dependency already acted becomes a
  duplicate. See `../correctness/idempotency.md`.
- A retry that catches everything: validation errors, 4xx responses, and
  authentication failures are retried although they can never succeed.
- Retries with no attempt cap, no backoff, or no jitter — every client
  retries in step and the recovering dependency is knocked down again.
- Stacked retries: the SDK retries, the wrapper retries, and the calling
  handler or job retries, multiplying one request into dozens.
- Fail-open on a security decision: the error path of an authorization,
  rate-limit, fraud, token-revocation, or feature-entitlement check returns
  "allowed". Taking the dependency down then bypasses the control.
- An optional dependency called inline on a critical path with no isolation
  — an analytics, email, or recommendation failure fails (or, inside a
  transaction, rolls back) the order it accompanies.
- A failure treated as an answer: an error or timeout mapped to "not found",
  empty list, zero, or `false`, then acted on (a duplicate record created,
  a balance shown as 0) or cached as if it were real.
- A fallback that silently serves stale or default data — nothing logged,
  nothing in the response marking it degraded — or serves a value computed
  for a different user or tenant.
- A liveness probe that calls a dependency (database ping, downstream
  health endpoint): when the dependency fails, the orchestrator restarts
  every healthy replica. Dependency checks belong in readiness, if anywhere.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where timeouts, retries, and probes usually live                                                                                                                      |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Net::HTTP` `open_timeout`/`read_timeout` (60s defaults); Faraday `request :retry`; `statement_timeout` in `database.yml`; `rack-timeout` for the request deadline     |
| Laravel      | `Http::timeout()->connectTimeout()->retry()`; raw Guzzle defaults to no timeout; PDO/driver timeout options; `Http::pool` for isolation                               |
| Django       | `requests` has no default timeout — pass `timeout=` on every call; urllib3 `Retry`, `tenacity`; DB `OPTIONS` `connect_timeout`/`statement_timeout`                    |
| Spring       | `RestTemplate`/`RestClient` need explicit connect/read timeouts; `WebClient` `responseTimeout`; Resilience4j `@Retry`/`@TimeLimiter`; Actuator liveness vs readiness  |
| Node/Express | `fetch` has no timeout — `AbortSignal.timeout()`; axios `timeout` defaults to 0; `p-retry`, `got` retry options; pass the `AbortSignal` down                          |
| Vapor        | AsyncHTTPClient `HTTPClient.Configuration.Timeout(connect:read:)` or a per-request `deadline`; no built-in retry — hand-rolled loops need a cap and backoff           |
| .NET         | `HttpClient.Timeout` (100s default); `IHttpClientFactory` with Polly or `AddStandardResilienceHandler`; pass `CancellationToken`; health-check tags per probe         |
| Go           | `http.DefaultClient` has no timeout; `http.Client{Timeout}`; `context.WithTimeout` passed through every call (`QueryContext`, gRPC deadlines)                         |

## Example

Vulnerable shape:

```text
handler place_order(request):
    try:
        allowed = fraud_api.check(request.user)      # no timeout
    catch any:
        allowed = true                               # fails open

    for attempt in 1..5:                             # retries everything,
        try:                                         # no backoff, and the
            payment_api.charge(request.total)        # charge is not
            break                                    # idempotent
        catch any:
            continue

    analytics_api.track("order_placed")              # optional, but its
    return ok                                        # outage fails the order
```

Fixed shape — bounded, safe to repeat, fails closed, degrades the optional:

```text
handler place_order(request):
    deadline = request.deadline(5s)

    try:
        allowed = fraud_api.check(request.user, timeout = 1s, deadline)
    catch any as e:
        log.error("fraud check unavailable", e)
        return 503                                   # fails closed

    key = idempotency_key(request)
    retry(max = 3, backoff = exponential + jitter,
          on = [timeout, connection_error, 5xx], within = deadline):
        payment_api.charge(request.total, idempotency_key = key,
                           timeout = 2s)

    try:
        analytics_api.track("order_placed", timeout = 200ms)
    catch any as e:
        log.warn("analytics unavailable", e)         # order still succeeds
    return ok
```

## Severity guidance

- **High** — a security decision that fails open; a retried non-idempotent
  operation that moves money or sends irreversible side effects; a failure
  treated as an answer that leads to a wrong write.
- **Medium** — a missing or over-budget timeout on a hot path; unbounded,
  catch-all, or stacked retries that amplify load on a struggling
  dependency; an optional dependency failing a critical flow; a liveness
  probe that depends on a downstream.
- **Low** — missing jitter or backoff on a low-volume caller; missing
  timeouts on cold paths (admin, startup); a silent fallback whose stale
  data is harmless.
- Severity scales with blast radius: a shared pool or a single event loop
  turns one slow dependency into a full outage; an isolated worker does not.
