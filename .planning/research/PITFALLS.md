# Pitfalls Research: Codebuddy Agent 集成

**Researched:** 2026-04-19
**Milestone:** v3.2 Codebuddy Agent 集成

## 常见陷阱

### 1. API Key 管理错误

**问题：** 忘记设置 `CODEBUDDY_INTERNET_ENVIRONMENT` 导致认证失败

**场景：**
- 中国版用户需要 `CODEBUDDY_INTERNET_ENVIRONMENT=internal`
- iOA 版用户需要 `CODEBUDDY_INTERNET_ENVIRONMENT=ioa`
- 海外版用户不需要设置（默认）

**预防策略：**

```python
# 在 config.py 中检测并提示
def validate_api_key():
    api_key = os.environ.get('CODEBUDDY_API_KEY')
    if not api_key:
        # 友好提示，不抛异常
        print("提示：未设置 CODEBUDDY_API_KEY")
        print("  - 如果已通过 CLI 登录，SDK 会自动使用登录凭据")
        print("  - 否则请设置环境变量：export CODEBUDDY_API_KEY='your-key'")
        return False
    return True
```

**处理阶段：** Phase 1 (Provider 初始化)

---

### 2. 工具调用失败时的无限循环

**问题：** 工具返回错误后，Agent 可能重复调用同一工具

**场景：**
- 工具参数验证失败
- 工具内部异常
- 依赖资源不可用

**预防策略：**

```python
# 在工具 handler 中捕获异常并返回友好错误
@tool("add_task", "添加任务", {...})
async def add_task(args: dict) -> dict:
    try:
        # 执行逻辑
        return {"success": True, "task": task}
    except ValueError as e:
        return {
            "success": False,
            "error": f"参数错误: {e}",
            "hint": "请检查参数格式后重试"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "retryable": False  # 明确标记不可重试
        }
```

**处理阶段：** Phase 2 (工具定义)

---

### 3. Session 日志过大

**问题：** 长时间对话导致日志文件过大

**场景：**
- 多轮对话累积大量消息
- 工具结果包含大量数据
- 未清理过期 session

**预防策略：**

```python
# 限制单个 session 的日志大小
MAX_SESSION_SIZE = 10 * 1024 * 1024  # 10MB

def save_session(session_id: str, messages: list[dict]):
    log_file = SESSIONS_DIR / f"{session_id}.jsonl"

    # 检查文件大小
    if log_file.exists() and log_file.stat().st_size > MAX_SESSION_SIZE:
        # 归档旧日志
        archive_file = SESSIONS_DIR / f"{session_id}_archived.jsonl"
        log_file.rename(archive_file)

    # 追加新消息
    with open(log_file, 'a') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')
```

**处理阶段：** Phase 3 (Session 管理)

---

### 4. Token 消耗追踪不准确

**问题：** 流式消息中 token 信息可能不完整

**场景：**
- 网络中断导致流不完整
- 缓存命中时 token 计数方式不同
- 多轮对话累积误差

**预防策略：**

```python
# 只在 ResultMessage 中统计最终 token
from codebuddy_agent_sdk import ResultMessage

total_usage = {"input": 0, "output": 0, "cache": 0}

async for message in query(...):
    if isinstance(message, ResultMessage):
        usage = message.usage or {}
        total_usage = {
            "input": usage.get("input_tokens", 0),
            "output": usage.get("output_tokens", 0),
            "cache": usage.get("cache_read_tokens", 0),
        }
        # 显示最终统计
        print(f"Token 消耗：输入 {total_usage['input']}，输出 {total_usage['output']}，缓存 {total_usage['cache']}")
```

**处理阶段：** Phase 3 (Token 显示)

---

### 5. 渐进式工具导致 Agent 困惑

**问题：** Agent 不知道何时需要获取工具详情

**场景：**
- 工具名称不够直观
- 系统提示词未说明渐进式机制
- Agent 过度或不足调用 `get_tool_details`

**预防策略：**

```python
# 系统提示词明确说明渐进式机制
SYSTEM_PROMPT = """
你是 claw-cron 的任务管理助手。

## 可用工具

- list_tasks: 列出所有定时任务（无需参数）
- add_task: 添加新任务（需调用 get_tool_details 获取参数）
- update_task: 修改已有任务（需调用 get_tool_details 获取参数）
- delete_task: 删除任务（需任务名）
- run_task: 立即执行任务（需任务名）

## 使用方式

1. 根据用户请求判断需要哪个工具
2. 如果不确定工具参数，先调用 get_tool_details 获取详细说明
3. 然后使用正确参数调用目标工具
"""
```

**处理阶段：** Phase 4 (系统提示词)

---

### 6. 多 Provider 切换时状态丢失

**问题：** 切换 Provider 时对话历史丢失

**场景：**
- 用户从 codebuddy 切换到 anthropic
- Session ID 不兼容
- 工具定义格式不同

**预防策略：**

```python
# 在切换 Provider 时提示用户
def switch_provider(new_provider: str, session_id: str | None):
    if session_id:
        print(f"警告：切换 Provider 将开始新对话")
        print(f"当前 session {session_id} 的历史不会保留")

    # 清理状态
    clear_session_state()

    # 初始化新 Provider
    return get_provider(new_provider)
```

**处理阶段：** Phase 1 (Provider 初始化)

---

### 7. 网络问题导致 SDK 调用失败

**问题：** Codebuddy SDK 依赖网络，可能因网络问题失败

**场景：**
- API 端点不可达
- 代理配置问题
- 临时网络中断

**预防策略：**

```python
from codebuddy_agent_sdk import CLIConnectionError, ExecutionError

async def safe_query(prompt: str, options: CodeBuddyAgentOptions, retries: int = 3):
    for attempt in range(retries):
        try:
            async for msg in query(prompt=prompt, options=options):
                yield msg
            return
        except CLIConnectionError as e:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
            raise
        except ExecutionError as e:
            if "rate limit" in str(e).lower():
                await asyncio.sleep(60)  # 速率限制等待
                continue
            raise
```

**处理阶段：** Phase 1 (Provider 初始化)

---

## 检查清单

### Phase 1 完成时

- [ ] API Key 缺失时友好提示（不抛异常）
- [ ] Provider 初始化失败时有降级方案
- [ ] 网络问题有重试机制

### Phase 2 完成时

- [ ] 所有工具都有错误处理
- [ ] 工具返回格式统一
- [ ] 工具文档清晰

### Phase 3 完成时

- [ ] Session 日志有大小限制
- [ ] Token 统计只在 ResultMessage 中显示
- [ ] 旧 session 有归档机制

### Phase 4 完成时

- [ ] 系统提示词说明渐进式工具机制
- [ ] Agent 能正确使用 get_tool_details
- [ ] 工具名称直观易懂
