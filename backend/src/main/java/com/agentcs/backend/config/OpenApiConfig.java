package com.agentcs.backend.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI agentBackendOpenApi() {
        return new OpenAPI().info(new Info()
                .title("Agent Customer Service · Backend API")
                .version("0.1.0")
                .description("""
                        Java 业务与工具层。Python 端 LangGraph Agent 通过 HTTP 调用本服务作为工具：

                        - /orders        — 对应 lookup_order / modify_order_address
                        - /returns       — 对应 check_return_policy / create_return_request
                        - /products      — 对应 search_product_specs / get_product_recommendation
                        - /tickets       — 对应 escalate_to_human (HITL 兜底)

                        错误响应统一为 { errorType, message, hint }，与 Agent 端 self-correct 协议对齐。
                        """)
                .contact(new Contact().name("agent-customer-service"))
                .license(new License().name("Internal")));
    }
}
