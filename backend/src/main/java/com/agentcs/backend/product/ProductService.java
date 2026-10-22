package com.agentcs.backend.product;

import com.agentcs.backend.common.error.BusinessException;
import com.agentcs.backend.common.error.ErrorType;
import com.agentcs.backend.entity.ProductEntity;
import com.agentcs.backend.product.dto.ProductResponse;
import com.agentcs.backend.product.dto.ProductSearchResponse;
import com.agentcs.backend.product.dto.RecommendItem;
import com.agentcs.backend.product.dto.RecommendResponse;
import com.agentcs.backend.repository.ProductRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 商品领域服务。对应 Python 端的 search_product_specs / get_product_recommendation。
 *
 * <p>搜索不命中时返回空列表 + {@code hintIfEmpty}（而非抛错），让 Agent
 * 自行决定是换关键词重试还是追问用户，与 Python 端"软失败"语义一致。
 */
@Service
public class ProductService {

    private static final Logger log = LoggerFactory.getLogger(ProductService.class);
    private static final TypeReference<Map<String, String>> SPECS_TYPE = new TypeReference<>() {};

    private final ProductRepository productRepository;
    private final ObjectMapper objectMapper;

    public ProductService(ProductRepository productRepository, ObjectMapper objectMapper) {
        this.productRepository = productRepository;
        this.objectMapper = objectMapper;
    }

    public ProductSearchResponse search(String query) {
        if (query == null || query.isBlank()) {
            throw new BusinessException(
                    ErrorType.VALIDATION_ERROR,
                    "query 为空。",
                    "请提供至少一个关键词，例如 \"键盘\" / \"MX Master\" / \"降噪耳机\"。"
            );
        }

        String q = query.trim();
        List<ProductEntity> hits = productRepository.search(q.toLowerCase());
        List<ProductResponse> results = hits.stream().map(this::toResponse).toList();
        String hint = results.isEmpty()
                ? "未命中任何商品。建议尝试更通用的关键词，如 \"键盘\"/\"鼠标\"/\"耳机\"，或追问用户的核心需求点。"
                : null;
        return new ProductSearchResponse(q, results.size(), results, hint);
    }

    public RecommendResponse recommend(String useCase, String budget) {
        String uc = useCase == null ? "" : useCase.trim();
        String bg = (budget == null || budget.isBlank()) ? "不限" : budget.trim();

        List<RecommendItem> items = new ArrayList<>();

        if (containsAny(uc, "编程", "办公", "日常")) {
            items.add(new RecommendItem("logitech-mx-master-3s",
                    "Logitech MX Master 3S 无线鼠标", "¥699",
                    "办公效率旗舰，适合长时间使用"));
            items.add(new RecommendItem("keychron-k8-pro",
                    "Keychron K8 Pro 机械键盘", "¥598",
                    "编程神器，QMK/VIA 自定义键位"));
        }
        if (containsAny(uc, "游戏")) {
            items.add(new RecommendItem("keychron-k8-pro",
                    "Keychron K8 Pro 机械键盘", "¥598",
                    "茶轴手感，游戏办公两相宜"));
        }
        if (containsAny(uc, "音乐", "通勤")) {
            items.add(new RecommendItem("sony-wh-1000xm5",
                    "Sony WH-1000XM5 头戴式降噪耳机", "¥2,499",
                    "降噪标杆，通勤/音乐首选"));
        }

        if (items.isEmpty()) {
            items.add(new RecommendItem("keychron-k8-pro",
                    "Keychron K8 Pro 机械键盘", "¥598", "机械键盘入门首选"));
            items.add(new RecommendItem("logitech-mx-master-3s",
                    "Logitech MX Master 3S 无线鼠标", "¥699", "办公鼠标天花板"));
            items.add(new RecommendItem("sony-wh-1000xm5",
                    "Sony WH-1000XM5 头戴式降噪耳机", "¥2,499", "降噪耳机王者"));
        }

        return new RecommendResponse(uc, bg, items);
    }

    private ProductResponse toResponse(ProductEntity p) {
        Map<String, String> specs = parseSpecs(p.getSpecsJson());
        return new ProductResponse(
                p.getProductId(),
                p.getName(),
                p.getPrice(),
                p.getCategory(),
                p.getHighlights(),
                specs
        );
    }

    private Map<String, String> parseSpecs(String specsJson) {
        if (specsJson == null || specsJson.isBlank()) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(specsJson, SPECS_TYPE);
        } catch (Exception ex) {
            log.warn("specs_json 反序列化失败，将返回空 specs。json={}, err={}", specsJson, ex.toString());
            return new LinkedHashMap<>();
        }
    }

    private static boolean containsAny(String text, String... keywords) {
        for (String k : keywords) {
            if (text.contains(k)) {
                return true;
            }
        }
        return false;
    }
}
