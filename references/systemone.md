# System One 结构化决策

用来分类、分流、打分或判断是否紧急，默认模型 `jev-latest`。这里整理既有 TypeSafe 契约和官网例子；2026-10-04 的图片验证没有重新在线测试 System One。

[返回首页](../README.md) · [配置 Key](../docs/getting-started.md) · [官网完整例子](https://tako.shiroha.tech/docs/integrations/tako-skill)

## 选择问题类型

| 类型 | 用途 | 请求中怎样描述 |
| --- | --- | --- |
| `choice` | 选择团队、类别或路线 | `criteria` 对象列出选项及解释 |
| `score` | 按标准打分 | `criteria` 数组描述评分标准 |
| `noul` | 判断一个陈述，例如是否紧急 | `instructions` 写出要判断的问题 |

写文章、写代码和聊天使用聊天模型；System One 不负责自由文本生成。英文问题是既有指南推荐的方式；中文可以提交，但没有承诺同等稳定性。

## 先试一个 Noul

```bash
./scripts/tako-systemone.sh "hello" "Is this a greeting?"
```

helper 只提交一个 Noul 问题。直接请求为：

```bash
curl --fail-with-body -sS --max-time 60 "$TAKO_BASE_URL/v1/systemone" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state":"hello","model":"jev-latest","questions":{"greeting":{"type":"noul","instructions":"Is this a greeting?"}}}'
```

成功后读取 `answers`。响应里的 `model` 可能是 `jev-1.13.0` 这样的版本号，不要因为它与别名不同就认定失败。

## 同时做分类、打分和紧急判断

先保存请求，再调用接口。这个示例沿用官网的三类问题结构，不把聊天接口包装成决策接口：

```bash
cat > systemone-request.json <<'JSON'
{
  "state": "My Stripe integration has failed for three days. I am losing sales. Please help ASAP.",
  "model": "jev-latest",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": {"billing": "Payment or subscription issues", "technical": "Bugs or integration problems", "sales": "Pricing or account questions"}
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated does the customer appear?",
      "criteria": ["Calm", "Frustrated but civil", "Very angry"]
    },
    "is_urgent": {"type": "noul", "instructions": "Does the message convey urgency?"}
  }
}
JSON
curl --fail-with-body -sS --max-time 60 "$TAKO_BASE_URL/v1/systemone" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @systemone-request.json --output systemone-response.json
```

检查响应中的 `answers.department`、`answers.frustration`、`answers.is_urgent`，按实际返回值交付结果；不要将它当作聊天文本。`state` 也可以是 JSON 对象。需要固定模型版本时，可按实际可用情况替换 `model`。

## 接入与错误

- 接口是 `POST /v1/systemone`，也兼容 `/api/v1/systemone`；鉴权使用同一 Tako 用户 Key。
- 不用 `/v1/chat/completions` 代替。不要依赖 `/v1/models` 发现 `jev-*`；公共定价目录在 2026-10-04 可见 `jev-latest`。
- TypeSafe SDK 的 `baseURL` / `TYPESAFE_BASE_URL` 使用 Tako 根域，不带 `/v1`，并使用 Tako Key。`systemOne()` 使用这个契约，`models.list()` 不保证能发现 Jev。
- `422` 时检查 `state`、`model`、`questions` 和问题类型；权限/额度问题见[常见问题](../docs/troubleshooting.md)。
- shell helper 使用 curl，HTTP 错误可能仍退出 0；检查响应 JSON。调用消费额度，不输出 Key。
