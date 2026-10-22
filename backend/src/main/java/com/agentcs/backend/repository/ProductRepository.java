package com.agentcs.backend.repository;

import com.agentcs.backend.entity.ProductEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface ProductRepository extends JpaRepository<ProductEntity, String> {

    /**
     * 关键词搜索：在 product_id / name / category / highlights 上做 case-insensitive LIKE。
     * 与 Python 端 search_product_specs 的行为对齐，覆盖商品 ID、品牌、品类与卖点关键词。
     */
    @Query("""
        SELECT p FROM ProductEntity p
        WHERE LOWER(p.productId)  LIKE LOWER(CONCAT('%', :q, '%'))
           OR LOWER(p.name)       LIKE LOWER(CONCAT('%', :q, '%'))
           OR LOWER(p.category)   LIKE LOWER(CONCAT('%', :q, '%'))
           OR LOWER(p.highlights) LIKE LOWER(CONCAT('%', :q, '%'))
        """)
    List<ProductEntity> search(@Param("q") String q);
}
