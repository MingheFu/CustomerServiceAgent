# Agent Customer Service · Backend (Java)

业务与工具层。基于 Spring Boot 3.3 + Java 21 + MySQL + Maven。

Python 端 LangGraph Agent 把这里暴露的 REST API 当作"工具"调用：

```
Python Agent (LangGraph)
    │ tool call: lookup_order("2024-78901")
    ▼
Python tools.py (HTTP adapter)
    │ GET /api/orders/2024-78901
    ▼
Java Spring Boot (本目录)
    │ JPA
    ▼
MySQL
```

## 业务域

| 域 | 说明 | 端点前缀 |
| --- | --- | --- |
| 订单 | 查询订单、修改未发货订单地址 | `/api/orders` |
| 退换货 | 退换货政策、创建退货单 | `/api/returns` |
| 商品 | 商品搜索、按场景推荐 | `/api/products` |
| 人工工单 | HITL 转人工兜底 | `/api/tickets` |

## 错误协议

所有非 2xx 响应统一返回 `ErrorResponse`：

```json
{
  "errorType": "VALIDATION_ERROR",
  "message": "order_id 不符合格式 YYYY-NNNNN",
  "hint": "请尝试在下一次调用时改用 \"2024-78901\""
}
```

`errorType` 枚举：

- `VALIDATION_ERROR` — 入参校验失败 (400)
- `NOT_FOUND` — 资源不存在 (404)
- `BUSINESS_BLOCKED` — 业务规则拒绝，如已发货不能改地址 (409)
- `SYSTEM_ERROR` — 系统内部错误 (500)

这套结构和 Python `_validate_order_id` 输出的"给 LLM 看的错误"对齐，Agent 端可以直接根据 `errorType` 决定是 self-correct、追问用户还是转人工。

## 本地启动

### 1. 准备 MySQL

```sql
CREATE DATABASE agent_cs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 如果你还没有创建数据库：
-- CREATE DATABASE agent_cs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 数据库连接

默认使用 `application.yml` 中的 localhost + root 账号连接 `agent_cs` 库。
如需覆盖，可设置环境变量：

```bash
export DB_URL='jdbc:mysql://localhost:3306/agent_cs?...'
export DB_USERNAME=your_user
export DB_PASSWORD=your_password
```

### 3. 启动

```bash
cd backend
./mvnw spring-boot:run     # 或
mvn spring-boot:run
```

启动后：

- API base: <http://localhost:8080/api>
- Swagger UI: <http://localhost:8080/swagger-ui.html>

Flyway 会自动执行 `src/main/resources/db/migration/` 下的脚本初始化 schema 并写入 mock 数据，与 Python 端原先的 `_MOCK_ORDERS` / `_PRODUCT_DB` 一致。
