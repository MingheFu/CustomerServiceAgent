package com.agentcs.backend.product;

import com.agentcs.backend.product.dto.ProductSearchResponse;
import com.agentcs.backend.product.dto.RecommendRequest;
import com.agentcs.backend.product.dto.RecommendResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/products")
@Tag(name = "Product", description = "商品搜索与按场景推荐")
public class ProductController {

    private final ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping("/search")
    @Operation(summary = "关键词搜索商品", description = "对应 Python tool: search_product_specs。")
    public ProductSearchResponse search(@RequestParam("q") String q) {
        return productService.search(q);
    }

    @PostMapping("/recommend")
    @Operation(summary = "按场景+预算推荐商品",
            description = "对应 Python tool: get_product_recommendation。budget 可空，默认 \"不限\"。")
    public RecommendResponse recommend(@Valid @RequestBody RecommendRequest request) {
        return productService.recommend(request.useCase(), request.budget());
    }
}
