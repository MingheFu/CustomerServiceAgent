package com.agentcs.backend.health;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

/**
 * 轻量健康检查。
 *
 * <p>Spring Boot Actuator 也能做这件事，但当前阶段不引依赖，先用一个简单的 endpoint
 * 给 Python 端启动时探活/重试用。
 */
@RestController
@RequestMapping("/health")
@Tag(name = "Health", description = "服务存活探针")
public class HealthController {

    @GetMapping
    @Operation(summary = "存活探针", description = "始终返回 200; 用于 Python 端启动检测后端是否就绪。")
    public Map<String, Object> health() {
        return Map.of(
                "status", "UP",
                "service", "agent-customer-service-backend",
                "timestamp", Instant.now().toString()
        );
    }
}
