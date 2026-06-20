# Caching Correctness

## Invariant

A cache entry is keyed by everything that varies its value — including the
principal and tenant when the value is per-user — and is invalidated or
expires whenever its source of truth changes. A cache miss never stampedes
the origin, a cache failure degrades to the source rather than serving wrong
or stale data, and nothing sensitive is written to a cache shared across
principals or to a shared/CDN layer without an explicit per-user directive.

## Does not apply when

- The cached value is immutable and public (a content-addressed asset, a
  released artifact) — its key already encodes its full identity, so there is
  nothing to invalidate and nothing principal-specific to leak.

## Why it happens

Caching is added late, as a performance patch, against code that assumed a
fresh read every time — so invalidation is bolted on per call site and one
writer is always forgotten, leaving a stale entry no one can explain. Keys
are built from the obvious inputs and omit the implicit ones (the logged-in
user, the tenant, the locale, the feature flag), so one principal is served
another's value. Under a traffic spike a popular key expires and every
request misses at once, hammering the origin. And HTTP/CDN caching is
controlled by headers the application rarely sets deliberately, so a
per-user response lands in a shared edge cache.

## Detection smells

- A cache key missing a dimension the value depends on — no user/tenant id on
  per-principal data, no locale on localized output, no version on
  flag-dependent output: the classic cross-user cache leak.
- A write path that updates the source of truth but no corresponding
  invalidation (or a TTL so long the staleness is a bug, not a tradeoff).
- Read-modify-write against a cached value treated as authoritative — the
  cache is a copy; the check-then-act race lives in the source (see
  `state-management.md`).
- A hot key with a single expiry and no jitter, lock, or
  stale-while-revalidate — every client misses simultaneously (stampede /
  thundering herd / dogpile).
- Negative or error results cached with the same TTL as success, pinning a
  transient failure (or a 404 for a row that now exists).
- A cache outage that throws instead of falling through to the origin, or a
  populated cache trusted without any path to rebuild it.
- Per-user or authenticated responses sent with `Cache-Control: public`,
  a missing `Vary`, or no `private`/`no-store` — a CDN or proxy serves one
  user's response to another (overlaps `data-exposure.md`).
- Unbounded in-process caches with no eviction (memory leak), or a
  process-local cache assumed coherent across replicas (see
  `statelessness.md`).

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Cache primitive vs the trap                                                                                       |
|--------------|-------------------------------------------------------------------------------------------------------------------|
| Rails        | `Rails.cache.fetch(key, race_condition_ttl:)`; scope keys per user/tenant; `fresh_when`/`stale?` set `Cache-Control` |
| Laravel      | `Cache::remember`; `Cache::lock` against stampede; tag-based flush vs forgotten `Cache::forget`; `response()->header` |
| Django       | `cache.get_or_set`, per-view `vary_on_*`; `CACHE_MIDDLEWARE_KEY_PREFIX`; `cache_control(private=True)` on auth views |
| Spring       | `@Cacheable(key=…, sync=true)` / `@CacheEvict`; key must include principal; `CacheControl.cachePrivate()` on responses |
| Node/Express | Redis `SET … EX`/`NX` lock; key prefix per tenant; `res.set('Cache-Control','private, no-store')` for auth routes    |
| Vapor        | `app.caches` / Redis; encode user into the key; set `Cache-Control` via middleware; avoid request-local globals      |
| .NET         | `IDistributedCache` / `IMemoryCache` with size limits; `ResponseCache` `VaryByHeader`; `Cache-Control: private`       |
| Go           | `singleflight.Group` collapses concurrent misses; per-tenant key prefix; set `Cache-Control` header explicitly        |

## Example

Vulnerable shape — key omits the principal, write skips invalidation, miss
stampedes:

```text
handler dashboard(request):
    return cache.fetch("dashboard", ttl=300) do      # no user in key
        build_dashboard(request.user)                 # leaks across users
    end

handler update_profile(request):
    db.save(request.user, request.body)               # source changed,
    respond 200                                        # cache never busted
# 300s later the key expires under load -> every request rebuilds at once
```

Fixed shape — principal in the key, invalidation on write, single-flight
rebuild:

```text
handler dashboard(request):
    key = "dashboard:" + request.user.id              # per-principal key
    return cache.fetch(key, ttl=300, single_flight=true) do
        build_dashboard(request.user)
    end

handler update_profile(request):
    db.save(request.user, request.body)
    cache.delete("dashboard:" + request.user.id)      # bust on write
    respond 200
```

## Severity guidance

- **Critical** — a shared or CDN cache serves one principal's data to another
  (missing principal/tenant in the key, or a `public` directive on an
  authenticated response): a confidentiality breach, not just staleness.
- **High** — a stampede that can take down the origin under realistic load,
  or stale data on a path where correctness matters (price, balance,
  permission shown after a change).
- **Medium** — missing invalidation that serves visibly outdated data, or
  cached errors/negatives that pin a transient failure.
- **Low** — unbounded or process-local cache that is a latent memory or
  coherence risk but not currently wrong; flag as hardening.
