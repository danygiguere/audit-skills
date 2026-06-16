# Audit: `demo/OrderController.java`

A Spring `@RestController` for orders. Authenticated (`currentUser` exists) but every handler trusts request-supplied IDs and bodies without ownership or value checks.

## Critical

**1. Mass assignment + price forgery + free "PAID" orders — `checkout` (lines 45–54)**
`@RequestBody Order order` binds the whole entity, and the total is computed from **client-supplied** `unitPrice`, `quantity`, and `discount` (lines 49, 51). An attacker sends any `unitPrice`/`discount` they like — including values that make `total` zero or negative — then the handler stamps `status="PAID"` (line 52) **without ever charging the gateway**. The bound `userId`/`id` also let the order be attributed to anyone (ownership repoint).
*Invariant:* mass assignment (allowlist) + authorization. *Fix:* decode a DTO with only `{productId, quantity}`; compute price from `Product.getPrice()` server-side; set `userId = currentUser.id()`; never trust client price/discount/status.

**2. IDOR — pay any order, charge against its total — `pay` (lines 76–83)**
`orders.findById(orderId)` with no ownership check (line 78), then `gateway.charge(card, order.getTotal())` and `setStatus("PAID")`. Any authenticated user supplies any `orderId` and mutates another principal's order. `orderId` is a sequential `Long`, so targets are enumerable.
*Invariant:* IDOR (write access to other principals' data). *Fix:* `orders.findByIdAndUserId(orderId, currentUser.id())`; treat absence as 404.

## High

**3. IDOR — read any order — `getOrder` (lines 25–28)**
`orders.findById(orderId).orElseThrow()` returns any order to any caller, no ownership scope. Sequential IDs make it enumerable; returns the raw `Order` entity (data over-exposure too).
*Fix:* scope the lookup by `currentUser.id()`; return a view DTO, not the entity.

**4. Lost update / oversold stock (check-then-act race) — `placeOrder` (lines 60–62)**
`if (stock >= qty)` then `setStock(stock - qty)` then `save` — two concurrent requests both pass the check and oversell. No lock, version, or atomic decrement.
*Invariant:* state management. *Fix:* atomic conditional update (`UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?`, check rows affected) or `@Lock(PESSIMISTIC_WRITE)`.

**5. Non-atomic stock + charge + order — `placeOrder` (lines 61–71)**
Three steps with no transaction and an external call in the middle: stock saved (62) → `gateway.charge` (65) → order saved (71). If the charge throws, stock is already gone with no order; if `orders.save` fails after a successful charge, the customer is charged with no order. External side effect sits between writes.
*Invariant:* atomicity. *Fix:* persist DB writes in one `@Transactional` unit; charge after commit (or with a compensating refund on failure).

**6. Double charge on retry/double-submit (no idempotency) — `placeOrder` (line 65) and `pay` (line 79)**
Both call `gateway.charge` with no idempotency key and no processed-state guard. A client retry, double-click, or proxy replay charges twice (and in `placeOrder`, decrements stock twice). `pay` also re-charges an already-`PAID` order — there's no `status != "PAID"` guard.
*Invariant:* idempotency. *Fix:* pass a Stripe-style idempotency key; in `pay`, no-op (return 200) if already `PAID`.

**7. Missing input validation enables negative amounts — `placeOrder` / `checkout`**
No bounds on `quantity`. A negative `quantity` in `placeOrder` passes `stock >= qty`, *increases* stock (`stock - (−n)`), and charges a **negative** amount (effectively a refund to the attacker's card). Same class of issue feeds finding #1.
*Invariant:* API contract & validation. *Fix:* `@Valid` with `@Positive` on quantity; reject non-positive amounts before charging.

## Low

**8. `orElseThrow()` → 500 instead of 404 — lines 27, 37, 58, 78**
A missing order/product raises `NoSuchElementException`, surfacing as a 500 (and leaking that an internal error occurred) rather than 404.
*Invariant:* exception handling (status mapping). *Fix:* `orElseThrow(() -> new ResponseStatusException(NOT_FOUND))`.

**9. N+1 query — `listOrders` (lines 34–39)**
`products.findById` runs once per order line, inside a loop over the user's orders — N×M queries.
*Invariant:* N+1. *Fix:* collect all `productId`s and `findAllById` once, or join in the repository query.

## Checklists applied

IDOR, authorization, mass assignment, atomicity, idempotency, state-management, API-contract-validation, data-exposure, exception-handling, N+1 — all produced findings above. **Came back clean:** CSRF (no cookie-auth evidence in scope), SSRF, injection (no query/command/path concatenation), file-handling, tenant-isolation (single-tenant), output-encoding (JSON API, no template rendering), secrets, crypto.