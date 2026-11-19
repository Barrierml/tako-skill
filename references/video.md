# 08 — Grok 视频生成

用同一把 Tako 用户 API Key，可以通过 Grok 渠道生成视频：文字直接生成视频，或以一张参考图生成图生视频。视频任务是异步的：先提交任务拿到 task id，再轮询状态，最后下载 MP4。视频请求会消耗账户或订阅额度，费用随模型、分辨率和时长变化，以模型广场与用量日志为准。

`grok-imagine-video-1.5` 还支持四项高阶能力：首尾帧插值（`--last-frame`）、多参考图一致性（`--ref-image` 可重复）、自然语言视频编辑（`--edit-video`）与无缝续写（`--extend-video`），下文分节说明。

## 准备 API Key

与图片相同：在 [Tako 控制台](https://tako.shiroha.tech)创建用户 Key，在运行命令的终端设置 `TAKO_BASE_URL` 和完整的 `TAKO_API_KEY`。Key 的分组和模型权限必须允许视频模型。

## 视频模型

| 模型 | 文生视频 | 图生视频 | 首尾帧 | 多参考图 | 视频编辑 | 无缝续写 | 分辨率 | 时长 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `grok-imagine-video-1.5` | 支持 | 支持（参考图可选） | 支持 | 支持 | 支持 | 支持 | `480p`（默认）、`720p`、`1080p` | 生成/编辑 1–15 秒，续写 2–10 秒 |

helper 始终使用 `grok-imagine-video-1.5`：画质与物理连贯性更好，支持 `1080p`。

- `aspect_ratio` 可选，例如 `16:9`、`9:16`、`1:1`。
- 参考图可以传本地文件（helper 编码为 `data:image/...;base64,...`）或公网 URL；参考图为可选，不传即为文生视频。
- 视频生成排队与渲染耗时明显长于图片；helper 默认最长等待 20 分钟，可用 `--max-wait` 调整。

## 最快方式：使用 Tako Skill helper

需要 Git、Bash、Python 3。helper 只依赖 Python 标准库。

```bash
git clone https://github.com/Barrierml/tako-skill.git
cd tako-skill

# 文生视频：提交后自动轮询，成功后保存 task JSON 和 MP4
./scripts/tako-video.sh generate "一颗红苹果在白色桌面上缓慢旋转，简洁摄影，无文字" \
  --duration 5 --resolution 480p --aspect-ratio 16:9 \
  --out task.json --save-video output/apple-clip.mp4

# 图生视频：用刚才生成的图片做参考
./scripts/tako-video.sh generate "镜头缓慢推近，画面轻微移动" \
  --model grok-imagine-video-1.5 --resolution 720p \
  --image output/apple.png --duration 8 \
  --out i2v-task.json --save-video output/apple-motion.mp4
```

`--out` 保存提交响应（含 task id），`--save-video` 保存成品 MP4；已有文件不会被覆盖，实际保存路径以 helper 输出为准。提交响应会先落盘：即使轮询超时或失败，也能凭 `--task-json` 恢复任务，不需要重复付费提交。

## 高阶能力

### 首尾帧插值 `--last-frame`

`--last-frame` 锁定视频的尾帧，与 `--image`（首帧）同时传入时生成首尾帧之间的过渡动画；此时 prompt 可选（不写则由模型推断中间过程）。本地图片自动编码为 `data:image/...;base64,...`，也可以直接传公网 URL。

```bash
./scripts/tako-video.sh generate "镜头从开场平滑过渡到结尾" \
  --image output/first.png --last-frame output/last.png \
  --duration 6 --out frames-task.json --save-video output/transition.mp4
```

### 多参考图一致性 `--ref-image`

`--ref-image` 可重复传多次（本地文件或公网 URL），用于保持角色 / 商品 / 风格的一致性。请求同时写入 `reference_images` 与 `reference_image_urls` 数组；在 prompt 中用 `@image0`、`@image1`（按传入顺序）显式引用对应参考图。

```bash
./scripts/tako-video.sh generate "@image0 中的角色穿着 @image1 的外套走向镜头" \
  --ref-image refs/hero.png --ref-image refs/jacket.png \
  --duration 8 --out refs-task.json --save-video output/consistent.mp4
```

### 视频编辑 `--edit-video`

基于已有 MP4 做自然语言风格 / 元素编辑。`--edit-video` 接受本地 MP4（≤20MB 自动编码为 `data:video/mp4;base64,...`，更大文件请先上传为公网 URL）或视频 URL，prompt 必填。helper 提交到 `/v1/videos/edits` 并写入 `mode: "edit"` + `video` 字段。

```bash
./scripts/tako-video.sh generate "把背景改成日落时分的海边，保留人物动作" \
  --edit-video output/transition.mp4 \
  --out edit-task.json --save-video output/edited.mp4
```

### 无缝续写 `--extend-video`

从已有视频的最后一帧无缝往后续写，`--duration` 取 2–10 秒，prompt 必填。helper 提交到 `/v1/videos/extensions` 并写入 `mode: "extend"` + `video` 字段。

```bash
./scripts/tako-video.sh generate "镜头继续向前推进，人群欢呼" \
  --extend-video output/edited.mp4 --duration 5 \
  --out extend-task.json --save-video output/extended.mp4
```

`--edit-video` 与 `--extend-video` 互斥，且不能与 `--image` / `--last-frame` / `--ref-image` 同用。

恢复或检查一个已有任务：

```bash
# 只查看状态
./scripts/tako-video.sh status task-id-xxx

# 用提交时保存的 JSON 定位任务
./scripts/tako-video.sh status --task-json task.json

# 任务成功后单独下载 MP4
./scripts/tako-video.sh status task-id-xxx --save-video output/clip.mp4
```

任务尚未完成时 `status --save-video` 会报错退出而不下载。视频调用不会自动重试：超时或失败后先查看 `--out` 保存的任务 JSON 与用量日志，能用 `status` 恢复就不要重新提交。

## 直接调用 API

### 1. 提交任务

```bash
curl --fail-with-body -sS --max-time 240 "$TAKO_BASE_URL/v1/videos/generations" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  --output task.json \
  -d '{
    "model": "grok-imagine-video-1.5",
    "prompt": "一颗红苹果在白色桌面上缓慢旋转，简洁摄影，无文字",
    "duration": 5,
    "resolution": "480p",
    "aspect_ratio": "16:9"
  }'
```

成功响应包含任务 id（`id` 或 `task_id`）。图生视频在请求体中加入 `image`：公网 URL，或 `data:image/png;base64,...` 形式的 data URL。其它高阶字段：

- `last_frame`：尾帧图片（URL 或 data URL），与 `image` 同传即首尾帧插值，此时 `prompt` 可省略。
- `reference_images` / `reference_image_urls`：多参考图数组，元素为 `{"url": ...}` 或 URL 字符串；prompt 中以 `@image0`、`@image1` 引用。
- 视频编辑：`POST /v1/videos/edits`，请求体带 `"mode": "edit"` 与 `"video": {"url": ...}`（MP4 URL 或 data URL），`prompt` 必填。
- 无缝续写：`POST /v1/videos/extensions`，请求体带 `"mode": "extend"` 与 `"video": {"url": ...}`，`duration` 取 2–10 秒，`prompt` 必填。

```bash
python3 - <<'PY'
import base64, json
from pathlib import Path
payload = {
    "model": "grok-imagine-video-1.5",
    "prompt": "镜头缓慢推近，画面轻微移动",
    "duration": 8,
    "resolution": "720p",
    "image": "data:image/png;base64," + base64.b64encode(Path("input.png").read_bytes()).decode(),
}
Path("i2v-request.json").write_text(json.dumps(payload))
PY
curl --fail-with-body -sS --max-time 240 "$TAKO_BASE_URL/v1/videos/generations" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @i2v-request.json --output task.json
```

### 2. 轮询状态

```bash
TASK_ID=$(python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path("task.json").read_text())
print(payload.get("id") or payload["task_id"])
PY
)
curl -sS --max-time 60 "$TAKO_BASE_URL/v1/videos/$TASK_ID" \
  -H "Authorization: Bearer $TAKO_API_KEY" --output status.json
```

状态字段为 `status`（或 `state`）：`SUCCESS` / `succeeded` / `done` 表示完成，`FAILURE` / `failed` 表示失败并应读取错误信息。未完成时每隔数秒重查，不要高频轮询。

### 3. 下载视频

```bash
curl --fail-with-body -sS --max-time 240 "$TAKO_BASE_URL/v1/videos/$TASK_ID/content" \
  -H "Authorization: Bearer $TAKO_API_KEY" --output clip.mp4
```

返回可能是 MP4 字节，也可能是包含视频 URL 的 JSON。是 URL 时用不带鉴权头的 `curl` 单独下载：不要把 Tako Key 发给视频 CDN，也不要跟随把凭据带走的重定向。保存后确认文件非空、能以 `ftyp` 开头的 MP4/MOV 结构打开。

## 参数、费用与限制

- `duration` 为整数秒，生成与编辑 1–15，续写 2–10。`resolution` 仅 `480p`/`720p`/`1080p`；helper 固定提交 `grok-imagine-video-1.5`。
- `grok-imagine-video-1.5` 支持文生视频和图生视频，参考图为可选；`--last-frame` 锁尾帧、`--ref-image` 传多参考图、`--edit-video` 改已有视频、`--extend-video` 续写已有视频。
- 本地视频入参限 20MB（编码进请求体）；更大的素材先传到公网 URL 再引用。
- 视频费用按模型、分辨率与时长计费，明显贵于单张图片；先跑一条 480p 短视频验收，再扩分辨率与时长。
- 生成结果是模型按提示词采样，不能逐帧保证与参考图一致；在提示词里写清主体、镜头运动和必须保留的元素。
- 审核或上游失败时任务状态会变成失败；读取状态 JSON 中的错误说明，调整提示词后重新提交是一次新的付费请求。
- 当前 Tako 不提供视频批量接口或队列管理接口；每个 `generate` 只提交一个任务。

## 排错

| 现象 | 处理 |
| --- | --- |
| `401`，无效令牌 | 检查完整 Key、过期/禁用状态和 Key 剩余额度 |
| `403`，无权访问分组或模型 | 在控制台核对 Key 分组和视频模型权限 |
| 余额/订阅额度不足 | 查看账户和订阅用量；视频按秒计费，成本高于图片 |
| 参数错误 / `invalid_request` | 检查模型名、`duration` 1–15 整数、`resolution` 组合（`1080p` 仅 `grok-imagine-video-1.5`）；旧名 `grok-imagine-video` 会被 helper 自动当作 `grok-imagine-video-1.5` |
| 一直 `PENDING`/`RUNNING` | 增加 `--max-wait`，或保存 task id 后稍后用 `status` 恢复 |
| 任务 `FAILURE` | 读取状态 JSON 的错误信息；调整提示词，重新提交按新任务计费 |
| 下载到的不是 MP4 | 确认任务已成功且响应不是错误 JSON；`--save-video` 会校验 `ftyp` 头 |
| 输出文件已存在 | helper 不覆盖已有文件，换一个新的 `--save-video` 路径 |
