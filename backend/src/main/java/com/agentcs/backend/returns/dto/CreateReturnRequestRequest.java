package com.agentcs.backend.returns.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateReturnRequestRequest(
        @NotBlank(message = "order_id 不能为空")
        String orderId,

        @NotBlank(message = "reason 不能为空")
        @Size(max = 255, message = "reason 长度不能超过 255 字符")
        String reason
) {
}
