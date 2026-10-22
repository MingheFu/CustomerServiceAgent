# 端到端 Agent 评测集

正式评测已落地为可执行脚本，用例定义在 `eval/cases.json`。

## 快速开始

```bash
# 1. 启动 Java 后端（含 Flyway seed）
cd backend && mvn spring-boot:run

# 2. 配置 Python .env（LLM + BACKEND_URL）

# 3. 跑全量评测
python run_eval.py

# 只跑订单域
python run_eval.py --tag order

# 单条调试
python run_eval.py --case order_self_correct_id
```

报告写入 `eval/results/run_YYYYMMDD_HHMMSS.json`。

## 评测链路

```text
用户问题 (cases.json)
  → LangGraph（独立 thread_id，单轮 invoke）
  → Router 意图
  → 业务子图 + 工具
  → Java REST
  → 最终回复
  → 规则打分（route / tools / 关键词 / 禁词 / 转人工）
```

## 用例覆盖（12 条）

| ID | 场景 |
| --- | --- |
| `order_lookup_valid` | 合法订单查询 |
| `order_self_correct_id` | 缺年份订单号自修正 |
| `order_search_by_product` | 商品关键词搜订单 |
| `order_modify_address_pending` | 未发货改地址 |
| `order_modify_blocked_shipped` | 已发货改地址被拒 |
| `order_not_found` | 订单不存在 |
| `refund_policy_keyboard` | 退换货政策 |
| `refund_create_request` | 创建退货单 |
| `product_search_specs` | 商品规格 |
| `product_recommend_office` | 场景推荐 |
| `chitchat_greeting` | 寒暄不调业务工具 |
| `hitl_explicit_request` | 明确要求转人工 |

## 评分指标（规则化）

- `route`：意图路由是否命中（部分用例允许 `acceptable_routes`）
- `tool:*`：是否调用预期工具
- `no_tool:*`：是否误调业务工具（寒暄）
- `min_lookup_order_calls`：自修正路径
- `escalation`：是否创建人工工单
- `must_contain_any` / `must_not_contain`：最终回复 groundedness 粗检

未使用 LLM-as-judge，便于本地反复跑、CI 集成。后续可加「评委模型」层做语义打分。

## 注意事项

- **需要真实 LLM**：每条用例约 5–30s，全量约数分钟。
- **需要 Java 后端**：启动前会探活 `GET {BACKEND_URL}/health`。
- **路由偶有波动**：`chitchat` / `hitl` 用例对路由较宽松，硬约束在 `forbidden_tools` / `require_escalation`。
- **关键词检查是粗检**：不能替代人工审阅；可据失败报告调整 `must_contain_any`。

## 扩展用例

在 `eval/cases.json` 的 `cases` 数组追加对象，字段说明见文件内首条用例。与 seed 数据（`V2__seed_data.sql`）保持一致。
