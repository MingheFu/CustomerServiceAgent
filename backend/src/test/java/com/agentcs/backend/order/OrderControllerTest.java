package com.agentcs.backend.order;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 订单接口 sanity test。
 *
 * <p>使用 H2 + MODE=MySQL，Flyway 跑同一套迁移脚本+种子数据，验证 Agent 端
 * 真正关心的几条路径：
 * <ul>
 *   <li>正常查询返回完整字段</li>
 *   <li>格式不合法 → VALIDATION_ERROR + hint，便于 LLM 自修正</li>
 *   <li>格式合法但不存在 → NOT_FOUND</li>
 *   <li>已发货订单改地址 → BUSINESS_BLOCKED</li>
 *   <li>未发货订单改地址 → 成功并返回新运单号</li>
 * </ul>
 *
 * <p>MockMvc 不应用 server.servlet.context-path，所以这里的路径不带 /api 前缀。
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class OrderControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void lookup_existing_order_returns_full_payload() throws Exception {
        mockMvc.perform(get("/orders/2024-78901"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.orderId").value("2024-78901"))
                .andExpect(jsonPath("$.status").value("SHIPPED"))
                .andExpect(jsonPath("$.statusDisplay").value("已发货"))
                .andExpect(jsonPath("$.carrier").value("顺丰速运"));
    }

    @Test
    void lookup_with_pure_5digit_id_returns_validation_error_with_hint() throws Exception {
        mockMvc.perform(get("/orders/78901"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorType").value("VALIDATION_ERROR"))
                .andExpect(jsonPath("$.hint").exists());
    }

    @Test
    void lookup_with_valid_format_but_missing_returns_not_found() throws Exception {
        mockMvc.perform(get("/orders/9999-99999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.errorType").value("NOT_FOUND"));
    }

    @Test
    void modify_address_on_shipped_order_returns_business_blocked() throws Exception {
        String body = """
                { "newAddress": "广东省深圳市南山区科技园南区 88 号" }
                """;
        mockMvc.perform(patch("/orders/2024-78901/address")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.errorType").value("BUSINESS_BLOCKED"));
    }

    @Test
    void modify_address_on_pending_order_succeeds_and_returns_new_tracking_no() throws Exception {
        String body = """
                { "newAddress": "广东省深圳市南山区科技园南区 88 号" }
                """;
        mockMvc.perform(patch("/orders/2024-78902/address")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.orderId").value("2024-78902"))
                .andExpect(jsonPath("$.newAddress").value("广东省深圳市南山区科技园南区 88 号"))
                .andExpect(jsonPath("$.newTrackingNo").exists());
    }

    @Test
    void modify_address_with_short_value_returns_validation_error() throws Exception {
        String body = """
                { "newAddress": "短地址" }
                """;
        mockMvc.perform(patch("/orders/2024-78902/address")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorType").value("VALIDATION_ERROR"));
    }
}
