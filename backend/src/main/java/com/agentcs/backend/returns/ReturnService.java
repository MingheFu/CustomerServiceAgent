package com.agentcs.backend.returns;

import com.agentcs.backend.common.error.BusinessException;
import com.agentcs.backend.common.error.ErrorType;
import com.agentcs.backend.common.validation.OrderIdValidator;
import com.agentcs.backend.entity.OrderEntity;
import com.agentcs.backend.entity.ReturnPolicyEntity;
import com.agentcs.backend.entity.ReturnRequestEntity;
import com.agentcs.backend.repository.OrderRepository;
import com.agentcs.backend.repository.ReturnPolicyRepository;
import com.agentcs.backend.repository.ReturnRequestRepository;
import com.agentcs.backend.returns.dto.CreateReturnRequestResponse;
import com.agentcs.backend.returns.dto.ReturnPolicyResponse;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/**
 * 退换货领域服务。对应 Python 端的 check_return_policy / create_return_request。
 *
 * <p>未匹配到具体品类时回退到「默认」政策（与 Python 端逻辑一致），保证 LLM 总能拿到一份策略，
 * 而不是收到 NOT_FOUND 又要再追问用户。
 */
@Service
public class ReturnService {

    private static final String DEFAULT_CATEGORY = "默认";

    private static final List<String> DEFAULT_NOTES = List.of(
            "请在退货前联系客服获取退货地址",
            "保留原包装及所有配件",
            "退款将在仓库签收后 3-5 个工作日内原路返回"
    );

    private final ReturnPolicyRepository policyRepository;
    private final ReturnRequestRepository requestRepository;
    private final OrderRepository orderRepository;

    public ReturnService(
            ReturnPolicyRepository policyRepository,
            ReturnRequestRepository requestRepository,
            OrderRepository orderRepository
    ) {
        this.policyRepository = policyRepository;
        this.requestRepository = requestRepository;
        this.orderRepository = orderRepository;
    }

    public ReturnPolicyResponse getPolicy(String category) {
        if (category == null || category.isBlank()) {
            throw new BusinessException(
                    ErrorType.VALIDATION_ERROR,
                    "product_category 为空。",
                    "请提供商品类别，例如 \"键盘\"/\"鼠标\"/\"耳机\"/\"显示器\"/\"笔记本\"。"
            );
        }

        ReturnPolicyEntity policy = policyRepository.findById(category)
                .orElseGet(() -> policyRepository.findById(DEFAULT_CATEGORY)
                        .orElseThrow(() -> new BusinessException(
                                ErrorType.SYSTEM_ERROR,
                                "未配置任何退换货政策。",
                                "请联系运营导入 return_policies 数据。"
                        )));

        return new ReturnPolicyResponse(
                category,
                policy.getPeriodDays(),
                policy.getConditionText(),
                policy.getShippingResponsibility(),
                DEFAULT_NOTES
        );
    }

    @Transactional
    public CreateReturnRequestResponse createRequest(String orderId, String reason) {
        String id = OrderIdValidator.requireValid(orderId);

        if (reason == null || reason.isBlank()) {
            throw new BusinessException(
                    ErrorType.VALIDATION_ERROR,
                    "reason 为空。",
                    "请提供退货原因，例如 \"质量问题\"、\"发错货\"、\"不想要了\" 等。"
            );
        }

        OrderEntity order = orderRepository.findById(id).orElseThrow(() -> new BusinessException(
                ErrorType.NOT_FOUND,
                "订单 " + id + " 未在系统中找到。",
                "请向用户确认订单号后再次调用本工具。"
        ));

        String ticketId = "RT" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();

        ReturnRequestEntity entity = new ReturnRequestEntity();
        entity.setTicketId(ticketId);
        entity.setOrderId(id);
        entity.setReason(reason.trim());
        entity.setStatus("WAITING_RETURN_SHIPMENT");
        requestRepository.save(entity);

        return new CreateReturnRequestResponse(
                ticketId,
                id,
                order.getProduct(),
                reason.trim(),
                "WAITING_RETURN_SHIPMENT",
                "深圳市南山区科技园南区 3C 数码退货中心 (收) · 400-888-8888",
                "退货工单 " + ticketId + " 已创建，等待客户寄回。退款将在仓库签收后 3-5 个工作日内原路返回。"
        );
    }
}
