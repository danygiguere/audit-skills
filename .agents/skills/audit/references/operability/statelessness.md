# Statelessness

## Invariant

In an app meant to run as N interchangeable replicas, state may live in
process memory or on local disk only when losing it is harmless and no peer
replica needs to see it. Anything that must survive a restart, be visible to
another replica, or be globally accurate — sessions, counters, locks,
uploads, schedules, connection registries — lives in a shared backing store.
The acid test: kill any replica, or add a second one; observable behavior
must not change.

## Does not apply when

- The system is deliberately stateful: databases, actor clusters with
  sharding and ownership, single-instance internal tools, desktop apps.
  Audit those against their own design, not this file.
- The in-process state is a true cache: re-derivable, staleness-tolerant,
  bounded. Per-replica caches are an optimization, not a finding — unless
  the code treats them as accurate or authoritative.

## Why it happens

Everything works with one process in development, and a module-level
variable is the easiest place to put anything. The failures only appear with
the second replica or the next deploy: lost sessions, rate limits that
multiply by replica count, broadcasts reaching half the clients, schedulers
running twice. Framework defaults make it worse — memory/file session and
cache drivers are correct on a laptop and wrong behind a load balancer.

## Detection smells

- Module-, class-, or static-level mutable collections accumulating
  per-user or per-request data: registries, "seen" sets, counters,
  in-memory session maps.
- Rate limits, quotas, or dedupe backed by process-local counters where
  accuracy matters — the real limit becomes `limit × replicas`, reset on
  every deploy.
- Memory or file session/cache drivers in production config; logic that
  only works if the load balancer pins users to one replica (sticky
  sessions as a correctness requirement, not an optimization).
- Uploads or generated artifacts written to local disk and expected to
  exist on a later request — which may land on another replica or after the
  disk is gone.
- Process-local locks or mutexes guarding resources other replicas also
  mutate — the lock works, the system doesn't (once shared, the race is
  `../correctness/state-management.md`'s problem).
- In-process timers/schedulers inside the web process: runs N times with N
  replicas, zero times during a rolling restart (move to
  `../correctness/background-work.md` territory — a real scheduler).
- WebSocket/SSE connection registries in memory with no shared pub/sub —
  broadcasts reach only the clients connected to this replica.
- Persistent-worker runtimes leaking state between requests: anything
  initialized per-process and mutated per-request can surface one user's
  data to the next (also a `../access-data-security/data-exposure.md`
  finding).

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name
the concept in common ecosystems.*

| Ecosystem    | Where the discipline usually lives                                                                                                                  |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | class-level `@@` state in controllers/jobs; `Rails.cache` `:memory_store` in prod; ActiveStorage local disk service behind a load balancer          |
| Laravel      | `SESSION_DRIVER=file` / `CACHE_STORE=file\|array` in prod; Octane keeps workers alive — static/singleton state persists across requests and users   |
| Django       | `LocMemCache` in prod; module-level dicts; `FileSystemStorage` for uploads on ephemeral disks                                                       |
| Spring       | mutable fields on singleton beans; `@Scheduled` in multi-replica deployments without a distributed lock (ShedLock); in-memory session/registry maps |
| Node/Express | module-scope objects (the classic); express-session `MemoryStore` (it warns you); multer disk storage on ephemeral filesystems                      |
| Vapor        | globals / `app.storage` mutated per request; in-memory sessions (`.memory`); user uploads under the app's own `Public/`                             |
| .NET         | `static` fields; `IMemoryCache`/`AddDistributedMemoryCache` as source of truth; local `wwwroot` writes                                              |
| Go           | package-level vars and `sync.Map` registries; in-process `time.Ticker` schedulers; local disk writes in handlers                                    |

## Example

Vulnerable shape:

```text
rate_limiter = {}                       # module-level: one map per process

handler send_sms(request):
    count = rate_limiter[request.user.id] or 0
    if count >= 5: respond 429
    rate_limiter[request.user.id] = count + 1
    sms.send(...)
# real limit is 5 x replicas, resets on every deploy,
# and works perfectly in development
```

Fixed shape — one counter, all replicas, survives restarts:

```text
handler send_sms(request):
    count = shared_store.incr("sms:" + request.user.id, ttl = 1h)
    if count > 5: respond 429
    sms.send(...)
```

## Severity guidance

- **High** — authoritative state in process memory or on ephemeral disk:
  sessions, payment/quota counters, dedupe sets, user uploads. Wrong with
  more than one replica, lost on every deploy.
- **Medium** — process-local locks or schedulers in multi-replica
  deployments (duplicate or missed work); connection registries without a
  shared bus.
- **Low** — per-process caches that are legitimate but unbounded, or
  treated as fresher than they can be.
- Cross-request leakage of one user's data through persistent-worker state
  is also a data-exposure finding — report both.
