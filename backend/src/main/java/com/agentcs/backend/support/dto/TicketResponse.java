package com.agentcs.backend.support.dto;

import java.time.Instant;

public record TicketResponse(
        String ticketId,
        String issueSummary,
        String attemptedSolutions,
        String urgency,
        String preferredContact,
        String status,
        Instant createdAt,
        String message
) {
}
