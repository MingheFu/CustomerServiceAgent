package com.agentcs.backend.repository;

import com.agentcs.backend.entity.SupportTicketEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SupportTicketRepository extends JpaRepository<SupportTicketEntity, String> {
}
