package com.agentcs.backend.order.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 修改收货地址请求。
 *
 * <p>地址至少 6 个字符，与 Python {@code modify_order_address} 的入参校验一致；
 * 校验失败由 {@code GlobalExceptionHandler} 翻译成 VALIDATION_ERROR + hint。
 */
public record ModifyAddressRequest(
        @NotBlank(message = "new_address 不能为空")
        @Size(min = 6, max = 512, message = "new_address 至少需要 6 个字符（省市区+详细门牌）")
        String newAddress
) {
}
