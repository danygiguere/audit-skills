# Algorithmic Complexity

## Invariant

In-memory work over a collection that grows with input or data uses a data
structure that fits how it is accessed. Exact-match lookups, membership
tests, and joins go through a hash map or set built once, not a linear scan
repeated per element. Range, nearest-match, and ordered queries go through
sorted data with binary search or an ordered tree, and the code that sorts
and the code that searches agree on the same order. A path whose input grows
linearly must not do quadratic work by accident.

## Does not apply when

- The collection is provably bounded and tiny (a hardcoded enum, a fixed
  list of a few config entries), not merely "usually small in dev".
- The code runs once, off any request or job path (a one-off script, a
  startup step over a fixed dataset), and its worst-case runtime is known
  to be acceptable.
- The work happens in the database. A missing index is
  `schema-design.md`, a query per loop iteration is `nplus1.md`, and an
  unbounded input size is `resource-limits.md`. This checklist covers the
  in-memory structure once the data is already loaded.
- The "better" structure would only shave a constant factor on a path with
  no measured or plausible cost. Do not report micro-optimizations.

## Why it happens

A linear search reads as a single cheap call: `list.includes(x)`,
`items.find(i => i.id == id)`, `x in rows`. Put it inside a loop and the
cost becomes O(n·m), but nothing at the call site shows that. Tests use ten
items, so quadratic and linear look the same until production has a hundred
thousand. Functional idioms hide copies: spreading an accumulator in every
`reduce` step, or concatenating immutable strings in a loop, rebuilds the
whole value each time. Binary search has the opposite problem. It is fast
but only correct on sorted data, and the code that keeps the data sorted is
often far from the code that searches it, so an unsorted insert or a
mismatched comparator returns wrong answers without any error.

## Detection smells

- **Linear lookup inside a loop**: `contains`, `includes`, `indexOf`, `find`,
  `filter(...)[0]`, `any`, or Python `x in some_list` inside iteration over
  another growing collection. Fix: build a set or a map keyed by the lookup
  field once, before the loop.
- **Nested-loop join or dedupe**: two nested loops matching records by key
  (`for a in A: for b in B: if a.id == b.a_id`), or deduplicating by
  checking each item against a results list. Fix: index one side in a hash
  map, or deduplicate through a set.
- **Hidden quadratic copies**: `[...acc, x]` or `{...acc, [k]: v}` inside
  `reduce`; `acc + [x]` on lists; immutable string concatenation in a loop
  where the language does not optimize it; `shift`/`unshift`,
  `list.remove(0)`, `insert(0, x)`, or `pop(0)` on an array-backed list in a
  loop (each one moves every element). Use a deque, a builder, or push then
  reverse.
- **Repeated sort or rebuild**: sorting, copying, or building the same index
  inside a loop or per request when the source has not changed; computing
  `min`/`max`/`count` over the whole collection on every iteration.
- **Binary search correctness** (rate these as correctness bugs, not
  performance):
  - binary search on data that is not sorted, or whose sort order is broken
    by later appends or inserts;
  - data sorted with one comparator or key and searched with another
    (case-insensitive sort, case-sensitive search; sort by name, search by
    id);
  - a hand-rolled binary search with off-by-one bounds, an overflowing
    midpoint `(lo + hi) / 2` in fixed-width integers, or a missing
    not-found case;
  - a library search whose not-found return value (a negative insertion
    point, the end iterator, `len(a)`) is used as if it were a valid index.
- **Hash map correctness**:
  - mutable objects used as keys and then modified, so the entry can no
    longer be found;
  - `equals` and `hashCode` (or `__eq__` and `__hash__`) that disagree, or
    one overridden without the other;
  - a map keyed by object identity where value equality was intended (JS
    `Map` or `Set` with object or array keys; reference-type keys without
    equality overrides);
  - floating-point keys compared for exact equality.
