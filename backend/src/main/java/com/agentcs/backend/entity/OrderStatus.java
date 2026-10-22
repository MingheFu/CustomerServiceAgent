package com.agentcs.backend.entity;

/**
 * 订单状态。
 *
 * <p>面向 Agent 暴露的 displayName 是中文，便于直接拼到给客户看的回复里；
 * 内部业务判断（如能否改地址）一律使用枚举本身，避免字符串比较错误。
 */
public enum OrderStatus {

    PENDING_SHIPMENT("待发货"),
    SHIPPED("已发货"),
    DELIVERED("已签收"),
    CANCELLED("已取消");

    private final String displayName;

    OrderStatus(String displayName) {
        this.displayName = displayName;
    }

    public String displayName() {
        return displayName;
    }

    public boolean canModifyAddress() {
        return this == PENDING_SHIPMENT;
    }
}
