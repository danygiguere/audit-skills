# Blocking I/O in Async Contexts

## Invariant

Code running on a cooperative scheduler — an event loop, coroutine
dispatcher, or reactor — never blocks it: no synchronous I/O, no blocking
sleeps, no CPU-heavy work inline. Blocking work is handed to a mechanism
built for it (async equivalent, worker pool, dedicated thread). One blocked
scheduler thread stalls every task sharing it.

## Does not apply when

- The code runs on a thread-per-request runtime (classic servlet stacks,
  process-based PHP, threaded Ruby servers), where a blocking call ties up
  only its own thread. The invariant then shifts form: outbound calls
  without timeouts exhaust the thread/worker pool — same outage, slower
  onset. Audit for that instead.

## Why it happens

The synchronous and asynchronous variants of the same client look almost
identical at the call site, so the wrong one passes review. A library that
was fine in a threaded web handler gets reused inside an event loop. CPU
work (parsing, image resizing, crypto) creeps into handlers one commit at a
time. And nothing fails in development, where a single user never notices a
blocked loop — the stall only appears under concurrency.

## Detection smells

- A synchronous I/O call (database, HTTP, filesystem, sleep) inside an async
  function, coroutine, or event-loop callback, with no handoff to a worker.
- An async handler that awaits nothing but does heavy CPU work inline —
  parsing large payloads, rendering, compression, hashing.
- Retry/backoff implemented with a blocking sleep inside async code.
- Sync and async clients for the same dependency coexisting in the codebase
  — one of them is being used in the wrong context somewhere.
- A lock held across an await point, or acquired blockingly on the
  scheduler thread.
- Sync-over-async: asynchronous work started and then immediately blocked on
  for its result from scheduler-managed code — latency at best, deadlock at
  worst.
- On thread-per-request runtimes: outbound HTTP/DB calls with no timeout —
  the pool-exhaustion equivalent of blocking the loop.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the rule shows up                                                                                                                                          |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | threaded (Puma): blocking allowed but pool-bounded — timeouts matter; never block inside Async/Fiber schedulers                                                  |
| Laravel      | PHP-FPM is sync per-process (rule mostly N/A); under Octane/Swoole/RoadRunner the event-loop rules apply                                                         |
| Django       | sync views run on threads; `async def` views must not call sync ORM/HTTP directly — wrap in `sync_to_async`                                                      |
| Spring       | WebFlux/Reactor: no blocking on event-loop threads — offload to `boundedElastic`; detected by BlockHound                                                         |
| Node/Express | single event loop: no `*Sync` fs/crypto APIs in handlers; CPU work to `worker_threads`; beware long JSON.parse                                                   |
| Vapor        | SwiftNIO event loops: never block — async/await throughout; offload blocking or CPU work with `app.threadPool.runIfActive`                                       |
| .NET         | `.Result`/`.Wait()`/`GetAwaiter().GetResult()` is the classic sync-over-async deadlock; async all the way; `Task.Run` for CPU work; watch thread-pool starvation |
| Go           | goroutines are preemptive, so blocking is cheap — the rule becomes `context.WithTimeout` on every call and bounded worker pools instead                          |

## Example

Vulnerable shape:

```text
async handler generate_report(request):
    data = http.get_sync(analytics_url)     # blocks the event loop: every
                                            # concurrent request stalls
    pdf = render_pdf(data)                  # CPU-heavy, still on the loop
    return pdf
```

Fixed shape — I/O goes async, CPU work leaves the scheduler:

```text
async handler generate_report(request):
    data = await http.get_async(analytics_url, timeout = 10s)
    pdf  = await worker_pool.run(render_pdf, data)
    return pdf
```

## Severity guidance

- **High** — a blocking call on a shared event loop in a hot path: one slow
  dependency stalls the entire process, not one request.
- **Medium** — CPU-heavy inline work on the scheduler; sync-over-async with
  deadlock potential; missing timeouts on pool-bound outbound calls.
- **Low** — short, rare blocking calls in cold async paths (startup,
  admin-only endpoints).
- Severity scales inversely with how much the runtime shares: single event
  loop > small reactor pool > large thread pool.
