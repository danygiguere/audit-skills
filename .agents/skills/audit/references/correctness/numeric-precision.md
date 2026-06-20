# Numeric & Money Precision

## Invariant

Money and any quantity that must be exact is represented and computed with a
decimal or integer type, never binary floating point. Rounding happens once,
at a defined boundary, with an explicit rounding mode and scale. Arithmetic
on values of different units or currencies is forbidden until they are
converted, and every operation that can overflow, truncate, or divide by
zero is bounded or guarded.

## Does not apply when

- The value is inherently approximate and never compared for equality or
  summed for an audited total (sensor readings, ratios driving a UI bar,
  ML features) — float is the correct tool there.

## Why it happens

`float`/`double` are the default numeric types in most languages, so money
lands in them by reflex; `0.1 + 0.2 != 0.3` stays invisible until totals
drift by a cent under load. Rounding gets sprinkled at display time in
several places instead of once at a boundary, so two code paths disagree.
Multiplying a price by a quantity, or summing a column, silently overflows a
32-bit integer long after the code looked correct in tests. And unit
mismatches — cents vs dollars, milliseconds vs seconds, percent vs fraction —
read fine because the types are identical; only the magnitude is wrong.

## Detection smells

- Money or a financial total stored or computed in `float`/`double`/`real`
  (or a JS `number`) instead of a decimal type or integer minor units.
- Equality or `<`/`>` comparison on floating-point results, or using a float
  as a map key, accumulator, or loop bound.
- Rounding applied ad hoc at multiple call sites, or with no explicit mode —
  the language default may be round-half-even when the business wants
  round-half-up, or vice versa.
- A division without a defined scale or remainder handling — splitting a
  charge across N items where the pennies don't sum back to the total.
- Multiplication of two input-controlled quantities, or a running sum over an
  unbounded collection, with no overflow guard on a fixed-width integer.
- A unit or currency carried only by variable name (`amountCents`,
  `priceUsd`) and never by the type — two such values added directly.
- Parsing a decimal string straight into a float (`parseFloat`,
  `Double(...)`) before it ever reaches a decimal type.
- A percentage or tax rate applied as `x * 0.0825` then re-rounded downstream,
  compounding rounding error across line items.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Exact type vs the trap                                                                                          |
|--------------|-----------------------------------------------------------------------------------------------------------------|
| Rails        | `BigDecimal` / `decimal` columns and `money-rails` vs `float`/`:float` columns; `round(2, half: :up)`           |
| Laravel      | `decimal:2` casts, `bcmath`, `brick/money` vs `(float)` casts; `bcadd`/`bcmul` instead of `+`/`*`               |
| Django       | `DecimalField` + `decimal.Decimal` vs `FloatField`; set `ROUND_HALF_UP` explicitly, never compute money in float |
| Spring       | `BigDecimal` with a stated `RoundingMode`/scale vs `double`; `JOptional`/`Money` types; `compareTo` not `==`     |
| Node/Express | integer minor units or `decimal.js`/`dinero.js` vs JS `number`; never `parseFloat` money; `Number.isSafeInteger` |
| Vapor        | `Decimal`/`NSDecimalNumber` vs `Double`; store cents as `Int`; explicit `NSDecimalNumberHandler` rounding        |
| .NET         | `decimal` (128-bit) vs `double`/`float`; `Math.Round(x, 2, MidpointRounding.AwayFromZero)`; `checked {}` blocks  |
| Go           | `shopspring/decimal` or integer cents vs `float64`; `math/big.Rat`; watch silent `int32`/`int64` overflow        |

## Example

Vulnerable shape — float money, implicit rounding, unguarded split:

```text
handler checkout(cart):
    total = 0.0
    for item in cart.items:
        total += item.price * item.qty          # float drift accumulates
    tax = total * 0.0825                          # more float
    charge(round(total + tax))                    # default mode, rounded late
    per_person = total / cart.party_size          # pennies vanish on division
```

Fixed shape — decimal/minor units, one rounding boundary, remainder handled:

```text
handler checkout(cart):
    total_cents = 0                               # integer minor units
    for item in cart.items:
        total_cents += item.price_cents * item.qty
    tax_cents = round_half_up(total_cents * Decimal("0.0825"))
    grand = total_cents + tax_cents
    charge(grand)                                 # already exact, integer
    base, remainder = divmod(grand, cart.party_size)
    shares = [base + (1 if i < remainder else 0)  # remainder distributed
              for i in range(cart.party_size)]     # shares sum back to grand
```

## Severity guidance

- **Critical** — money or balances computed in float on a path that charges,
  refunds, or settles, where drift produces a real financial discrepancy, or
  an overflow that lets a total wrap to a smaller (or negative) charge.
- **High** — rounding inconsistency between two paths (e.g. invoice vs
  ledger) that reconciliation will flag, or a split/proration whose parts do
  not sum to the whole.
- **Medium** — float used for a quantity later compared for equality or
  summed into an audited report, where error is bounded but observable.
- **Low** — approximate value where exactness is not required but the type
  choice is fragile against future use; flag as a hardening note.
