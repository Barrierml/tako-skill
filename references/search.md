# 网页搜索

用 Tako 搜索并获得回答与来源。这里记录既有接口和历史成功检查；2026-10-04 的图片验证没有重新测试搜索。

[返回首页](../README.md) · [配置 Key](../docs/getting-started.md) · [排错](../docs/troubleshooting.md)

## 先运行一条搜索

在 Skill 克隆目录、已配置 Key 的终端中执行：

```bash
./scripts/tako-search.sh "capital of Japan" --count 3
```

有 `results` 时应得到标题、链接和摘要；回答在 `answer`。助手应引用实际返回的 `results[].url`，不要自行编造引用。

也可以对助手说：

```text
使用 tako-skill 搜索日本首都的信息，给出简短回答和返回的来源链接。
```

## 参数与接口

`POST $TAKO_BASE_URL/v1/search`，鉴权为 `Authorization: Bearer $TAKO_API_KEY`。

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `query` | 是 | 非空查询文本 |
| `count` | 否 | 默认 5，最多 20 |
| `provider` | 否 | `kab`、`groq`、`grok`、`grok_x`；只筛选服务族，不指定渠道 |

默认不传 provider，由渠道优先级/权重选择。需要筛选时：

```bash
./scripts/tako-search.sh "capital of Japan" --provider groq --count 3
```

直接请求：

```bash
curl --fail-with-body -sS --max-time 60 "$TAKO_BASE_URL/v1/search" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"capital of Japan","count":3}'
```

## 读取结果

响应格式示意：

```json
{
  "query": "capital of Japan",
  "provider": "kab",
  "answer": "Search results for: capital of Japan…",
  "results": [
    {"title": "Capital of Japan", "url": "https://en.wikipedia.org/wiki/Capital_of_Japan", "snippet": "…"}
  ]
}
```

部分 Groq 请求可能只返回 `answer`，空 `results` 不一定是失败。没有来源时明确说明，不要编造 URL。搜索也消费账户或订阅额度。

helper 使用 curl，HTTP 错误时进程仍可能退出 0；检查返回的错误 JSON，不能只看 shell 退出码。直接请求示例用 `--fail-with-body` 保留错误响应并返回非零状态。不用 chat-completions 模拟这个接口，也不发明 `kab_search` 等能力名。
