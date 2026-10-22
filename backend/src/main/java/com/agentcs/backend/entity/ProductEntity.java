package com.agentcs.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;

@Entity
@Table(name = "products")
public class ProductEntity {

    @Id
    @Column(name = "product_id", length = 64, nullable = false)
    private String productId;

    @Column(name = "name", length = 255, nullable = false)
    private String name;

    @Column(name = "price", length = 64, nullable = false)
    private String price;

    @Column(name = "category", length = 64)
    private String category;

    @Column(name = "highlights", length = 512)
    private String highlights;

    @Lob
    @Column(name = "specs_json", columnDefinition = "TEXT")
    private String specsJson;

    public String getProductId() {
        return productId;
    }

    public void setProductId(String productId) {
        this.productId = productId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getPrice() {
        return price;
    }

    public void setPrice(String price) {
        this.price = price;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public String getHighlights() {
        return highlights;
    }

    public void setHighlights(String highlights) {
        this.highlights = highlights;
    }

    public String getSpecsJson() {
        return specsJson;
    }

    public void setSpecsJson(String specsJson) {
        this.specsJson = specsJson;
    }
}
