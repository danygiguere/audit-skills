# N+1 Queries

## Invariant

Never query inside a loop over a collection; load related data in bulk. The
number of queries (or HTTP/cache calls) a code path issues must be constant,
not proportional to the number of items it processes. One query for the
collection, one (or a fixed few) for everything related to it.

## Does not apply when

- The collection is provably bounded and tiny (a hardcoded enum, a config
  list of three items) — not "usually small in dev".
- Each iteration genuinely requires a serialized round-trip whose input
  depends on the previous result (rare; document it when true).

## Why it happens

Lazy loading makes per-item access look like a cheap property read — the
query it fires is invisible at the call site. The code is correct, tests
pass against ten rows, and the cost only appears in production where the
collection has ten thousand. Serializers and template layers hide the loop:
the handler issues one query, but the rendering of each item triggers more.

## Detection smells

- A loop (or map/each) over query results where the body accesses a related
  record, association, or foreign-keyed lookup on each element.
- The same shape with a remote call per item: an HTTP request, cache get, or
  external API call inside iteration over a collection.
- A serializer, presenter, or template that renders a per-item field whose
  value comes from another table, and the collection was fetched without its
  relations preloaded.
- A count, sum, or exists-check computed per row (`for each order: count
  its items`) instead of one grouped aggregate query.
- A helper function that takes a single ID and queries, called from inside a
  loop — the N+1 is split across two functions and invisible in either alone.
- Nested loops over related collections, multiplying queries (N×M).

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Bulk-loading mechanism                                                                                                |
|--------------|-----------------------------------------------------------------------------------------------------------------------|
| Rails        | `includes`/`preload`/`eager_load`; `strict_loading` to surface lazy access                                            |
| Laravel      | `with()` eager loading; `withCount()`; `Model::preventLazyLoading()`                                                  |
| Django       | `select_related` (FK joins), `prefetch_related` (reverse/M2M), `annotate`                                             |
| Spring       | JPA fetch joins / `@EntityGraph`; beware default `LAZY` access in loops                                               |
| Node/Express | DataLoader batching; ORM `include`/`populate`; `WHERE id IN (...)` then map                                           |
| Vapor        | eager-load with `.with(\.$relation)` on the query; a `find` or child query inside a `for` over models is the smell    |
| .NET         | lazy-loading proxies are the trap; `Include()`/`ThenInclude()` or projections; a query inside `foreach` over entities |
| Go           | a query inside `for range` over rows; GORM `Preload`; batch with `IN` (sqlx.In)                                       |

## Example

Vulnerable shape:

```text
orders = db.orders.where(status = "open")        # 1 query
for order in orders:
    customer = order.customer                    # +1 query per order
    total    = db.items.count(order_id = order.id)  # +1 more per order
    render(order, customer.name, total)
```

Fixed shape — constant query count regardless of N:

```text
orders    = db.orders.where(status = "open").preload(customer)  # 2 queries
totals    = db.items.group_by(order_id)
              .count(where order_id in orders.ids)              # 1 query
for order in orders:
    render(order, order.customer.name, totals[order.id])
```

With no eager-loader available (raw SQL, micro-ORMs, query builders), the
same result comes from the **two-query + in-memory grouping** pattern —
fetch the parents, collect their IDs, fetch all children in one `IN` query,
and group by foreign key in memory:

```text
users = db.query("SELECT * FROM users LIMIT 25")            # 1 query
posts = db.query("SELECT * FROM posts
                  WHERE user_id IN (?)", ids(users))        # 1 query
posts_by_user = group_by(posts, post -> post.user_id)       # in memory,
for user in users:                                          # no queries
    user.posts = posts_by_user[user.id] or []
# 2 queries total, regardless of how many users
```

The same fix shape applies to remote calls: collect the IDs, issue one batch
request, then iterate over the in-memory result.

## Severity guidance

- **High** — the loop runs on a hot path (list endpoints, dashboards,
  per-request middleware) over an unbounded collection; in production this
  is latency that grows with data, connection-pool exhaustion, and outages
  under load.
- **Medium** — unbounded collection on a low-traffic path or background job;
  degrades quietly until data grows.
- **Low** — collection bounded by pagination or a hard cap, so the constant
  factor is contained.
- Per-item *remote* calls (HTTP, external APIs) rate at least one level
  higher than per-item database queries — each iteration costs a full
  network round-trip and a dependency's error budget.
