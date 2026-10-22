package com.agentcs.backend.common.validation;

import com.agentcs.backend.common.error.BusinessException;
import com.agentcs.backend.common.error.ErrorType;

import java.util.regex.Pattern;

/**
 * 订单号格式校验。
 *
 * <p>所有吃 order_id 的接口都先走这里，与 Python 端 {@code _validate_order_id}
 * 的行为对齐：非法时不查 DB，直接抛 {@link BusinessException}，由全局异常处理器
 * 翻译成 {@link ErrorType#VALIDATION_ERROR}。hint 文案设计成"LLM 一眼能改的修正建议"。
 */
public final class OrderIdValidator {

    public static final String FORMAT = "YYYY-NNNNN";
    public static final String EXAMPLE = "2024-78901";
    public static final Pattern PATTERN = Pattern.compile("^\\d{4}-\\d{5}$");

    /** Hint 兜底使用的默认年份（与 Python 端保持一致，避免 LLM 凭空猜年份）。 */
    private static final String FALLBACK_YEAR = "2024";

    private OrderIdValidator() {
    }

    /** 校验通过则返回去除首尾空格后的订单号；否则抛 {@link BusinessException}。 */
    public static String requireValid(String orderId) {
        if (orderId == null || orderId.isBlank()) {
            throw new BusinessException(
                    ErrorType.VALIDATION_ERROR,
                    "order_id 为空或不是字符串。",
                    "期望格式 " + FORMAT + " (例如 \"" + EXAMPLE + "\")。"
                            + "请向用户确认完整订单号后再次调用本工具。"
            );
        }

        String cleaned = orderId.trim();
        if (PATTERN.matcher(cleaned).matches()) {
            return cleaned;
        }

        throw new BusinessException(
                ErrorType.VALIDATION_ERROR,
                "order_id=\"" + cleaned + "\" 不符合格式 ^\\d{4}-\\d{5}$。",
                buildHint(cleaned)
        );
    }

    private static String buildHint(String cleaned) {
        boolean allDigits = cleaned.chars().allMatch(Character::isDigit);

        if (allDigits && cleaned.length() == 5) {
            return "你传入了纯数字 \"" + cleaned + "\"，疑似缺少年份前缀。"
                    + "请尝试改用 \"" + FALLBACK_YEAR + "-" + cleaned + "\"；"
                    + "若用户提到了其他下单年份，请用该年份替换。";
        }
        if (allDigits) {
            return "订单号是纯数字，格式不对。完整订单号包含 4 位年份和 5 位序号，中间用短横线分隔。";
        }
        if (!cleaned.contains("-")) {
            return "订单号缺少短横线分隔符。完整格式: 4 位年份-5 位序号 (例如 \"" + EXAMPLE + "\")。";
        }
        long dashes = cleaned.chars().filter(c -> c == '-').count();
        if (dashes > 1) {
            return "订单号只应包含一个短横线，请检查是否多拼了字符。";
        }
        return "期望形如 \"" + EXAMPLE + "\"。请基于上下文修正参数后再次调用本工具。";
    }
}
