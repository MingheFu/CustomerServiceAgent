package com.agentcs.backend.common.error;

import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * 统一错误响应体。
 *
 * <p>三个字段都直接喂给 LLM：
 * <ul>
 *   <li>{@code errorType} — 机器可分类的错误码，用于路由 self-correct / NOT_FOUND 等不同处理</li>
 *   <li>{@code message}   — 简洁的事实陈述（不要太长，避免污染上下文）</li>
 *   <li>{@code hint}      — 可执行的下一步建议；validate 错误时尽量给出修正示例</li>
 * </ul>
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ErrorResponse(ErrorType errorType, String message, String hint) {

    public static ErrorResponse of(ErrorType type, String message) {
        return new ErrorResponse(type, message, null);
    }

    public static ErrorResponse of(ErrorType type, String message, String hint) {
        return new ErrorResponse(type, message, hint);
    }
}
