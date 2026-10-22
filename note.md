## 2. DeepSeek 不支持 `with_structured_output` 的 `tool_choice` 参数

**现象**：调用 `with_structured_output(CustomerIntent, method="function_calling")` 时报错：
```
BadRequestError: deepseek-reasoner does not support this tool_choice
```

**根因**：LangChain 的 `with_structured_output(method="function_calling")` 内部会将 `tool_choice` 强制设为指定 tool 的名称，要求模型只能调用该 tool。DeepSeek 的 API 不接受这种用法。

**修复**：放弃 `with_structured_output`，改为手动 `bind_tools` + 从 `tool_calls` 中解析：
```python
_router_llm = ChatOpenAI(...).bind_tools([CustomerIntent])

def _classify(user_text):
    response = _router_llm.invoke(...)
    if response.tool_calls:
        args = response.tool_calls[0]["args"]
        return CustomerIntent.model_validate(args)
    # 无 tool_call → 模型回了纯文本 → 视为闲聊
    return CustomerIntent(intent="CHITCHAT", ...)
```

> 教训：`with_structured_output` 并非万能。当模型供应商不完全支持 OpenAI 的 `tool_choice` 语义时，`bind_tools` 是更底层、兼容性更好的选择。

---

## 3. DeepSeek thinking mode 导致 `reasoning_content` 回传错误

**现象**：子图中第二次调用 LLM 时报错：
```
BadRequestError: The `reasoning_content` in the thinking mode must be passed back to the API.
```

**根因**：DeepSeek v4 Flash 默认启用 thinking mode。API 返回的 assistant message 中包含 `reasoning_content` 字段，后续请求必须原样回传。但 LangChain 的 `AIMessage` 不会自动保留该字段。

**修复**：通过 `extra_body` 参数全局禁用 thinking mode：
```python
ChatOpenAI(
    ...,
    extra_body={"thinking": {"type": "disabled"}},
)
```

---

## 4. `model_kwargs` vs `extra_body` 的参数透传差异

**现象**：使用 `model_kwargs={"thinking": {"type": "disabled"}}` 时报错：
```
TypeError: Completions.create() got an unexpected keyword argument 'thinking'
```

**根因**：LangChain 的 `model_kwargs` 会将参数直接作为 `create()` 的关键字参数传递。而 `thinking` 不是 `create()` 的合法参数 —— 它需要嵌套在 `extra_body` 字典中，由 OpenAI SDK 的 `create(extra_body={...})` 单独处理。

**修复**：通过 `ChatOpenAI.model_fields` 确认 `extra_body` 是合法字段，改用：
```python
ChatOpenAI(extra_body={"thinking": {"type": "disabled"}})
```

> 教训：`model_kwargs` 和 `extra_body` 是不同的透传通道。需要嵌套在 `extra_body` 中的参数不能放到 `model_kwargs`，反之亦然。遇到未知参数错误时，先用 `ChatOpenAI.model_fields` 查看可用字段列表。

---

## 5. 工具调用循环超限后无文本输出（空回复）

**现象**：产品推荐域命中 `MAX_CORRECTION_ATTEMPTS`（3 次）后，用户看到空回复。

**根因**：当循环因超限强制终止时，最后一条消息是 `ToolMessage`（工具执行结果），而非 `AIMessage`（文本回复）。`main.py` 取 `messages[-1].content` 输出，拿到的是工具返回的 JSON 字符串而非给用户看的自然语言。

**第一次尝试（失败）**：新增独立的 `summarize_node` 节点，超限后路由到该节点生成总结。但这引入了新问题 —— 最后一个 LLM 消息中包含未被执行的 `tool_calls`，而 OpenAI API 要求每个 `tool_call_id` 必须有对应的 `ToolMessage`：
```
BadRequestError: An assistant message with 'tool_calls' must be followed by
tool messages responding to each 'tool_call_id'.
```

**最终方案**：将超限检测内置到 `_llm_node` 内部，而非依赖拓扑分支。

```python
def _llm_node(state):
    attempts = state.get("correction_attempts", 0)
    if attempts >= MAX_CORRECTION_ATTEMPTS:
        # 超限 → 用不带 tool 的 chat_llm，保证一定输出文本
        response = _chat_llm.invoke(full_messages)
    else:
        # 正常 → 用带 tool 的 llm
        response = llm.invoke(full_messages)
    return {"messages": [response], "correction_attempts": attempts + 1}
```

拓扑随之简化：
```
条件边只判断「是否有 tool_calls」：
  有 → tools → llm（循环）
  无 → END
超限控制在 llm_node 内部完成，不依赖额外的拓扑分支。
```

