package com.agentcs.backend.product.dto;

import java.util.List;

public record RecommendResponse(
        String useCase,
        String budget,
        List<RecommendItem> items
) {
}
