# Query cardinality

## Invariant

Any operation that assumes a predicate identifies exactly one row must be
backed by a uniqueness guarantee — a primary key, or a column with a UNIQUE
constraint. A write (UPDATE/DELETE) must additionally be provably
single-target when one row is intended, or deliberately and verifiably
bounded when several are. A query is correct only when the number of rows it
touches is the number the code assumes.

## Does not apply when

- The predicate is the primary key, or a column the schema enforces as
  UNIQUE — the database already guarantees at most one matching row.
- A multi-row read or write is the intended behavior and the code treats the
  result as a set: it iterates, aggregates, or checks the affected-row count.

## Why it happens

Human-readable identifiers — name, email, slug, title, reference code — feel
unique because they are unique in the developer's test data, so code looks
them up and acts as if exactly one row comes back. ORMs encourage it:
`findOne`, `.first()`, `.single()`, and `find_by` return one row from a
query that could match many, silently discarding the rest. On the write
side, `UPDATE ... WHERE <column>` reads identically whether the column has a
UNIQUE constraint or not — the danger is invisible at the call site and
surfaces only once a second matching row exists in production.

## Detection smells

- An UPDATE or DELETE keyed on a non-unique, nullable, or human-readable
  column (`name`, `email`, `slug`, `status`) that the code assumes selects
  one row, with no UNIQUE constraint guaranteeing it — a duplicate makes the
  write fan out across unintended rows.
- A mutation whose WHERE clause is missing, commented out, or broader than
  the single row intended — `DELETE FROM x` with no predicate, or a predicate
  missing a discriminator the sibling read includes.
- `findOne` / `.first()` / `.single()` / `find_by` on a column with no
  uniqueness guarantee — the "one" row returned is arbitrary, and which one
  can change between calls.
- A column treated as unique in application logic (lookups, upserts,
  find-or-create, join keys) with no matching UNIQUE constraint in the schema.
- A bulk update or delete driven by a filter from request input, with no
  upper bound and no assertion on the affected-row count.
- An ORM update/delete run on a query whose filter was built conditionally,
  where a skipped branch silently widens the target set to every row.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Single-row assumptions to back with a uniqueness guarantee                                                                          |
|--------------|------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `find_by`/`where(...).first`; `update_all`/`delete_all` on a non-unique scope; back it with `add_index ..., unique: true`           |
| Laravel      | `where('col', x)->first()`/`->update([...])` on a non-PK column; back it with a `unique()` migration constraint                     |
| Django       | `.get()` raising `MultipleObjectsReturned`; `filter(...).update()` over more rows than meant; `unique=True`/`UniqueConstraint`      |
| Spring       | a derived `findByX` returning one when several match; `@Modifying` bulk update; `@Column(unique = true)`/unique constraint          |
| Node/Express | `findOne`/`SELECT ... LIMIT 1` on a non-unique column; `UPDATE ... WHERE col = ?` with no UNIQUE index behind it                    |
| Vapor        | `.filter(\.$col == x).first()` on a non-unique field; `.update()`/`.delete()` over a non-unique filter; `.unique(on:)` in migration |
| .NET         | `SingleOrDefault`/`FirstOrDefault` on a non-key column; `ExecuteUpdate`/`ExecuteDelete` over many rows; `HasIndex(...).IsUnique()`  |
| Go           | `db.Where("col = ?", x).First(&row)`; GORM `Updates`/`Delete` over a non-unique filter; `uniqueIndex` tag / unique constraint       |

## Example

Vulnerable shape — the write keys on a non-unique column and clobbers every
match; the lookup assumes one row from a many-row query:

```text
handler rename_account(request):
    db.execute("UPDATE accounts SET name = ?
                WHERE name = ?", new_name, old_name)   # every account named old_name
    owner = db.users.find_one(email = request.email)   # arbitrary row if email not unique
```

Fixed shape — writes key on the primary key (or a UNIQUE-backed column), the
affected count is asserted, and single-row reads run against a column the
schema guarantees unique:

```text
handler rename_account(request):
    n = db.execute("UPDATE accounts SET name = ?
                    WHERE id = ?", new_name, account_id)   # one row, by primary key
    assert n == 1                                          # affected-count guard
    owner = db.users.find_one(id = account.owner_id)       # email also UNIQUE in schema
```

## Severity guidance

- **High** — a wrong-target UPDATE or DELETE corrupts or destroys rows other
  than the intended one (non-unique predicate, missing or over-broad WHERE):
  data loss or silent overwrite of unrelated records.
- **Medium** — a single-row read on a non-unique column returns an arbitrary
  row, producing wrong-but-recoverable behavior (wrong record shown, wrong
  branch taken); a missing UNIQUE constraint that lets duplicates accumulate.
- **Low** — the assumption holds in practice (effectively-unique data) but
  nothing in the schema enforces it — latent until a duplicate first appears.
- A mutation reachable by unauthenticated or high-volume input rates one
  level higher: the fan-out is triggerable on demand, not just by accident.
