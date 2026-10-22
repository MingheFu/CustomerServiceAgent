package com.agentcs.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "support_tickets")
public class SupportTicketEntity {

    @Id
    @Column(name = "ticket_id", length = 32, nullable = false)
    private String ticketId;

    @Column(name = "issue_summary", length = 2000, nullable = false)
    private String issueSummary;

    @Column(name = "attempted_solutions", length = 2000)
    private String attemptedSolutions;

    @Column(name = "urgency", length = 16, nullable = false)
    private String urgency;

    @Column(name = "preferred_contact", length = 255)
    private String preferredContact;

    @Column(name = "status", length = 32, nullable = false)
    private String status;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
    }

    public String getTicketId() {
        return ticketId;
    }

    public void setTicketId(String ticketId) {
        this.ticketId = ticketId;
    }

    public String getIssueSummary() {
        return issueSummary;
    }

    public void setIssueSummary(String issueSummary) {
        this.issueSummary = issueSummary;
    }

    public String getAttemptedSolutions() {
        return attemptedSolutions;
    }

    public void setAttemptedSolutions(String attemptedSolutions) {
        this.attemptedSolutions = attemptedSolutions;
    }

    public String getUrgency() {
        return urgency;
    }

    public void setUrgency(String urgency) {
        this.urgency = urgency;
    }

    public String getPreferredContact() {
        return preferredContact;
    }

    public void setPreferredContact(String preferredContact) {
        this.preferredContact = preferredContact;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
