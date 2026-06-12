# Schema Design (indexes, foreign keys, constraints)

## Invariant

Every relationship is enforced by a real foreign-key constraint with a
deliberate `ON DELETE` choice; every hot query's access path is backed by an
index; and every integrity rule the application depends on — presence,
uniqueness, ranges — exists in the schema, not only in app-level validation.
A finding here must be consequence-backed: orphaned rows, duplicates, wrong
results, or measurably slow queries.

## Does not apply when

- The concern is style: naming conventions, singular/plural tables, column
  order, normalization-level preferences, UUID-vs-integer primary keys.
  These are never findings, regardless of taste.
- The concern is how a schema change *deploys* (locks, backfills, rollback)
  — that is `migration-safety.md`. This file audits what the schema *says*.

## Why it happens

ORMs declare relationships in code and run happily without the database
enforcing them — until a job, console session, or second service bypasses
the app's validation. Migrations are written for the feature's happy path;
indexes get added only after production slowness is felt. And engines
differ where developers assume they don't: Postgres does **not**
auto-index foreign-key columns; MySQL/InnoDB does.

## Detection smells

- A migration adds a foreign-key (or `*_id`) column with no index on it —
  every join, lookup, and cascading delete on that column scans.
- A relationship that exists only in the ORM (association, navigation
  property) with no FK constraint in the database — orphaned rows are a
  matter of time.
- An FK with default or unspecified `ON DELETE` where the choice matters —
  cascade, restrict, and set-null produce three different systems.
- Columns the application treats as required but the schema allows NULL;
  uniqueness enforced only by app validation (see `../correctness/state-management.md`
  — the race makes duplicates, the missing unique index makes them permanent).
- Queries in the code filtering, joining, or ordering on columns no index
  covers — or a composite index whose column order doesn't match the query;
  tenant/soft-delete columns missing from the indexes that filter on them.
- Type-level bugs: money in float/double, naive timestamps where time zones
  matter, free-text strings standing in for enums with no CHECK constraint,
  mixed charsets/collations across joined columns.
- A table with no primary key; duplicate or shadowed indexes; indexing
  nearly every column of a write-heavy table.

## Verification note

Constraint findings (missing FK, NOT NULL, unique) are verifiable statically
from migrations and schema files. Index *usefulness* is only provable
against real data: when database access is available, confirm with
`EXPLAIN`/`EXPLAIN ANALYZE`; otherwise report "likely missing index", not a
confirmed finding. Fixes on large live tables must follow
`migration-safety.md` (concurrent index builds, batched backfills).

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the discipline usually lives                                                                                                                        |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `t.references :user, foreign_key: true` (index is default, FK is opt-in); `validates_uniqueness_of` without a unique index is the smell                   |
| Laravel      | `$table->foreignId('user_id')->constrained()->cascadeOnDelete()`; bare `unsignedBigInteger` with no `->foreign()`/`->index()` is the smell                |
| Django       | `ForeignKey` creates both FK and index, and `on_delete` is mandatory; `unique=True` vs validator-only uniqueness                                          |
| Spring       | JPA `@ManyToOne` does not guarantee an index — declare via `@Index`/DDL; `@Column(nullable = false, unique = true)`; auto `hbm2ddl` in prod is the smell  |
| Node/Express | Prisma `@relation` creates the FK, indexes need `@@index`; Sequelize `references` + explicit indexes; Mongoose `unique` is index creation, not validation |
| Vapor        | Fluent `.references(..., onDelete: .cascade)` and `.unique(on:)`; secondary indexes drop to SQLKit raw SQL                                                |
| .NET         | EF Core conventions auto-create FK indexes; `.OnDelete(DeleteBehavior.…)` explicit; `HasIndex`/`IsRequired` in the model builder                          |
| Go           | GORM does not create FK constraints unless the `constraint:` tag/config says so; `gorm:"index"`; migrate/goose raw SQL — everything is explicit           |

## Example

Vulnerable shape:

```text
migration create_comments:
    create table comments (
        id      serial primary key,
        post_id integer,                  # no FK, no index, nullable
        body    text
    )
# app code: Comment belongs_to Post; hot query: WHERE post_id = ?
```

Fixed shape — the relationship, the access path, and the integrity rules
all live in the schema:

```text
migration create_comments:
    create table comments (
        id      bigint primary key,
        post_id bigint not null
                references posts(id) on delete cascade,
        body    text not null
    )
    create index on comments (post_id)    # Postgres won't do this for you
```

## Severity guidance

- **High** — missing FK or unique constraint where a second writer exists
  (jobs, consoles, other services): orphans or duplicates are inevitable.
  Money stored in float/double.
- **Medium** — missing index on a confirmed hot path (EXPLAIN or evident
  scale); `ON DELETE` defaulted where the wrong behavior corrupts or
  mass-deletes; required-but-nullable columns.
- **Low** — duplicate or shadowed indexes; over-indexing; any "likely
  missing index" not yet verified against real data.
- Existing corrupted data (orphans already present) raises the related
  finding one level — the bug has already fired.
