package com.agentcs.backend.common.error;

/**
 * 业务错误类型。
 *
 * <p>与 Python 端 src/tools.py 中"给 LLM 看的错误"语义对齐：Agent 拿到响应后，
 * 根据 errorType 决定是 self-correct、追问用户还是转人工。
 *
 * <ul>
 *   <li>{@code VALIDATION_ERROR}  — 入参格式不合法，LLM 可自行修正参数后重试</li>
 *   <li>{@code NOT_FOUND}         — 资源不存在，需要向用户核对信息</li>
 *   <li>{@code BUSINESS_BLOCKED}  — 业务规则拒绝，例如已发货不能改地址</li>
 *   <li>{@code SYSTEM_ERROR}      — 系统内部错误，建议转人工</li>
 * </ul>
 */
public enum ErrorType {

    VALIDATION_ERROR(400),
    NOT_FOUND(404),
    BUSINESS_BLOCKED(409),
    SYSTEM_ERROR(500);

    private final int httpStatus;

    ErrorType(int httpStatus) {
        this.httpStatus = httpStatus;
    }

    public int httpStatus() {
        return httpStatus;
    }
}
