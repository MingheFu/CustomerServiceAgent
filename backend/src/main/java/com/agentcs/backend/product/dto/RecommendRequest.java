package com.agentcs.backend.product.dto;

import jakarta.validation.constraints.NotBlank;

public record RecommendRequest(
        @NotBlank(message = "use_case 不能为空")
        String useCase,

        String budget
) {
}
