package com.agentcs.backend.returns.dto;

public record CreateReturnRequestResponse(
        String ticketId,
        String orderId,
        String productName,
        String reason,
        String status,
        String returnShippingAddress,
        String message
) {
}
