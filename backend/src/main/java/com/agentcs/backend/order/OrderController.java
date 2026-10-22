package com.agentcs.backend.order;

import com.agentcs.backend.order.dto.ModifyAddressRequest;
import com.agentcs.backend.order.dto.ModifyAddressResponse;
import com.agentcs.backend.order.dto.OrderResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/orders")
@Tag(name = "Order", description = "订单查询与未发货订单地址修改")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/search")
    @Operation(summary = "按商品名关键词搜索订单",
            description = "对应 Python tool: search_orders。当用户不记得订单号时，用商品名定位订单。")
    public List<OrderResponse> search(@RequestParam("q") String q) {
        return orderService.search(q);
    }

    @GetMapping("/{orderId}")
    @Operation(summary = "查询订单详情",
            description = "对应 Python tool: lookup_order。order_id 格式 YYYY-NNNNN。")
    public OrderResponse lookup(@PathVariable String orderId) {
        return orderService.lookup(orderId);
    }

    @PatchMapping("/{orderId}/address")
    @Operation(summary = "修改未发货订单的收货地址",
            description = "对应 Python tool: modify_order_address。已发货订单会返回 BUSINESS_BLOCKED。")
    public ModifyAddressResponse modifyAddress(
            @PathVariable String orderId,
            @Valid @RequestBody ModifyAddressRequest request
    ) {
        return orderService.modifyAddress(orderId, request.newAddress());
    }
}
