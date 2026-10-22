package com.agentcs.backend.product.dto;

import java.util.Map;

public record ProductResponse(
        String productId,
        String name,
        String price,
        String category,
        String highlights,
        Map<String, String> specs
) {
}
