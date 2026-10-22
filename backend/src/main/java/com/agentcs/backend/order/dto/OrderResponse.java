package com.agentcs.backend.order.dto;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 订单查询响应。
 *
 * <p>{@code status} 是枚举字面量（机器友好），{@code statusDisplay} 是中文展示名，
 * 便于 Agent 在生成回复时直接拼到给客户看的句子里。
 */
public record OrderResponse(
        String orderId,
        String product,
        BigDecimal price,
        String status,
        String statusDisplay,
        LocalDate orderDate,
        String carrier,
        String trackingNo,
        String shippingAddress,
        LocalDate estimatedDelivery
) {
}
