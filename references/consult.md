# 外脑体系：深度会诊 vs 结构化决策

Tako 提供两套互补的「外脑」能力：一套负责**开放式深度架构与代码会诊**（`tako-consult.sh`，默认 `gpt-6.2-sol`），另一套负责**低延迟、确定性的结构化分类/打分/二元判别**（`tako-systemone.sh` / `POST /v1/systemone`，`jev-latest`）。

[返回首页](../README.md) · [System One 结构化决策](systemone.md) · [快速开始](../docs/getting-started.md) · [常见问题](../docs/troubleshooting.md)

## 双外脑定位与选型

| 维度 | 深度外脑会诊（`tako-consult.sh`） | 结构化判别外脑（`tako-systemone.sh` / `/v1/systemone`） |
| --- | --- | --- |
| 默认模型与接口 | `gpt-6.2-sol` → `POST /v1/chat/completions`（`stream: false`） | `jev-latest` → `POST /v1/systemone` |
| 核心定位 | 独立高级架构 / 代码会诊参谋（Second Opinion） | `Choice` / `Score` / `Noul` 结构化状态判断 |
| 擅长场景 | 挑战隐含假设与盲点、排查并发/状态机竞态、评审重构方案、给出可落地修正补丁 | 工单路由分流、按多条标准打分、自动化流程中的明确布尔门禁 |
| 返回结构 | 自然语言深度分析（提取 `choices[0].message.content`） | 严格结构化 `answers` JSON 对象 |
| 何时不要混用 | 不要用 `tako-consult.sh` 代替脚本里需要稳定枚举字段的判断 | 不要用 `jev-latest` 写代码、评审架构或做自由文本对话 |

## 何时调用深度外脑会诊

1. **并发与状态机高风险改动前**：异步超时重试、支付回调乱序到达、多客户端配置热更新或文件锁竞争。
2. **主模型陷入局部最优或自说自话时**：需要另一个前沿模型独立挑刺、质疑前提假设。
3. **跨模块重构 / 故障根因排查**：结合日志与源码片段（`--context-file`）快速定位边界隐患。

## 最快方式：使用 `tako-consult.sh`

需要 Git、Bash、Python 3（仅用标准库）。在已配置 `TAKO_API_KEY` 的 Skill 根目录执行：

```bash
./scripts/tako-consult.sh "<question>" \
  [--model gpt-6.2-sol] \
  [--context "..."] \
  [--context-file <path>] \
  [--focus "..."] \
  [--out <json_path>]
```

- `--model`：默认 `gpt-6.2-sol`，也可按控制台权限切换 `gpt-6.2-astra`、`claude-opus-5-5`、`deepseek-v4.1-flash`、`swe-2` 等模型；helper 会保留你的显式选择。
- `--context` 与 `--context-file`：可同时或单独使用，helper 会自动组装为 `<context>` 段并附上文件路径标识。
- `--focus`：指定审查视角（如“并发竞态与幂等性”、“向后兼容性”）。
- `--out`：保存完整 API 响应 JSON（**拒绝覆盖已有文件**）。

## 真实会诊输入与输出示例

### 场景：异步任务 90s 超时重试与回调并发状态机评审

#### 输入命令

```bash
./scripts/tako-consult.sh \
  "异步生视频 90 秒超时重试与支付回调并发到达时，当前状态机容易在哪些地方造成重复扣费或状态回退？" \
  --context "客户端 90s 超时会自动重发请求；回调 handler 直接 UPDATE tasks SET status = \$1 WHERE id = \$2。" \
  --focus "幂等键设计、单调状态转移条件、超时恢复路径" \
  --out output/consult-state-machine.json
```

#### 会诊输出示例（摘录）

```text
1. 核心盲点：客户端超时重发缺少稳定幂等键
   若超时重发时生成新的 request_id，网关会当作全新生视频任务再次扣费。
   修正建议：将 idempotency_key 绑定到单次用户意图并在服务端对 (user_id, idempotency_key) 建唯一约束，命中直接返回已有 task_id。

2. 极端边界：settled 终态被晚到回调覆写（状态回退 / 错误退款）
   无条件 UPDATE tasks SET status = $1 WHERE id = $2 时，若轮询已结算为 completed，晚到的 timeout/failed 回调会倒退状态并触发误退款。
   修正建议：改为单调条件更新（WHERE id = $2 AND status IN ('pending', 'running')），受影响行数为 0 时按幂等忽略并记录审计日志。

3. 推荐改法：超时返回只读续传凭证
   90s 超时直接返回 status: 'pending' 与 task_id，后续通过只读 status / resume_task_id 查询接口继续等待结果，彻底消除盲目重扣。
```

### 附带本地源码文件做代码评审

```bash
./scripts/tako-consult.sh \
  "请排查这个脚本在原子落盘、路径校验与错误泄露方面是否还有边界漏洞。" \
  --context-file scripts/tako_audio.py \
  --focus "文件覆盖防护、异常路径泄露 Key、HTTP 非 2xx 处理" \
  --model gpt-6.2-sol
```

## 直接调用 API

```bash
curl --fail-with-body -sS --max-time 120 "$TAKO_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  --output consult-response.json \
  -d '{
    "model": "gpt-6.2-sol",
    "stream": false,
    "messages": [
      {
        "role": "system",
        "content": "You are an independent senior architecture and code consultation advisor. Challenge implicit assumptions and blind spots, uncover concurrency, state-machine, and edge-case hazards, and provide concrete, actionable fixes."
      },
      {
        "role": "user",
        "content": "多个桌面客户端同时切入本地统一网关时，端口抢占与配置热更新有哪些竞态盲点？"
      }
    ]
  }'
```

## 注意事项

- 外脑会诊会按模型消耗账户或订阅额度；不要把完整 `TAKO_API_KEY` 或敏感生产密钥放进 `--context` / `--context-file` 中发送给外部模型。
- 需要结构化枚举/评分输出时，请转向 [System One](systemone.md)（`POST /v1/systemone`）。
