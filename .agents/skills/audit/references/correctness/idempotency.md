# Idempotency

## Invariant

Any handler that can run twice — webhook redelivery, queue retry, client
retry, double submit — produces the same outcome as running once. The second
execution is detected and skipped, or the operation is shaped so that
repeating it changes nothing.

## Does not apply when

- The operation is naturally idempotent: setting a field to an absolute
  value, deleting by ID, an UPSERT keyed on a stable identifier.
- The handler can provably run at most once (no retries, no redelivery, no
  user-facing submit) — rare, and worth questioning.

## Why it happens

The happy path is written first and duplicates never appear in development.
Webhook providers, queue brokers, and HTTP clients all retry on timeout —
including timeouts where the first attempt actually succeeded — so
"run twice" is the normal failure mode, not an edge case. Developers assume
the network delivers exactly once; every layer in practice delivers at
least once.

## Detection smells

- A webhook handler that processes the payload without first checking a
  stored event/delivery ID for "already seen".
- A charge, refund, or transfer call to a payment provider with no
  idempotency key, inside a handler that can be retried.
- A counter or balance incremented (`+= amount`) by a handler that a retry
  or redelivery would re-execute.
- A plain INSERT for a record that must be unique per external event, order,
  or user-action — where an UPSERT or a unique constraint should absorb the
  duplicate.
- A form submit or API endpoint that creates a resource with no
  client-supplied request key and no server-side dedupe — double-click
  creates two.
- Side effects (email, shipment, provisioning) keyed off "handler ran"
  rather than off a state transition that can only happen once.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where dedupe usually lives                                                                                                               |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `create_or_find_by` on a unique index; `Stripe-Idempotency-Key`; processed-event table                                                   |
| Laravel      | `firstOrCreate`/`upsert` on a unique column; `WithoutOverlapping`/`ShouldBeUnique` jobs                                                  |
| Django       | `get_or_create`/`update_or_create`; `unique` constraints; idempotency-key middleware                                                     |
| Spring       | unique constraints + `DataIntegrityViolationException` catch; idempotent consumer table                                                  |
| Node/Express | `INSERT ... ON CONFLICT DO NOTHING`; idempotency-key header checked against a store                                                      |
| Vapor        | `.unique(on:)` in Fluent migrations + catching the constraint violation; idempotency-key stores and webhook event tables are hand-rolled |
| .NET         | unique indexes + catching `DbUpdateException`; idempotency keys hand-rolled or middleware; Polly retries make duplicates likely          |
| Go           | unique index + `ON CONFLICT DO NOTHING`, check rows affected; idempotency-key tables hand-rolled                                         |

## Example

Vulnerable shape:

```text
handler payment_webhook(event):
    order = db.orders.find(event.order_id)
    order.balance_paid += event.amount      # redelivery pays twice
    email.send_receipt(order)               # redelivery emails twice
```

Fixed shape — the event ID is recorded atomically before processing, and the
duplicate is detected by a unique constraint, not an in-memory check:

```text
handler payment_webhook(event):
    inserted = db.processed_events.insert_ignore(id = event.id)
    if not inserted: respond 200            # duplicate -> acknowledge, do nothing
    db.transaction:
        order = db.orders.find(event.order_id)
        order.mark_paid(event.amount)       # absolute state, not increment
    on_commit: email.send_receipt(order)
```

## Severity guidance

- **High** — duplicates move money or inventory: double charges, double
  refunds, double shipments, balances drifting on redelivery.
- **Medium** — duplicate rows or double-fired side effects (two emails, two
  provisioned resources) that require cleanup but do not corrupt
  authoritative totals.
- **Low** — duplicates are cosmetic (repeated log entries, re-rendered
  notifications) and self-correcting.
- Handlers reachable by external retry loops (payment providers, webhook
  senders) rate one level higher than purely internal paths.

## Remediation

See `../remediation/async-patterns.md` — idempotency keys, processed-event
tables, unique constraints with UPSERT, and absolute-state writes.
