package com.agentcs.backend.order;

import com.agentcs.backend.common.error.BusinessException;
import com.agentcs.backend.common.error.ErrorType;
import com.agentcs.backend.common.validation.OrderIdValidator;
import com.agentcs.backend.entity.OrderEntity;
import com.agentcs.backend.order.dto.ModifyAddressResponse;
import com.agentcs.backend.order.dto.OrderResponse;
import com.agentcs.backend.repository.OrderRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/**
 * 订单领域服务。
 *
 * <p>所有方法返回的 DTO 都直接给 Agent 当作工具结果使用，因此：
 * <ul>
 *   <li>错误一律以 {@link BusinessException} 抛出，附带 errorType + hint，便于 LLM 自修正</li>
 *   <li>成功响应里同时给出机器字段（枚举名）和展示字段（中文 displayName）</li>
 * </ul>
 */
@Service
public class OrderService {

    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public OrderResponse lookup(String orderId) {
        String id = OrderIdValidator.requireValid(orderId);
        OrderEntity order = orderRepository.findById(id).orElseThrow(() -> new BusinessException(
                ErrorType.NOT_FOUND,
                "订单 " + id + " 格式合法但在数据库中未命中。",
                "请向用户确认订单号是否正确，或建议其登录账户查看订单列表。"
        ));
        return toResponse(order);
    }

    @Transactional
    public ModifyAddressResponse modifyAddress(String orderId, String newAddress) {
        String id = OrderIdValidator.requireValid(orderId);

        if (newAddress == null || newAddress.trim().length() < 6) {
            throw new BusinessException(
                    ErrorType.VALIDATION_ERROR,
                    "new_address 过短或为空。",
                    "请确认收货地址至少包含省市区+详细门牌（不少于 6 个字符），修正后再次调用本工具。"
            );
        }

        OrderEntity order = orderRepository.findById(id).orElseThrow(() -> new BusinessException(
                ErrorType.NOT_FOUND,
                "订单 " + id + " 未在系统中找到，无法修改地址。",
                "请向用户确认订单号。"
        ));

        if (!order.getStatus().canModifyAddress()) {
            throw new BusinessException(
                    ErrorType.BUSINESS_BLOCKED,
                    "订单 " + id + " 当前状态为「" + order.getStatus().displayName() + "」，已发货的订单无法在线修改地址。",
                    "请告知客户联系顺丰/京东物流客服，或拨打 400-888-8888。"
            );
        }

        String trimmed = newAddress.trim();
        order.setShippingAddress(trimmed);
        order.setCarrier("顺丰速运");
        String newTrackingNo = "SF" + UUID.randomUUID().toString().replace("-", "").substring(0, 10).toUpperCase();
        order.setTrackingNo(newTrackingNo);

        return new ModifyAddressResponse(
                id,
                trimmed,
                newTrackingNo,
                "订单 " + id + " 的收货地址已更新，新运单号将在发货后生效。"
        );
    }

    public List<OrderResponse> search(String keyword) {
        if (keyword == null || keyword.trim().isBlank()) {
            throw new BusinessException(
                    ErrorType.VALIDATION_ERROR,
                    "搜索关键词为空。",
                    "请提供商品名关键词（如\"鼠标\"、\"键盘\"）。"
            );
        }
        List<OrderEntity> results = orderRepository.searchByProduct(keyword.trim());
        if (results.isEmpty()) {
            throw new BusinessException(
                    ErrorType.NOT_FOUND,
                    "未找到包含 \"" + keyword.trim() + "\" 的订单。",
                    "请尝试更通用的关键词，或建议用户提供订单号。"
            );
        }
        return results.stream().map(this::toResponse).toList();
    }

    private OrderResponse toResponse(OrderEntity order) {
        return new OrderResponse(
                order.getOrderId(),
                order.getProduct(),
                order.getPrice(),
                order.getStatus().name(),
                order.getStatus().displayName(),
                order.getOrderDate(),
                order.getCarrier(),
                order.getTrackingNo(),
                order.getShippingAddress(),
                order.getEstimatedDelivery()
        );
    }
}