- **Wrong structure for the query**: a hash map used for range or "nearest"
  queries (forcing a full scan), or a sorted array that receives frequent
  inserts in the middle (each insert O(n)). Use an ordered map or tree for
  mixed insert and range workloads, and a heap for repeated min or max.
- **Attacker-controlled hash keys**: user-supplied strings used as keys in a
  hash table whose implementation has no randomized seed or collision
  protection, letting crafted keys degrade it to O(n) per operation
  (HashDoS). Relevant mainly to custom hash tables and older runtimes; see
  `resource-limits.md` for the input-size cap.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Hash / ordered structures and the usual traps                                                                                                |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Array#include?`/`find` in loops vs `Set`, `index_by`, `group_by`; `Array#bsearch` requires sorted input; `+=` on arrays copies              |
| Laravel      | Collection `contains`/`firstWhere` in loops vs `keyBy()`/`groupBy()`; PHP `in_array` vs `isset($map[$k])`; `array_unshift` is O(n)           |
| Django       | Python `x in list` vs `set`/`dict`; `bisect` needs sorted input; `list.pop(0)` vs `collections.deque`; `in_bulk()` to key query results       |
| Spring       | `List.contains` vs `HashSet`; `Collections.binarySearch` needs sorted input and returns negative on miss; `equals`/`hashCode` contract; `TreeMap` for ranges |
| Node/Express | `Array.includes`/`find` in loops vs `Set`/`Map`; `Map` keys compare by reference; `[...acc, x]` in `reduce`; `shift()` is O(n)               |
| Vapor        | Swift `Array.contains`/`first(where:)` vs `Set`/`Dictionary(uniqueKeysWithValues:)`; `Hashable` conformance; `removeFirst()` is O(n)         |
| .NET         | `List.Contains`/LINQ `First` in loops vs `HashSet`/`ToDictionary`/`ToLookup`; `List.BinarySearch` returns bitwise complement on miss; `SortedDictionary` |
| Go           | slice scans vs `map[K]struct{}`; `sort.Search` returns `len` on miss; `append` to front copies; struct keys must be comparable              |

## Example

Vulnerable shape:

```text
orders    = load_orders()                   # n items
customers = load_customers()                # m items
for order in orders:
    customer = customers.find(c -> c.id == order.customer_id)   # O(m) each
    if not seen.contains(order.sku):                            # O(n) each
        seen.append(order.sku)
result = orders.reduce((acc, o) -> [...acc, render(o, customer)], [])  # copies

prices = load_price_tiers()                 # arrives in insertion order
tier   = binary_search(prices, amount)      # wrong answer: never sorted
```

Fixed shape — one pass to build each index, constant-time lookups:

```text
customers_by_id = map_by(load_customers(), c -> c.id)   # O(m), once
seen   = new Set()
result = []
for order in orders:
    customer = customers_by_id[order.customer_id]        # O(1)
    if seen.add(order.sku):                              # O(1), returns false if present
        ...
    result.push(render(order, customer))                 # amortized O(1)

prices = sort_by(load_price_tiers(), t -> t.threshold)  # sort once, same key
tier   = binary_search(prices, amount, key = t -> t.threshold)
```

Choose by the access pattern: a hash map or set for exact-match lookups and
membership; sorted data plus binary search (or an ordered map) for ranges,
"largest value ≤ x", and ordered iteration; a heap for repeated min or max.

## Severity guidance

- **High** — a binary search or hash lookup that returns wrong results
  (unsorted input, mismatched comparator, mutated keys, broken equality),
  because it is a correctness bug that fails silently. Also high: quadratic
  work on a hot path over a collection whose size an unauthenticated or
  low-cost caller controls, since one request can pin a CPU (rate together
  with `resource-limits.md`).
- **Medium** — quadratic or worse work on a request or job path over a
  collection that grows with stored data; latency rises steadily as the
  data grows.
- **Low** — the collection is capped by pagination or a hard limit, so the
  quadratic factor is bounded, or the path is low-traffic background work.
- Do not report a linear scan over a provably tiny, fixed collection, or a
  constant-factor improvement with no plausible production cost.