> 教训：在 LangGraph 的 tool-calling 循环中，超限控制不应由条件边 + 额外节点实现（会导致 `tool_calls` / `ToolMessage` 配对断裂）。更好的方式是将超限逻辑内化到 LLM 节点中，通过切换为不带 tool 的 LLM 实例强制生成文本回复。

---

## 6. DeepSeek 在无 tool binding 时输出幻觉 tool_call 文本

**现象**：超限强制总结路径（使用 `_chat_llm`，未绑定任何 tool）下，DeepSeek 的回复内容中出现原始的 XML 格式 tool_call 文本：
```
<tool_calls>
<invoke name="search_product_specs">
<parameter name="query" string="true">耳机</parameter>
```

**根因**：DeepSeek v4 Flash 的训练数据中包含 tool_call 格式。当对话历史中存在 tool_call / ToolMessage 消息对时，即使当前请求未绑定任何 tool，模型也可能从历史中学习并模仿该格式输出，产生"tool call 幻觉文本"。

**修复**：两步并行 —（1）强化 override prompt，明确禁止输出 XML 标签；（2）在超限路径的 LLM 调用后增加 `_strip_tool_call_text()` 防御性清洗，正则匹配 `<tool_calls>` 并截断：

```python
def _strip_tool_call_text(text: str) -> str:
    if "<tool_calls>" not in text and "</tool_calls>" not in text:
        return text
    cleaned = re.split(r"<\s*/?\s*tool_calls", text)[0].strip()
    if cleaned:
        return cleaned
    return "抱歉，系统暂时无法完成该请求，请稍后重试或联系人工客服。"
```

> 教训：不带 tool binding 的 LLM 调用不保证不输出 tool_call 格式。当模型训练数据中包含 tool_call 格式且对话历史中存在先例时，模型可能"模仿"输出。必须同时做 prompt 层禁止和代码层清洗。

---——————————————————————————————————————————————————————————————————————————————

## CLI Streaming 改造的五个关键点

**目标**：把原来的 `graph.invoke()` 阻塞式调用，改成可以边生成边输出的流式 CLI，同时保留路由决策、工具调用、自修正过程的可观测性。

### 1. 用 `graph.stream()` 替代 `graph.invoke()`

**原来**：整轮图执行完后，才从 `result["messages"][-1]` 取最终回复。

**现在**：使用 LangGraph 的事件流：

```python
stream = graph.stream(
    {"messages": [HumanMessage(content=user_input)]},
    config=config,
    stream_mode=["updates", "messages"],
    subgraphs=True,
)
```

含义：
- `messages`：拿到 token 级别的 LLM 输出，用于打字机式输出。
- `updates`：拿到节点级状态更新，用于展示路由、工具调用、工具返回。
- `subgraphs=True`：让订单/售后/商品三个业务子图内部的 `llm` / `tools` 事件也能被主循环捕获。

### 2. 用双通道事件流区分"给用户看的 token"和"给开发者看的状态"

`stream_mode=["updates", "messages"]` 会让每条事件带上模式：

```python
namespace, mode, payload = chunk
```

处理策略：
- `mode == "messages"`：处理 `AIMessageChunk`，把内容流式打印给用户。
- `mode == "updates"`：处理 `{node_name: state_delta}`，打印路由决策、工具调用和工具返回。

这样 CLI 不只是"流式输出文本"，还能展示 agent 内部执行路径，适合 demo 和调试。

### 3. 过滤可流式输出的节点，避免中间思考/摘要外泄

不是所有 LLM token 都应该打印给用户。比如 router、memory summary 之类中间节点可能产生结构化分类、摘要或内部文本。

当前通过元数据过滤：

```python
_STREAMABLE_NODES = {"chat", "llm"}

if meta.get("langgraph_node") not in _STREAMABLE_NODES:
    continue
```

只允许两类节点流式打印：
- `chat`：主图闲聊节点。
- `llm`：业务子图里的订单/售后/商品 LLM 节点。

> 教训：Streaming 不是把所有 token 直接吐给用户，而是要做节点级白名单过滤。否则 agent 的内部状态、路由结果、摘要内容可能泄露到用户界面。

### 4. 工具调用阶段不打印空 token，只展示工具事件

Tool calling 阶段，模型通常不会在 `content` 里输出自然语言，而是通过 `tool_calls` 字段表达要调用的工具。

因此 `messages` 通道里空内容直接跳过：

```python
content = msg_chunk.content
if not content:
    continue
```

而工具调用和工具返回通过 `updates` 通道展示：

```python
[🔧 调用 lookup_order(order_id='78901')]
[⚠️ lookup_order 校验失败 → LLM 将自我修正] ...
[🔧 调用 lookup_order(order_id='2024-78901')]
[✓ lookup_order 返回] 📦 订单 2024-78901
```

