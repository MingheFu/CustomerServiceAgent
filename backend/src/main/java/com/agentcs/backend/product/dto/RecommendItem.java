package com.agentcs.backend.product.dto;

public record RecommendItem(
        String productId,
        String name,
        String price,
        String reason
) {
}
