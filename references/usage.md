# 用量与额度

Tako 有两种只读视角。需要判断一次请求是否可能重复扣费时，先看当前 Key；需要看用户账户的订阅窗口和累计消费时，再看 billing 视角。两者都只读，不会生成图片、搜索或改变额度。

## 快速查询

在 Skill 目录执行，先配置完整的用户 Key：

```bash
export TAKO_BASE_URL="https://tako.shiroha.tech"
export TAKO_API_KEY="YOUR_COMPLETE_TAKO_USER_KEY"

# 当前 API Key 的授予、已用、可用额度、模型限制和过期时间
./scripts/tako-usage.sh token

# 用户订阅窗口 + 聚合计费用量
./scripts/tako-usage.sh billing
```

输出是 Tako 原始 JSON。脚本不把 Key 写入文件；billing 模式只在受限临时目录保存两个响应，结束时删除。不要把带有账户信息的输出直接发到公共聊天。

## 端点与字段

| 视角 | 请求 | 认证 | 主要字段 |
| --- | --- | --- | --- |
| 当前 Key | `GET /v1/usage/token/` | `Authorization: Bearer <完整 Key>` | `data.total_granted`、`data.total_used`、`data.total_available`、`data.unlimited_quota`、`data.model_limits`、`data.expires_at` |
| 订阅窗口 | `GET /v1/dashboard/billing/subscription` | 同上 | `hard_limit_usd`、`soft_limit_usd`、`system_hard_limit_usd`、`access_until` |
| 聚合消费 | `GET /v1/dashboard/billing/usage` | 同上 | `total_usage`（接口按展示设置返回，通常是美元值 × 100） |

`total_granted` 是当前 Key 的初始额度加已用额度，`total_available` 是剩余额度，单位是 Tako quota；不要直接当人民币或美元。`unlimited_quota=true` 时，Key 不受固定额度约束。`expires_at=0` 表示没有固定过期时间；具体账户订阅窗口仍以 billing 响应为准。

示例响应结构（数值仅作字段说明）：

```json
{
  "code": true,
  "message": "ok",
  "data": {
    "object": "token_usage",
    "total_granted": 100000000,
    "total_used": 2500000,
    "total_available": 97500000,
    "unlimited_quota": false,
    "model_limits": {},
    "model_limits_enabled": false,
    "expires_at": 0
  }
}
```

## 给助手的判断规则

- 生图、改图、搜索或 System One 之前，用户问“还剩多少”时先执行 token 查询，并报告查询时间、可用额度、是否无限额、模型限制和过期信息。
- 看到 `401`/`403` 先检查完整 Key、禁用状态和用户封禁；不要把它解释成额度不足。
- 可用额度为 0、billing 返回错误或上游明确报余额不足时，停止付费重试并说明计费来源；单独提高 Key 限额不会增加账户或订阅额度。
- `total_available` 只表示当前 Key；订阅窗口和用户聚合消费要同时参考 billing 模式，不能把两套数字相加。
- 超时后先查询用量并检查已保存响应，再决定是否重试图片请求。查询本身是只读的，不会恢复已经扣除的额度。
- 查询结果是一个时间点快照，不能据此承诺某次请求一定成功；模型权限、分组、订阅状态和上游限流仍可能拒绝请求。

## 历史兼容接口

Tako 仍保留 tako-cli 使用的 `GET|POST /apiStats/api/user-quota`、`GET|POST /apiStats/api/user-stats` 和 `POST /apiStats/api/get-key-id`。它们需要先用 `get-key-id` 将 Key 映射为用户 ID，返回的是兼容旧客户端的计划/日用量形状；新脚本默认使用上面的只读 Key 端点。不要把 `apiId` 当作用户 Key，也不要在公共日志中打印它和原始响应。

查询能力按 2026-10-04 Tako 代码契约整理；本次只补充 Skill 的只读入口和文档，没有重新消耗图片、搜索或决策额度。