这样用户看到的是最终自然语言回复，开发者同时能看到 self-correction 是否真的发生。

### 5. 用本地静态校验确认改造是否成功

这次没有直接跑真实 LLM 请求，而是做了不联网的静态校验：

```text
✓ main.py 字节码编译通过
✓ 关键函数齐全
✓ graph.stream kwargs 配置正确: stream_mode + subgraphs=True
✓ langgraph 版本 API 兼容
```

验证点包括：
- `main.py` 无语法错误。
- `_print_router_decision` / `_print_llm_tool_calls` / `_print_tool_results` / `run_cli` 都存在。
- `graph.stream()` 使用了 `stream_mode=["updates", "messages"]`。
- 当前 LangGraph 版本的 `CompiledStateGraph.stream` 支持 `stream_mode` 和 `subgraphs` 参数。

> 教训：Streaming 改造的成功标准不只是"代码能跑"，而是同时满足三点：token 能实时输出、子图事件能被捕获、中间节点不会泄露给用户。


————————————————————————————————————————————————————————————

## 追踪计时修复：用 `run_id` 区分每次 LLM / Tool 调用

原先 `AgentTracer` 的计时器使用固定 key：

```python
self._timers["__llm__"] = time.time()
self._timers["__tool__"] = time.time()
```

这个写法在简单串行 demo 里能工作，但在 LangGraph / LangChain 的真实 callback 场景下不够稳：

- 同一轮图执行里可能连续触发多个 LLM 调用，例如 router、业务子图 LLM、memory summary。
- 工具调用也可能在子图循环中多次发生。
- 如果存在嵌套调用或未来引入并发，固定 key 会被后一次 start 覆盖，导致前一次 end 取到错误耗时，甚至出现 `latency_ms = -1`。

这次改为使用 LangChain callback 传入的 `run_id` 作为计时维度：

```python
self._timers[_timer_key("llm", kwargs)] = time.time()
self._timers[_timer_key("tool", kwargs)] = time.time()
```

另外补了 `on_chat_model_start`，因为 `ChatOpenAI` 这类模型在 LangChain 中可能触发 chat model callback，而不是普通 `on_llm_start`。

其中 key 形如：

```text
llm:<run_id>
tool:<run_id>
```

同时在 JSONL 事件里写入 `run_id`：

```json
{"type": "llm", "run_id": "...", "latency_ms": 1234}
{"type": "tool", "run_id": "...", "latency_ms": 52}
```

这样每一次 LLM / Tool 的 start 和 end 都能一一配对，后续排查也可以按 `run_id` 串起单次调用。`unknown` 只作为旧版 callback 没有传 `run_id` 时的兼容兜底。


————————————————————————————————————————————————————————————

## RAG 跨目录 import 修复：不要把 `sys.path` 注入写在单一入口里

**现象**：跑交互式入口 `python main.py` 时，本地 RAG 可以 import；但跑评测入口 `python run_eval.py` 时失败：

```text
ModuleNotFoundError: No module named 'agent'
```

报错链路是：

```text
run_eval.py
  → eval.runner
  → src.config
  → src.__init__
  → src.graph
  → src.nodes
  → from agent.rag_tool import local_document_search
```

**根因**：`local-rag` 是隔壁目录：

```text
lc_cc/
├── agent-customer-service/
│   └── main.py
└── local-rag/
    ├── agent/
    │   └── rag_tool.py
    └── ingestion/
        └── pdf_parser.py
```

最开始只在 `main.py` 顶部做了：

```python
_LOCAL_RAG_PATH = Path(__file__).resolve().parent.parent / "local-rag"
sys.path.insert(0, str(_LOCAL_RAG_PATH))
```

这只对 `python main.py` 有效。`run_eval.py` 不会执行 `main.py`，所以 `src.nodes` 在 import `agent.rag_tool` 时找不到隔壁项目。

**第一次修复尝试**：抽出 `src/local_rag_path.py`，用 `ensure_local_rag_path()` 统一注册 `../local-rag`。但如果在 `src/__init__.py` 里过早调用，容易扩大副作用：任何 `import src.*` 都会把隔壁项目插到 `sys.path[0]`，并可能触发不必要的依赖解析。

**最终修复**：

1. 保留 `src/local_rag_path.py`，集中计算路径，并支持 `LOCAL_RAG_PATH` 环境变量覆盖。
2. 新增 `src/rag_tools.py`，在本项目内定义轻量的 LangChain `@tool` wrapper：

```python
@tool
def local_document_search(query: str) -> str:
    ensure_local_rag_path()
    from agent.rag_tool import local_document_search as _local_document_search
    return _local_document_search.invoke({"query": query})
```

