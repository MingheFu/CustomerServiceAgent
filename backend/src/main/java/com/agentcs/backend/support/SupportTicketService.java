package com.agentcs.backend.support;

import com.agentcs.backend.common.error.BusinessException;
import com.agentcs.backend.common.error.ErrorType;
import com.agentcs.backend.entity.SupportTicketEntity;
import com.agentcs.backend.repository.SupportTicketRepository;
import com.agentcs.backend.support.dto.CreateTicketRequest;
import com.agentcs.backend.support.dto.TicketResponse;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;

/**
 * 人工客服工单服务。对应 Python 端 hitl.py 的 escalate_to_human。
 *
 * <p>真实生产环境里这里应该对接 Zendesk / Salesforce / 飞书；当前用 MySQL 自存，
 * 接口契约保持稳定，未来替换实现不影响 Agent 调用方。
 */
@Service
public class SupportTicketService {

    private static final Set<String> VALID_URGENCY = new LinkedHashSet<>(Set.of("low", "normal", "high"));

    private final SupportTicketRepository repository;

    public SupportTicketService(SupportTicketRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public TicketResponse createTicket(CreateTicketRequest req) {
        String urgency = (req.urgency() == null || req.urgency().isBlank())
                ? "normal"
                : req.urgency().trim().toLowerCase();

        if (!VALID_URGENCY.contains(urgency)) {
            throw new BusinessException(
                    ErrorType.VALIDATION_ERROR,
                    "urgency 取值非法: \"" + req.urgency() + "\"。",
                    "可选值: " + String.join(" / ", VALID_URGENCY) + "。请在下次调用时使用其中之一。"
            );
        }

        String ticketId = "CS" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();

        SupportTicketEntity entity = new SupportTicketEntity();
        entity.setTicketId(ticketId);
        entity.setIssueSummary(req.issueSummary());
        entity.setAttemptedSolutions(req.attemptedSolutions());
        entity.setUrgency(urgency);
        entity.setPreferredContact(emptyToNull(req.preferredContact()));
        entity.setStatus("WAITING_AGENT");
        repository.save(entity);

        return new TicketResponse(
                ticketId,
                req.issueSummary(),
                req.attemptedSolutions(),
                urgency,
                emptyToNull(req.preferredContact()),
                "WAITING_AGENT",
                entity.getCreatedAt(),
                "人工客服工单 " + ticketId + " 已创建，预计 30 分钟内通过电话/邮件回复。"
        );
    }

    public TicketResponse getTicket(String ticketId) {
        if (ticketId == null || ticketId.isBlank()) {
            throw new BusinessException(
                    ErrorType.VALIDATION_ERROR,
                    "ticket_id 为空。",
                    "请提供形如 \"CS12345678\" 的工单编号。"
            );
        }
        SupportTicketEntity entity = repository.findById(ticketId.trim()).orElseThrow(() -> new BusinessException(
                ErrorType.NOT_FOUND,
                "工单 " + ticketId + " 不存在。",
                "请确认工单号是否正确。"
        ));
        return new TicketResponse(
                entity.getTicketId(),
                entity.getIssueSummary(),
                entity.getAttemptedSolutions(),
                entity.getUrgency(),
                entity.getPreferredContact(),
                entity.getStatus(),
                entity.getCreatedAt(),
                null
        );
    }

    private static String emptyToNull(String s) {
        return (s == null || s.isBlank()) ? null : s.trim();
    }
}
