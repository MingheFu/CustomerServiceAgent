package com.agentcs.backend.repository;

import com.agentcs.backend.entity.OrderEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface OrderRepository extends JpaRepository<OrderEntity, String> {

    @Query("SELECT o FROM OrderEntity o WHERE LOWER(o.product) LIKE LOWER(CONCAT('%', :keyword, '%'))")
    List<OrderEntity> searchByProduct(@Param("keyword") String keyword);
}
