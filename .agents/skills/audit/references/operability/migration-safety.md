# Migration Safety

## Invariant

Schema changes deploy without downtime. A migration must run safely against
the production table at production size while the old code is still serving
traffic: no long locks, no destructive change in the same release as the
code that stops using the thing, and a rollback path that has actually been
thought through.

## Does not apply when

- The table is provably small and low-traffic (lookup/config tables), where
  a brief lock is harmless — but verify size in production, not dev.
- The system tolerates a maintenance window and the deploy process makes
  that explicit.

## Why it happens

Migrations are written and tested against a development database with a
hundred rows, where every operation is instant and nothing else holds
locks. Production has millions of rows and live traffic, and the same
statement takes a table lock for minutes. The migration and the code change
ship in one deploy, so developers assume they apply atomically — but during
the deploy window (and after a code rollback) old code and new schema, or
new code and old schema, run together.

## Detection smells

- An operation known to rewrite or lock a large table runs in one
  statement: adding a column with a volatile default, changing a column
  type, adding a non-concurrent index, adding a NOT NULL or foreign-key
  constraint that validates existing rows immediately.
- A destructive change — drop column, drop table, rename column/table —
  ships in the same release as the code change, instead of expand-contract:
  release 1 stops reading/writing it, release 2 (later) drops it. Renames
  are a drop plus an add; old code breaks the moment the migration runs.
- A backfill written as one `UPDATE ... SET ...` over the whole table
  instead of batched updates with pauses — one giant transaction, long row
  locks, and replication lag.
- New code that assumes the migration has already run (reads a new column
  on boot), or a migration that assumes new code is already deployed (a
  constraint old code's writes violate) — the deploy order is load-bearing
  but nothing enforces or documents it.
- A migration with no reverse operation and no stated rollback plan, on a
  change that destroys information (dropped data, lossy type change).
- Data transformation logic embedded in the migration that calls
  application models or external services — it breaks when the code it
  references changes or is gone.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Migration tooling and safety levers                                                                                                    |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | ActiveRecord migrations; `strong_migrations` gem flags unsafe ops; `disable_ddl_transaction!` + `algorithm: :concurrently`             |
| Laravel      | artisan migrations; `->change()` rewrites; chunked backfills via `chunkById` in a command, not the migration                           |
| Django       | `makemigrations`/`migrate`; `RunPython` with `reverse_code`; `AddIndexConcurrently`; separate schema and data migrations               |
| Spring       | Flyway/Liquibase versioned migrations; out-of-order and undo scripts; batched backfills outside DDL                                    |
| Node/Express | Knex/TypeORM/Prisma migrate; raw `CREATE INDEX CONCURRENTLY`; `down` functions often unimplemented — check                             |
| Vapor        | Fluent `AsyncMigration` with a real `revert`; drop to SQLKit for online operations (e.g. concurrent indexes); batch backfills manually |
| .NET         | EF Core migrations — review the generated SQL (`migrations script`); never `EnsureCreated` in prod; batch backfills manually           |
| Go           | golang-migrate/goose with down migrations; raw SQL so locks are explicit — review them; batch backfills                                |

## Example

Vulnerable shape:

```text
migration (same release as the code change):
    rename_column orders.state -> orders.status   # old code breaks instantly
    add_column orders.total NOT NULL DEFAULT compute()  # rewrites/locks table
    UPDATE orders SET total = ...                 # one statement, all rows
```

Fixed shape — expand-contract across releases:

```text
release 1: add nullable column orders.status     # additive, instant
           code writes both state and status, reads state
release 2: backfill in batches of 1000 with sleep between batches
           code reads status, still writes both
release 3 (after verifying): code drops all use of state
release 4: drop_column orders.state              # destructive, nothing reads it
# each step is individually deployable and individually rollbackable
```

## Severity guidance

- **High** — the migration will lock or rewrite a large hot table, or a
  destructive change ships with the code change; in production this is an
  outage during deploy, or an unrollbackable deploy (reverting the code
  leaves it incompatible with the schema).
- **Medium** — unbatched backfill on a sizable table (replication lag,
  long-held locks), or an undocumented deploy-order assumption that works
  only if nothing goes wrong mid-deploy.
- **Low** — missing reverse migration on a non-destructive change; friction
  during an incident rather than damage.
- Irreversible *and* destructive with no rollback plan rates one level
  higher: failure during the deploy means data loss, not just downtime.
