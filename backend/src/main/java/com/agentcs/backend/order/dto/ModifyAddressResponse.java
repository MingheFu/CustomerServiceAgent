package com.agentcs.backend.order.dto;

/**
 * 修改收货地址响应。
 *
 * <p>{@code newTrackingNo} 为模拟值（实际生产应等真实发货系统回填）；
 * {@code message} 是面向客户的中文一句话，方便 Agent 直接复述。
 */
public record ModifyAddressResponse(
        String orderId,
        String newAddress,
        String newTrackingNo,
        String message
) {
}
