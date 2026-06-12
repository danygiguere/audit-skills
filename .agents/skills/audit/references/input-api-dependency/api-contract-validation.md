# API contract & validation

## Invariant

Every input crossing a trust boundary — request bodies, query and path
parameters, headers, webhook payloads — is validated server-side for type,
bounds, format, and allowed fields before use. Unknown fields are rejected
or explicitly ignored, never silently bound to internal state. Values the
server can derive (prices, totals, roles, ownership) are computed
server-side, never accepted from the client.

## Why it happens

The client already validates, so server-side checks feel redundant — until
a caller skips the client. Mass-assignment-style binding maps whole payloads
onto models in one call, so any field a model has becomes writable unless
someone remembers the allowlist. Sending the price or total from the UI is
convenient because the UI already displayed it. Edge cases (negative
numbers, absent vs null, huge values) pass happy-path testing and surface
only under adversarial input.

## Detection smells

- A handler binds the raw request body onto a model or update call without
  a field allowlist — any column (role, owner_id, verified flag) becomes
  settable.
- Monetary or privilege-bearing values (price, discount, total, role, plan,
  quantity-times-price) read from the request instead of recomputed from
  server-side records.
- Numeric inputs used without bounds: negative quantities flipping a charge
  into a credit, zero page sizes, huge limits driving unbounded work.
- Validation rules present in the front-end or a client SDK with no
  matching server-side enforcement on the same fields.
- Code that treats absent, null, and empty-string identically (or worse,
  differently by accident) — e.g., a partial update where absent should
  mean "unchanged" but null clears the field, with no explicit handling.
- String inputs without length or format constraints feeding storage,
  rendering, or downstream parsers.
- Validation-error responses that echo internals — model/class names, raw
  exception text, query fragments — instead of a stable, uniform error
  shape.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Boundary validation idiom                                                                                                               |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | strong parameters (`params.require(...).permit(...)`); model validations                                                                |
| Laravel      | Form Request rules; `$request->validated()` vs `$request->all()` into `fill()`                                                          |
| Django       | DRF serializers with explicit `fields`; `serializer.validated_data`                                                                     |
| Spring       | Bean Validation (`@Valid`, constraint annotations); dedicated request DTOs                                                              |
| Node/Express | schema validation middleware (zod/Joi-style) with strict/strip-unknown enabled                                                          |
| Vapor        | `Validatable` (`try User.Create.validate(content: req)`); Codable DTOs give types/bounds — note Codable ignores unknown fields silently |
| .NET         | model binding + DataAnnotations/FluentValidation; `[ApiController]` auto-400s on invalid `ModelState`; records as DTOs                  |
| Go           | decode into request structs + go-playground/validator tags; `DisallowUnknownFields()` on the json.Decoder                               |

## Example

Vulnerable shape:

```text
handler create_order(request):
    order = Order.create(request.body)        # whole payload bound: role? price?
    charge(request.body.total)                # client-computed money
```

Fixed shape — explicit schema, server-derived values, bounded numbers:

```text
schema CreateOrder:
    product_id : id, must exist
    quantity   : integer, 1..100
    reject unknown fields                      # or strip, but decide explicitly

handler create_order(request):
    input = validate(CreateOrder, request.body)   # 422 with uniform error shape
    price = db.products.find(input.product_id).price
    order = Order.create(product_id = input.product_id,
                         quantity   = input.quantity,
                         total      = price * input.quantity)  # server-computed
    charge(order.total)
```

## Severity guidance

- **Critical** — client-supplied values controlling money, roles, or
  ownership are honored (price tampering, mass-assigning `role`/`is_admin`).
- **High** — unknown-field binding onto models with sensitive columns, or
  missing bounds enabling negative-value abuse on financial paths.
- **Medium** — validation existing only client-side for non-sensitive
  fields, absent/null/empty confusion corrupting data, or error responses
  leaking internals.
- **Low** — missing length/format constraints with no identified downstream
  consequence; inconsistent error shapes alone.
- Severity follows what the unvalidated field reaches, not the missing
  check itself — trace the field to its sink before rating.
