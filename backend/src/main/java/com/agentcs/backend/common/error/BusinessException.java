package com.agentcs.backend.common.error;

/**
 * 业务层抛出的受控异常。
 *
 * <p>Service 只关心"出了什么业务错"，由 {@link GlobalExceptionHandler}
 * 统一把它翻译成 HTTP 状态 + {@link ErrorResponse}。
 */
public class BusinessException extends RuntimeException {

    private final ErrorType errorType;
    private final String hint;

    public BusinessException(ErrorType errorType, String message) {
        this(errorType, message, null);
    }

    public BusinessException(ErrorType errorType, String message, String hint) {
        super(message);
        this.errorType = errorType;
        this.hint = hint;
    }

    public ErrorType errorType() {
        return errorType;
    }

    public String hint() {
        return hint;
    }
}
