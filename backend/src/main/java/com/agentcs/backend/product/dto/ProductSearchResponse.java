package com.agentcs.backend.product.dto;

import java.util.List;

public record ProductSearchResponse(
        String query,
        int count,
        List<ProductResponse> results,
        String hintIfEmpty
) {
}