3. `src.nodes` 只导入本项目 wrapper：

```python
from src.rag_tools import local_document_search
```

4. `main.py` 初始化索引时仍调用 `ensure_local_rag_path()`，再 import `build_rag_indexes` / `parse_and_chunk`。

**为什么这样更好**：

- `run_eval.py` 的 import 链不会再因为 `agent.rag_tool` 找不到而失败。
- eval 启动阶段不会提前加载 `sentence_transformers` / embedding 等 RAG 重依赖。
- 真正调用 `local_document_search` 时才懒加载隔壁 `local-rag` 实现。
- 未来如果把 `local-rag` 正式做成 package，可以替换为 `pip install -e ../local-rag`，不需要改业务图结构。

**验证**：

```bash
./.venv/bin/python -c "from eval.runner import run_suite; print('eval import ok')"
./.venv/bin/python -c "import src.nodes; print('nodes ok')"
./.venv/bin/python run_eval.py --help
```

> 教训：跨项目复用代码时，不要把 `sys.path` 注入放在某个 CLI 入口里。所有入口都会 import 的代码应该依赖稳定 package，或用小 wrapper 做懒加载，把路径 hack 的影响面控制到最小。


————————————————————————————————————————————————————————————

## Eval case 修复：`refund_create_request` 和 `hitl_explicit_request`

这次全量 eval 原本是 `8/12 passed`，其中先处理两个最有价值的失败：

```text
refund_create_request   未通过: tool:create_return_request
hitl_explicit_request   未通过: escalation
```

### 1. `refund_create_request` 没有创建退货工单

**现象**：用户输入已经足够明确：

```text
订单 2024-78901 的键盘有质量问题，帮我提交退货申请，原因写质量问题
```

但 agent 只调用了 `check_return_policy`，然后追问是否拆封、具体质量问题，没有调用 `create_return_request`。

**根因**：`REFUND_SYSTEM_PROMPT` 太保守。原流程写的是：

```text
确认问题 → 查政策 → 告知方案 → 客户确认后创建工单
```

模型把“质量问题 + 政策里的未拆封条件”理解成还需要继续确认，而没有把用户的“帮我提交退货申请，原因写质量问题”视为明确授权。

**修复**：在售后 prompt 中新增“直接创建规则”：

```text
- 如果用户已经提供订单号、退货原因，并明确要求"提交/创建/申请退货"，不要继续追问；
  查询政策后应立即调用 create_return_request 创建退货工单。
- 质量问题属于售后申请的有效原因；即使政策提到"未拆封"，也不要因为用户说质量问题而卡住流程。
```

**验证**：

```bash
./.venv/bin/python run_eval.py --case refund_create_request
# 1/1 passed
```

### 2. `hitl_explicit_request` 只是口头转人工，没有创建工单

**现象**：用户明确说：

```text
这个问题太复杂了，帮我转人工客服处理
```

路由结果是 `CHITCHAT`，最终回复也包含“转人工客服”，但 eval 仍失败：

```text
未通过: escalation
```

**根因**：`CHITCHAT` 路径走的是普通 `chat_node`，这个节点只绑定 `_chat_llm`，没有 `escalate_to_human` 工具。模型只能生成“我帮你转人工”的文本，不能真的创建工单，因此 `ToolMessage(name="escalate_to_human")` 不存在，eval 的 `require_escalation` 检查失败。

**修复**：

1. 新增 `human_support_node`，在用户明确要求转人工时直接调用 `escalate_to_human.invoke(...)`。
2. 手动写入一组消息，保证最终 state 里既有 tool call 记录，也有 `ToolMessage(name="escalate_to_human")`，便于 eval 和 tracing 识别：

```python
tool_call = AIMessage(
    content="",
    tool_calls=[{"name": "escalate_to_human", "args": args, "id": tool_call_id}],
)
tool_result = escalate_to_human.invoke(args)
ToolMessage(content=str(tool_result), name="escalate_to_human", tool_call_id=tool_call_id)
```

3. 在 `graph.py` 的条件路由里增加显式转人工检测：

```python
if _is_explicit_human_support_request(state):
    return "human_support"
```

这里没有改 state 里的 `route` 字段，所以 eval 仍可接受 `CHITCHAT` 路由；只是图执行时会分流到实际创建工单的节点。

**验证**：

```bash
./.venv/bin/python run_eval.py --case hitl_explicit_request
# 1/1 passed
```

> 教训：HITL 不能只靠自然语言“我帮你转人工”。只要系统需要工单、审计或 eval 识别，就必须让图里真的执行 `escalate_to_human`，并把工具调用结果写回 messages。
