# Resource Limits

## Invariant

All work driven by input size is bounded. Whenever the cost of a request —
rows returned, items processed, bytes buffered, CPU spent matching — scales
with something the caller controls, there must be an explicit server-side
cap. The caller may *request* less than the cap, never more.

## Does not apply when

- The input's size is fixed by the protocol or schema itself (a single
  scalar field with validated bounds), not merely "expected to be small".
- A trusted upstream layer demonstrably enforces the bound (gateway body
  limit, infrastructure rate limiter) — verify it exists; do not assume.

## Why it happens

Development traffic is small and polite: lists have ten rows, uploads are
kilobytes, nobody sends a million-element array. Every unbounded path works
perfectly until data grows or one caller — malicious or just buggy — sends
the pathological input. The cost asymmetry is the trap: a request that is
cheap to send (one HTTP call) triggers work that is expensive to perform
(a full table scan, an exponential regex, a gigabyte in memory), so a
single client can exhaust a shared resource.

## Detection smells

- A list endpoint that returns the whole result set with no pagination, or
  one that accepts a `limit`/`page_size` parameter without clamping it to a
  server-side maximum.
- No size cap on request bodies or file uploads at the application layer —
  parsing, buffering, or storing whatever arrives.
- A loop over a user-supplied collection (array of IDs, bulk-create items,
  CSV rows) with no count limit before the loop starts — each element costs
  a query, a job, or an outbound call.
- A regex applied to user input where the pattern has nested or overlapping
  quantifiers (catastrophic backtracking), or where the pattern itself
  comes from the user.
- A file or response read entirely into memory (`read all`, buffering the
  full body) before processing, where streaming or chunking is possible and
  the size is caller-controlled.
- Expensive or authentication endpoints — login, password reset, report
  generation, exports, anything that fans out — with no rate limit, letting
  one client repeat the expensive thing arbitrarily fast.
- A cap guarding the wrong point: size checked after the payload is fully
  buffered, a per-iteration timeout where the total is unbounded, or limit
  arithmetic that can underflow or overflow — the cap exists, the peak
  allocation is unguarded.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the bounds usually live                                                                                                      |
|--------------|------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `page`/`per_page` via Pagy/Kaminari with a max; Rack::Attack for rate limits; `Rack::Utils` body limits often left to nginx        |
| Laravel      | `paginate()` with clamped `per_page`; `throttle` middleware; `max:` upload validation rules                                        |
| Django       | DRF pagination classes with `max_page_size`; `DATA_UPLOAD_MAX_MEMORY_SIZE`; django-ratelimit                                       |
| Spring       | `Pageable` with capped size; `spring.servlet.multipart.max-file-size`; Bucket4j/resilience4j rate limiting                         |
| Node/Express | `express.json({ limit })`; multer file size limits; express-rate-limit; RE2 for untrusted regex input                              |
| Vapor        | `app.routes.defaultMaxBodySize` / `.on(..., body: .collect(maxSize:))`; Fluent `.paginate(for: req)`; rate limiting via middleware |
| .NET         | `[RequestSizeLimit]` / Kestrel `MaxRequestBodySize`; built-in rate limiter middleware (`AddRateLimiter`); `Skip`/`Take` pagination |
| Go           | `http.MaxBytesReader`; server timeouts; `x/time/rate` limiter; paginate queries explicitly                                         |

## Example

Vulnerable shape:

```text
handler export_orders(request):
    orders = db.orders.where(user = request.principal)   # all of them
    rows   = file.read_all(request.upload)               # whole file in memory
    for id in request.body.ids:                          # caller picks N
        db.orders.update(id, ...)
    if regex_match(request.body.pattern, data): ...      # caller picks pattern
```

Fixed shape — every caller-controlled dimension is clamped:

```text
handler export_orders(request):
    size   = min(request.params.page_size or 50, MAX_PAGE_SIZE)  # server cap
    orders = db.orders.where(user = request.principal)
               .paginate(request.params.page, size)
    if request.upload.size > MAX_UPLOAD: respond 413
    stream  = file.open_stream(request.upload)           # chunked, not buffered
    if length(request.body.ids) > MAX_BATCH: respond 422
    rate_limiter.check(request.principal, "export")      # bound repetition
```

## Severity guidance

- **High** — an unauthenticated or cheap-to-call path does unbounded work
  (full-table list, user-controlled regex, unbounded upload buffering); in
  production one client can exhaust memory, connections, or CPU and take
  the service down for everyone.
- **Medium** — unbounded work behind authentication or on a low-traffic
  path; degrades as data grows and is abusable by any single account.
- **Medium** — missing rate limits on auth endpoints: beyond resource cost,
  this enables credential stuffing and brute force (overlaps with
  authentication findings).
- **Low** — a cap exists but is generous, or the bound lives only in
  infrastructure config the application does not control.
- Amplification raises severity: if each input element fans out to further
  work (a job, an outbound call, a write per element), rate one level
  higher than the same shape doing constant work per element.
