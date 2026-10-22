package com.agentcs.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "return_policies")
public class ReturnPolicyEntity {

    @Id
    @Column(name = "category", length = 64, nullable = false)
    private String category;

    @Column(name = "period_days", nullable = false)
    private int periodDays;

    @Column(name = "condition_text", length = 512, nullable = false)
    private String conditionText;

    @Column(name = "shipping_responsibility", length = 255, nullable = false)
    private String shippingResponsibility;

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public int getPeriodDays() {
        return periodDays;
    }

    public void setPeriodDays(int periodDays) {
        this.periodDays = periodDays;
    }

    public String getConditionText() {
        return conditionText;
    }

    public void setConditionText(String conditionText) {
        this.conditionText = conditionText;
    }

    public String getShippingResponsibility() {
        return shippingResponsibility;
    }

    public void setShippingResponsibility(String shippingResponsibility) {
        this.shippingResponsibility = shippingResponsibility;
    }
}
