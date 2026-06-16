// Deliberately vulnerable sample — a Spring Boot ecommerce controller.
// Ten bugs a pattern-based scanner (SonarQube, Semgrep, CodeQL) can't find,
// because each needs reasoning about ownership, money, concurrency, or retries —
// not a grep-able syntax pattern. Every route below looks idiomatic and would
// pass a linter clean:
//    1. IDOR / authorization  — GET /{orderId} returns any order by id, no owner check
//    2. Mass assignment       — checkout binds the whole request body onto the order, so a
//                                client sets userId / discount / status; and because the body
//                                is trusted wholesale the total is summed from the client's
//                                unitPrice (price tampering) instead of the catalog price
//    3. Atomicity             — order save + stock decrement + payment are three separate
//                                writes with no transaction and no compensation
//    4. Idempotency           — /pay has no idempotency key; a retry charges the card twice
//    5. Race condition        — stock is checked then decremented in two steps; two
//                                concurrent orders both pass the check and oversell
//    6. N+1 queries           — listing orders queries the product table once per line item
//    7. Data exposure         — GET /{orderId} returns the whole Order entity: addresses,
//                                every line, internal fields — not a view DTO
//    8. Missing validation    — no @Valid, no bounds; a negative quantity flips the charge
//                                into a credit and mints money
//    9. Wrong HTTP status     — orElseThrow / IllegalStateException surface as 500 where
//                                the condition means 404 (not found) or 409 (out of stock)
//   10. No observability      — no logging on any failure path; the double-charge, the
//                                oversell, and the orphaned stock are invisible in prod
//
// Run `/audit demo/OrderControllerWithExplanations.java` and the audit should flag all ten.
// This file is a fixture, not real code — the repositories and gateway are sketched, not wired.

package com.shop.api;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.math.BigDecimal;
import java.util.*;

@RestController
@RequestMapping("/api/orders")
public class OrderControllerWithExplanations {

    private final OrderRepository orders;
    private final ProductRepository products;
    private final PaymentGateway gateway;       // gateway.charge(card, amount) — external call
    private final CurrentUser currentUser;       // currentUser.id() — the authenticated principal

    public OrderControllerWithExplanations(OrderRepository orders, ProductRepository products,
                                           PaymentGateway gateway, CurrentUser currentUser) {
        this.orders = orders;
        this.products = products;
        this.gateway = gateway;
        this.currentUser = currentUser;
    }

    // 1. IDOR: the order is loaded by the path id alone. The caller is never checked
    //    as its owner, so any logged-in user can read anyone's order — addresses,
    //    line items, totals — just by incrementing the id.
    // 7. Data exposure: the whole Order entity is returned, not a view DTO — every
    //    column the model has (shipping address, internal status, audit fields) ships
    //    to the client. This compounds the IDOR above.
    // 9. Wrong HTTP status: orElseThrow throws NoSuchElementException, which surfaces
    //    as a 500. A missing order is a 404 — the status should say "not found", not
    //    "the server broke".
    @GetMapping("/{orderId}")
    public Order getOrder(@PathVariable Long orderId) {
        return orders.findById(orderId).orElseThrow();
    }

    // 6. N+1: one query loads the user's orders, then the loop issues another query
    //    per line item to fetch the product name. A user with 50 orders of 5 items
    //    each fans out into 250 extra round-trips on a single page load.
    @GetMapping
    public List<OrderView> listOrders() {
        List<Order> mine = orders.findByUserId(currentUser.id());
        List<OrderView> views = new ArrayList<>();
        for (Order order : mine) {
            List<String> names = new ArrayList<>();
            for (OrderLine line : order.getLines()) {
                Product p = products.findById(line.getProductId()).orElseThrow();
                names.add(p.getName());
            }
            views.add(new OrderView(order.getId(), order.getTotal(), names));
        }
        return views;
    }

    // 2. Mass assignment (price tampering is the financial face of it): the request body
    //    is bound straight onto the Order entity, so the client controls fields it should
    //    never set — userId, status, discount — and the same wholesale trust means the
    //    total is summed from each line's client-supplied unitPrice instead of the catalog
    //    price, so a buyer can order a $2000 laptop for $1.00 by editing the JSON.
    // 8. Missing validation: the body has no @Valid and no bounds. A negative quantity
    //    makes unitPrice * quantity negative, so the total goes negative — the "charge"
    //    becomes a credit and the order mints money.
    @PostMapping("/checkout")
    public Order checkout(@RequestBody Order order) {
        BigDecimal total = BigDecimal.ZERO;
        for (OrderLine line : order.getLines()) {
            total = total.add(line.getUnitPrice().multiply(BigDecimal.valueOf(line.getQuantity())));
        }
        order.setTotal(total.subtract(order.getDiscount()));
        order.setStatus("PAID");
        return orders.save(order);
    }

    // 3. Atomicity + 5. Race condition: three independent writes with no @Transactional.
    //    Stock is checked then decremented in separate statements (two concurrent orders
    //    both pass the check and oversell), and if gateway.charge throws after the stock
    //    is already decremented, the order is never saved but the inventory stays wrong —
    //    no rollback, no compensation.
    @PostMapping
    public Order placeOrder(@RequestBody PlaceOrderRequest req) {
        Product product = products.findById(req.productId()).orElseThrow();

        if (product.getStock() >= req.quantity()) {
            product.setStock(product.getStock() - req.quantity());
            products.save(product);

            BigDecimal amount = product.getPrice().multiply(BigDecimal.valueOf(req.quantity()));
            gateway.charge(req.card(), amount);          // external call — may fail or time out

            Order order = new Order();
            order.setUserId(currentUser.id());
            order.setTotal(amount);
            order.setStatus("PAID");
            return orders.save(order);
        }
        // 9. Wrong HTTP status: "out of stock" is a 409 Conflict the client can act on,
        //    but a bare IllegalStateException surfaces as an opaque 500.
        // 10. No observability: the charge can fail after stock is decremented (#3), the
        //     stock check can lose a race (#5), and none of it is logged — the orphaned
        //     inventory and the failed payment leave no trace to debug from.
        throw new IllegalStateException("Out of stock");
    }

    // 4. Idempotency: a double-click, an impatient retry, or a gateway timeout-then-retry
    //    re-runs this handler and charges the card a second time. There is no idempotency
    //    key, no check that this order was already paid, nothing to make the retry a no-op.
    @PostMapping("/{orderId}/pay")
    public ResponseEntity<String> pay(@PathVariable Long orderId, @RequestBody CardDetails card) {
        Order order = orders.findById(orderId).orElseThrow();
        gateway.charge(card, order.getTotal());
        order.setStatus("PAID");
        orders.save(order);
        return ResponseEntity.ok("charged");
    }
}