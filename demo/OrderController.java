package com.shop.api;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.math.BigDecimal;
import java.util.*;

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderRepository orders;
    private final ProductRepository products;
    private final PaymentGateway gateway;
    private final CurrentUser currentUser;

    public OrderController(OrderRepository orders, ProductRepository products,
                           PaymentGateway gateway, CurrentUser currentUser) {
        this.orders = orders;
        this.products = products;
        this.gateway = gateway;
        this.currentUser = currentUser;
    }

    @GetMapping("/{orderId}")
    public Order getOrder(@PathVariable Long orderId) {
        return orders.findById(orderId).orElseThrow();
    }

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

    @PostMapping
    public Order placeOrder(@RequestBody PlaceOrderRequest req) {
        Product product = products.findById(req.productId()).orElseThrow();

        if (product.getStock() >= req.quantity()) {
            product.setStock(product.getStock() - req.quantity());
            products.save(product);

            BigDecimal amount = product.getPrice().multiply(BigDecimal.valueOf(req.quantity()));
            gateway.charge(req.card(), amount);

            Order order = new Order();
            order.setUserId(currentUser.id());
            order.setTotal(amount);
            order.setStatus("PAID");
            return orders.save(order);
        }
        throw new IllegalStateException("Out of stock");
    }

    @PostMapping("/{orderId}/pay")
    public ResponseEntity<String> pay(@PathVariable Long orderId, @RequestBody CardDetails card) {
        Order order = orders.findById(orderId).orElseThrow();
        gateway.charge(card, order.getTotal());
        order.setStatus("PAID");
        orders.save(order);
        return ResponseEntity.ok("charged");
    }
}