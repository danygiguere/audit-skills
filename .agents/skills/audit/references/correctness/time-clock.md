# Time, Timezone & Clock Correctness

## Invariant

Instants are stored and computed in UTC (or as timezone-aware values) and
converted to a local zone only at the display boundary. Duration, timeout,
and expiry logic reads a monotonic clock, never wall-clock time, so it
survives clock adjustments. Comparisons and arithmetic never mix
timezone-aware and naive values, and never assume the process's local zone.
Calendar math (days, months, "midnight", recurrence) accounts for DST
transitions, month lengths, and leap days rather than treating a day as a
fixed number of seconds.

## Does not apply when

- The value is a pure wall-clock label with no instant attached and no
  cross-zone interpretation (a store's posted opening hour, a recurring
  alarm the user sets in their own zone) — there, local civil time *is* the
  correct representation; storing it as UTC would be the bug.

## Why it happens

The default `now()` in most languages returns a naive, server-local
timestamp, so zone-incorrect values enter by reflex and read fine on a
machine set to UTC — then drift by hours in another region or break twice a
year at DST. The same wall clock is reused to measure elapsed time, so an
NTP step or a leap-second smear makes a timeout fire early, never, or
negative. Adding `86400` seconds to "now" looks like "tomorrow" until it
lands inside a DST gap or overlap. Persisted timestamps lose their offset on
the way through a column or JSON field, and a later read reinterprets them in
whatever zone the reader happens to run in.

## Detection smells

- A bare `now()`/`today()` that returns server-local time used for a stored
  instant, a comparison, or anything cross-zone — instead of an explicit UTC
  or zone-aware call.
- Elapsed time, rate limiting, timeouts, retries, or token expiry measured by
  subtracting two wall-clock readings rather than a monotonic clock.
- Date math by adding/subtracting raw seconds (`+ 86400`, `* 3600`) to cross a
  day/month/DST boundary, instead of calendar-aware date arithmetic.
- A timezone-aware value compared with, or subtracted from, a naive one — or
  an equality/`<`/`>` between timestamps of unstated zones.
- A timestamp serialized or stored without its offset/zone (a naive column, a
  format string with no `Z`/offset), then parsed back in the reader's local
  zone.
- A fixed UTC offset hardcoded for a zone that observes DST (`+05:00` for a
  zone that shifts), or a hand-rolled offset table instead of the tz database.
- "Midnight", "start of day", or day-bucketing computed in UTC for a
  user-facing boundary that should be in the user's zone (off-by-one days in
  reports, streaks, cutoffs).
- Token/grant TTLs with no clock-skew tolerance between issuer and verifier,
  rejecting or accepting at the boundary; or `exp`/`nbf` checked against
  local time.
- Two-digit-year, `localtime`-without-zone, or platform-default-zone
  assumptions; `Date` arithmetic in JS done on local-zone getters.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Correct primitive vs the trap                                                                                              |
|--------------|----------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Time.current`/`Time.zone` + `store UTC` vs `Time.now`/`Date.today`; `1.day.from_now` vs `+ 86400`; `Process.clock_gettime(:MONOTONIC)` |
| Laravel      | Carbon with explicit tz + UTC storage vs `date()`/`strtotime` local; `addDay()` vs `+ 86400`; `hrtime(true)` for elapsed   |
| Django       | `USE_TZ=True`, `timezone.now()` (aware) vs `datetime.now()` (naive); `timedelta` care at DST; `time.monotonic()`           |
| Spring       | `Instant`/`ZonedDateTime` + `Clock` injected vs `LocalDateTime.now()`/`new Date()`; `System.nanoTime()` for durations      |
| Node/Express | store epoch/ISO-UTC, format with `Intl`/Temporal/`luxon` vs local `Date` getters; `process.hrtime.bigint()` for elapsed    |
| Vapor        | `Date` (UTC instant) + `Calendar`/`TimeZone` at edges vs `DateComponents` in default zone; `DispatchTime`/`ContinuousClock`|
| .NET         | `DateTimeOffset`/`DateTime.UtcNow` + `TimeZoneInfo` vs `DateTime.Now`; `Stopwatch` for elapsed; NodaTime for calendar math |
| Go           | `time.Now().UTC()` + `time.LoadLocation` vs naive local; `AddDate` for calendar vs adding `Duration`; monotonic via `time.Since` |

## Example

Vulnerable shape — server-local now, wall-clock expiry, raw-seconds "tomorrow":

```text
handler issue_token(user):
    token.created = now()                       # naive, server-local
    token.expires = now() + 3600                # wall clock; NTP step breaks it
    store(token)

handler valid(token):
    return now() < token.expires                # zone/skew-dependent, drifts

handler daily_cutoff(user):
    return start_of_day(now())                  # UTC midnight, not user's day
```

Fixed shape — UTC instants, monotonic for elapsed, calendar-aware boundary:

```text
handler issue_token(user):
    token.created_utc = now_utc()               # aware/UTC instant
    token.ttl_seconds = 3600                     # store a duration, not a clock
    token.issued_mono = monotonic()             # for server-side elapsed checks
    store(token)

handler valid(token):
    return now_utc() <= token.created_utc + seconds(token.ttl_seconds + SKEW)

handler daily_cutoff(user):
    return start_of_day(now_utc(), zone = user.timezone)   # user's civil day
```

## Severity guidance

- **Critical** — a clock bug that breaks a security or financial boundary:
  token/session expiry that never fires or fires early, a signature/nonce
  window defeated by skew, or billing/interest periods miscounted by a day.
- **High** — wall-clock-based timeouts/rate limits that an NTP step or DST
  transition can make fire wrongly under load, or stored naive timestamps that
  reinterpret across regions and corrupt ordering or audit trails.
- **Medium** — off-by-one day boundaries in reports, streaks, or cutoffs from
  UTC-vs-user-zone bucketing; DST-naive recurrence that double-fires or skips.
- **Low** — display-only zone inconsistency, or fragile time handling that is
  correct today but unguarded against a future cross-zone use; hardening note.
