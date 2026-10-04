# 图片生成与改图

用同一把 Tako 用户 API Key，可以生成新图片，也可以上传参考图要求修改。第一次使用建议选择 `gpt-image-2`，先生成一张图片，再试改图。图片请求会消耗账户或订阅额度。

## 准备 API Key

登录 [Tako 控制台](https://tako.shiroha.tech)，在密钥管理中创建用户 API Key。复制完整值，不要自行更换前缀。Key 的分组、模型权限和额度必须允许调用你选择的模型。

在运行命令的终端设置：

```bash
export TAKO_BASE_URL="https://tako.shiroha.tech"
# 在本机安全设置 TAKO_API_KEY；不要把真实 Key 发到聊天或提交到 Git。
```

所有示例使用 `Authorization: Bearer $TAKO_API_KEY`。这是 Tako 用户 Key，不是 OpenAI、Google 或 xAI 的官方 Key。使用 OpenAI SDK 时 `base_url` 带 `/v1`；下面 curl 和 helper 的 `TAKO_BASE_URL` 使用根域名。

## 选择模型和接口

以下按 2026-10-04 的线上调用验证整理。你的实际可用模型以控制台模型广场和 Key 权限为准。

| 模型 | 生成图片 | 改图的推荐入口 | 返回图片 |
| --- | --- | --- | --- |
| `gpt-image-2` | `/v1/images/generations` | `/v1/images/edits`，multipart 上传文件 | `data[].b64_json` |
| `gpt-image-2.5-flare` | 同上 | 同上 | 同上 |
| `gpt-image-2.5-sunburst` | 同上 | 同上 | 同上 |
| `gemini-3.1-flash-image` | Images API 或原生 `generateContent` | 原生 `generateContent` + `inlineData` | 原生为 `candidates[].content.parts[].inlineData` |
| `gemini-3-pro-image` | 同上 | 同上 | 同上 |
| `grok-imagine-image-quality` | `/v1/images/generations` | `/v1/images/edits`，JSON `images[].image_url` | 请求 `response_format=b64_json` |

Gemini 的 Images 兼容改图在当前线上版本存在参考图和返回结构问题，改图请使用下文的原生接口或已更新的 helper。原生生成/改图已验证。Grok 文生图和 JSON 改图都已验证返回可解码图片。当前上游 multipart 改图会忽略 `response_format`，需要 base64 返回时请使用 JSON 或 helper。Grok 的默认 URL 返回依赖 `imgen.x.ai` 下载链路，本次本机下载超时、服务端下载被拒；优先直接请求 base64 图片。

## 最快方式：使用 Tako Skill helper

需要 Git、Bash、Python 3。helper 使用 Python 标准库，不需要安装 OpenAI SDK。

```bash
git clone https://github.com/Barrierml/tako-skill.git
cd tako-skill

# 生成一张图：JSON 保存在 response.json，图片保存在 output/apple.png
./scripts/tako-image.sh generate "白色桌面上的红苹果，简洁摄影，无文字" \
  --out response.json --save-image output/apple.png

# 修改现有图片；明确什么改变、什么保持不变
./scripts/tako-image.sh edit output/apple.png \
  "只把苹果改成绿色，保持位置、形状、桌面和光照不变" \
  --out edited-response.json --save-image output/green-apple.png

# Gemini 改图：helper 自动选择原生接口并编码参考图
./scripts/tako-image.sh edit output/apple.png \
  "只把苹果改成绿色，保留其余内容" \
  --model gemini-3.1-flash-image \
  --out gemini-response.json --save-image output/gemini-edit.png

# Grok：helper 请求 base64，避免单独下载 CDN 图片链接
./scripts/tako-image.sh generate "白底蓝色圆形，无文字" \
  --model grok-imagine-image-quality \
  --out grok-response.json --save-image output/grok.png
```

`--out` 保存响应 JSON，`--save-image` 保存图片。实际扩展名根据图片字节自动选择：请求保存 `grok.png` 时，如果返回 JPEG，最终文件是 `grok.jpg`。多张图片按 `-1`、`-2` 编号。已有图片文件不会被覆盖。终端会输出最终文件路径。图片保存失败时保留成功响应；从响应恢复图片，不要重新付费生成。

只需更换 `--model` 就能切换上述模型。每次先用 `--n 1`；Gemini 一次只支持生成一张。GPT/Grok 的批量张数和其他高级参数需要按具体模型确认，不要从一个模型的成功推断到所有模型。

## 直接调用：生成图片

```bash
curl --fail-with-body -sS --max-time 240 "$TAKO_BASE_URL/v1/images/generations" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  --output response.json \
  -d '{"model":"gpt-image-2","prompt":"白色桌面上的红苹果，无文字","n":1,"response_format":"b64_json"}'
```

成功响应示意：

```json
{"created": 1791111000, "data": [{"b64_json": "..."}]}
```

将第一张图片解码到文件：

```bash
python3 - <<'PY'
import base64, json
from pathlib import Path
response = json.loads(Path("response.json").read_text())
data = base64.b64decode(response["data"][0]["b64_json"], validate=True)
ext = ".png" if data.startswith(b"\x89PNG") else ".jpg" if data.startswith(b"\xff\xd8\xff") else ".webp"
output = Path("generated" + ext)
with output.open("xb") as file:
    file.write(data)
print(output)
PY
```

要用 Grok，将 `model` 换为 `grok-imagine-image-quality`，保留 `response_format=b64_json`。Gemini 用 Images API 生成时只返回 base64，`n` 使用 `1`；需要原生参数时用下一节的接口。

## 直接调用：GPT 改图

准备一张 PNG、JPEG 或 WebP 参考图。下面以 PNG 为例：

```bash
curl --fail-with-body -sS --max-time 240 "$TAKO_BASE_URL/v1/images/edits" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  --output edited-response.json \
  -F "model=gpt-image-2" \
  -F "prompt=只把红苹果改成绿色，保持其他内容不变" \
  -F "n=1" \
  -F "response_format=b64_json" \
  -F "image=@./input.png;type=image/png"
```

让 curl 自动生成 multipart 的 `Content-Type` 和 boundary。JPEG 使用 `type=image/jpeg`，WebP 使用 `type=image/webp`。从响应的 `data[].b64_json` 保存图片，方法同上一节。另外两个 GPT 模型更换 `model` 即可。

GPT JSON 改图也已验证支持 `images:[{"image_url":"data:image/png;base64,..."}]`；上传本地文件仍推荐 multipart，避免手动拼接很长的 base64 JSON。

## 直接调用：Grok JSON 改图

需要直接返回 base64 时使用 JSON。先将图片编码成请求文件，再提交：

```bash
python3 - <<'PYCODE'
import base64, json
from pathlib import Path
payload = {
    "model": "grok-imagine-image-quality",
    "prompt": "只把红苹果改成绿色，保持其他内容不变",
    "n": 1, "response_format": "b64_json",
    "images": [{"image_url": "data:image/png;base64," + base64.b64encode(Path("input.png").read_bytes()).decode()}]
}
Path("grok-edit-request.json").write_text(json.dumps(payload))
PYCODE
curl --fail-with-body -sS --max-time 240 "$TAKO_BASE_URL/v1/images/edits" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @grok-edit-request.json --output edited-response.json
```

响应仍为 `data[].b64_json`，用前面的解码方式保存图片。JPEG/WebP 参考图替换 data URL 中的 MIME 类型。使用 helper 时，它会自动选择此 JSON 路径。

## 直接调用：Gemini 原生生成与改图

原生路径为 `/v1beta/models/{model}:generateContent`。请求中启用 `responseModalities=["TEXT","IMAGE"]`；改图时在文字指令旁加入 `inlineData`。下面会读取、编码、提交本地参考图，并把返回图片保存为 `gemini-edited.jpg/png/webp`：

```bash
python3 - <<'PY'
import base64, json, mimetypes, os, urllib.request
from pathlib import Path
source = Path("input.png")
model = "gemini-3.1-flash-image"
payload = {
    "contents": [{"role": "user", "parts": [
        {"text": "只把红苹果改成绿色，保持其他内容不变"},
        {"inlineData": {
            "mimeType": mimetypes.guess_type(source.name)[0],
            "data": base64.b64encode(source.read_bytes()).decode()
        }}
    ]}],
    "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
}
url = os.environ["TAKO_BASE_URL"].rstrip("/") + f"/v1beta/models/{model}:generateContent"
request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
    "Authorization": "Bearer " + os.environ["TAKO_API_KEY"],
    "Content-Type": "application/json"
})
with urllib.request.urlopen(request, timeout=240) as response:
    result = json.load(response)
Path("gemini-response.json").write_text(json.dumps(result))
images = [part["inlineData"] for candidate in result.get("candidates", [])
          for part in candidate.get("content", {}).get("parts", [])
          if part.get("inlineData", {}).get("mimeType", "").startswith("image/")]
if not images:
    raise SystemExit("没有收到图片；检查响应中的安全拦截或错误提示")
for index, image in enumerate(images):
    extension = {"image/png":"png", "image/jpeg":"jpg", "image/webp":"webp"}[image["mimeType"]]
    path = Path(f"gemini-edited-{index+1}.{extension}")
    with path.open("xb") as output:
        output.write(base64.b64decode(image["data"], validate=True))
    print(path)
PY
```

生成新图时，删除 `inlineData` 那个 part，并换成生成图片的提示词。另一个 Gemini 模型替换 `model` 为 `gemini-3-pro-image`。原生接口可通过 `generationConfig.imageConfig.aspectRatio` 指定画幅，例如 `16:9`。

## 参数、费用与限制

- 默认从 `model`、`prompt`、`n=1` 开始。尺寸、质量、透明背景、蒙版、多参考图等参数的支持因模型和渠道而异，本指南没有承诺它们都可用。
- 改图是模型按指令重绘，不能保证每个像素保持不变。提示词中写清“只改变什么、必须保留什么”，并打开结果检查。
- 普通请求等待完整响应。GPT `stream=true` 已实测返回图片完成事件；需要自行解析 SSE，不能把流式响应当普通 JSON。Gemini 原生流式与 Images 兼容流式是不同契约，不要混用。
- 请求耗时取决于模型、队列和网络；示例等待最多 240 秒。超时后先检查用量日志和已有响应，避免重复生成、重复扣费。
- 费用以模型广场和用量日志为准。Gemini 的图像输出费用与文本费用不同；先生成一张验收，再扩量。
- 当前 Tako 不提供 `/v1/images/tasks/{id}` 轮询、Images 异步任务或批量任务 API。`/v1/images/variations` 返回未实现。

## 排错

| 现象 | 处理 |
| --- | --- |
| `401`，无效令牌 | 检查完整 Key、过期/禁用状态和 Key 剩余额度 |
| `403`，无权访问分组或模型 | 在控制台核对 Key 分组、模型限制和账户权限 |
| 余额/订阅额度不足 | 查看账户和订阅用量，确认计费来源；单独提高 Key 限额不会增加账户额度 |
| `invalid_request` / 参数错误 | 检查模型名、请求结构、张数和图片格式；当前旧版可能把参数错误返回为 `500` |
| `429` / `503` | 查看限流或上游繁忙提示；不要无限重试 |
| 安全拦截、只返回文字、无图片 | 读取错误和 Gemini candidate 的拦截信息，调整提示词 |
| `200` 但 `data` 不存在 | 确认响应协议；Gemini 原生图片在 `candidates` 中 |
| Grok URL 下载超时/被拒 | 生成/改图请求指定 `response_format=b64_json`；不要把 Tako Key 发给图片 CDN |

收到 `200` 后还要确认有图片、能解码、可打开；改图还要对照参考图检查修改效果。
