package com.agentcs.backend.returns.dto;

import java.util.List;

public record ReturnPolicyResponse(
        String category,
        int periodDays,
        String conditionText,
        String shippingResponsibility,
        List<String> notes
) {
}
