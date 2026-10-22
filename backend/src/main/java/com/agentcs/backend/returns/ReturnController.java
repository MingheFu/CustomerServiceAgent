package com.agentcs.backend.returns;

import com.agentcs.backend.returns.dto.CreateReturnRequestRequest;
import com.agentcs.backend.returns.dto.CreateReturnRequestResponse;
import com.agentcs.backend.returns.dto.ReturnPolicyResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/returns")
@Tag(name = "Return", description = "退换货政策查询与退货单创建")
public class ReturnController {

    private final ReturnService returnService;

    public ReturnController(ReturnService returnService) {
        this.returnService = returnService;
    }

    @GetMapping("/policies/{category}")
    @Operation(summary = "查询退换货政策",
            description = "对应 Python tool: check_return_policy。未匹配品类时回退到默认政策。")
    public ReturnPolicyResponse getPolicy(@PathVariable String category) {
        return returnService.getPolicy(category);
    }

    @PostMapping("/requests")
    @Operation(summary = "创建退货工单",
            description = "对应 Python tool: create_return_request。order_id 必须符合 YYYY-NNNNN 格式。")
    public CreateReturnRequestResponse createRequest(@Valid @RequestBody CreateReturnRequestRequest request) {
        return returnService.createRequest(request.orderId(), request.reason());
    }
}
