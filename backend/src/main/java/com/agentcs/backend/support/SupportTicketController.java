package com.agentcs.backend.support;

import com.agentcs.backend.support.dto.CreateTicketRequest;
import com.agentcs.backend.support.dto.TicketResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/tickets")
@Tag(name = "SupportTicket", description = "人工客服工单 (HITL 兜底)")
public class SupportTicketController {

    private final SupportTicketService service;

    public SupportTicketController(SupportTicketService service) {
        this.service = service;
    }

    @PostMapping
    @Operation(summary = "创建人工客服工单",
            description = "对应 Python tool: escalate_to_human。urgency 取值: low / normal / high。")
    public ResponseEntity<TicketResponse> create(@Valid @RequestBody CreateTicketRequest request) {
        TicketResponse body = service.createTicket(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(body);
    }

    @GetMapping("/{ticketId}")
    @Operation(summary = "查询工单详情")
    public TicketResponse get(@PathVariable String ticketId) {
        return service.getTicket(ticketId);
    }
}
