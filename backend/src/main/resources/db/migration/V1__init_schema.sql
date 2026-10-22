-- ============================================================================
-- V1: 初始 schema
-- 与 Python 端 src/tools.py 中 _MOCK_ORDERS / _RETURN_POLICIES / _PRODUCT_DB
-- 的字段对齐，所有金额使用 DECIMAL，订单号使用 VARCHAR 主键。
-- ============================================================================

CREATE TABLE orders (
    order_id            VARCHAR(16)     NOT NULL,
    product             VARCHAR(255)    NOT NULL,
    price               DECIMAL(10, 2)  NOT NULL,
    status              VARCHAR(32)     NOT NULL,
    order_date          DATE            NOT NULL,
    carrier             VARCHAR(64),
    tracking_no         VARCHAR(64),
    shipping_address    VARCHAR(512),
    estimated_delivery  DATE,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id)
);

CREATE TABLE return_policies (
    category                 VARCHAR(64)  NOT NULL,
    period_days              INT          NOT NULL,
    condition_text           VARCHAR(512) NOT NULL,
    shipping_responsibility  VARCHAR(255) NOT NULL,
    PRIMARY KEY (category)
);

CREATE TABLE return_requests (
    ticket_id   VARCHAR(32)  NOT NULL,
    order_id    VARCHAR(16)  NOT NULL,
    reason      VARCHAR(255) NOT NULL,
    status      VARCHAR(32)  NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticket_id),
    CONSTRAINT fk_return_order FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

CREATE TABLE products (
    product_id   VARCHAR(64)  NOT NULL,
    name         VARCHAR(255) NOT NULL,
    price        VARCHAR(64)  NOT NULL,
    category     VARCHAR(64),
    highlights   VARCHAR(512),
    specs_json   TEXT,
    PRIMARY KEY (product_id)
);

CREATE TABLE support_tickets (
    ticket_id           VARCHAR(32)   NOT NULL,
    issue_summary       VARCHAR(2000) NOT NULL,
    attempted_solutions VARCHAR(2000),
    urgency             VARCHAR(16)   NOT NULL,
    preferred_contact   VARCHAR(255),
    status              VARCHAR(32)   NOT NULL,
    created_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticket_id)
);

CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_products_category ON products (category);
CREATE INDEX idx_support_tickets_urgency ON support_tickets (urgency);
