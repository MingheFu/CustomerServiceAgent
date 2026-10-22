package com.agentcs.backend.support.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateTicketRequest(
        @NotBlank(message = "issue_summary 不能为空")
        @Size(max = 2000, message = "issue_summary 长度不能超过 2000 字符")
        String issueSummary,

        @NotBlank(message = "attempted_solutions 不能为空")
        @Size(max = 2000, message = "attempted_solutions 长度不能超过 2000 字符")
        String attemptedSolutions,

        String urgency,

        String preferredContact
) {
}
