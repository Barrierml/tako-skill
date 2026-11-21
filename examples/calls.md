# 命令与任务示例

先完成[安装和 Key 配置](../docs/getting-started.md)。下面命令从克隆仓库根目录运行；助手按自己的 Skill 安装目录解析脚本路径。

[返回首页](../README.md) · [图片示例](../references/images.md) · [视频生成](../references/video.md) · [冰糖语音](../references/audio.md) · [外脑会诊](../references/consult.md)

## 生成图片并保存

```bash
./scripts/tako-image.sh generate "暖色陶瓷马克杯的产品摄影，奶油色背景，清晨侧光，无文字" \
  --model gpt-image-2 --out response.json --save-image output/mug.png
```

交付响应 JSON 和可打开的图片；扩展名按实际格式保存。提示词可直接从[产品、花园、森林例子](../references/images.md#看效果三个生图例子与一次改图)替换。

## 单参考图改色

```bash
./scripts/tako-image.sh edit output/mug.png \
  "只把杯子改成深青绿，保留杯子形状、背景、构图和光线" \
  --model gpt-image-2 --out edited-response.json --save-image output/teal-mug.png
```

输入文件路径要使用前一步实际保存的文件。Gemini 或 Grok 单图编辑可以更换模型，helper 会选择对应协议。

## 多张参考图

对助手说：

```text
使用 tako-skill，根据这两张参考图生成一张新图。
保留第一张图的主体，采用第二张图的背景与配色，说明你使用了哪两份输入。
按 Skill 的多参考图 API 示例调用，不要只取其中一张；保存并打开结果。
```

完整两图请求、输入资产和已验证模型见[多参考图例子](../references/images.md#直接调用多张参考图)。`tako-image.sh edit` 当前不是多文件命令。

## 生成视频并保存

```bash
./scripts/tako-video.sh generate "暖色桌面上的苹果缓慢旋转，简洁摄影，无文字" \
  --duration 5 --resolution 480p --aspect-ratio 16:9 \
  --out video-task.json --save-video output/apple-clip.mp4
```

helper 会提交任务、轮询直到完成再下载 MP4；任务 JSON 先保存，超时可用 `status` 恢复。视频模型为 `grok-imagine-video-1.5`（画质与物理连贯性更好，支持 `1080p`）。图生视频加 `--image` 参考图（可选传）；`--last-frame` 锁尾帧、`--ref-image` 可重复传多参考图保持角色 / 商品一致（prompt 中用 `@image0`、`@image1` 引用）、`--edit-video` 用自然语言编辑已有 MP4、`--extend-video` 无缝续写 2–10 秒。模型与排错见[视频生成](../references/video.md)。

## 冰糖语音合成、情绪控制、克隆与转写

```bash
# 1) 冰糖默认配音（mimo-v2.5-tts）
./scripts/tako-audio.sh tts \
  "在 Tako Switch 一键挂载之后，一句话就能合成有温度的旁白。" \
  --save-audio output/bingtang-warm.mp3 --out output/bingtang-warm.json

# 2) 情绪与语速控制（自动切换 mimo-v2.5-tts-instruct）
./scripts/tako-audio.sh tts \
  "深夜改完最后一行代码，窗外正下着细雨。" \
  --instructions "深夜电台旁白，声音沉静温柔，语速略慢" \
  --format wav --speed 0.92 \
  --save-audio output/bingtang-radio.wav

# 3) 零样本声音克隆（<= 10MB 本地样本，自动切换 mimo-v2.5-tts-voiceclone）
./scripts/tako-audio.sh tts \
  "欢迎来到本周的技术更新速递。" \
  --voice-sample assets/audio/voice-bingtang-warm.mp3 \
  --save-audio output/cloned.mp3

# 4) 语音转写 ASR（speech_asr）
./scripts/tako-audio.sh asr assets/audio/voice-bingtang-warm.mp3 --language zh
```

`--save-audio` 与 `--out` 均拒绝覆盖已有文件；若接口返回非 2xx 或 JSON 错误响应不会写入坏文件。详情见[冰糖语音与克隆](../references/audio.md)。

## 搜索并引用来源

```bash
./scripts/tako-search.sh "capital of Japan" --count 3
```

引用真实返回的 `results[].url`；如果只有 `answer`，明确说明没有来源列表。[参数与响应](../references/search.md)。

## 外脑深度会诊（Second Opinion）

```bash
./scripts/tako-consult.sh \
  "多个桌面客户端同时切入本地统一网关时，端口抢占与配置热更新有哪些竞态盲点？" \
  --context "各客户端启动时都会探测 18419 并直接写配置文件" \
  --focus "单飞探活锁与原子配置替换" \
  --out output/consult-gateway.json
```

默认使用 `gpt-6.2-sol`，可传 `--context-file <path>` 附上代码或日志片段。什么时候用 `tako-consult.sh` vs `tako-systemone.sh` 见[外脑会诊指南](../references/consult.md)。

## System One 判断

```bash
./scripts/tako-systemone.sh "hello" "Is this a greeting?"
```

这条 helper 只发一个 Noul 问题。分类与打分见 [Choice / Score / Noul 完整请求](../references/systemone.md#同时做分类打分和紧急判断)。不使用聊天接口代替。

## 查询用量

用户问“还剩多少额度”时，先执行只读查询：

```bash
./scripts/tako-usage.sh token
./scripts/tako-usage.sh billing
```

前者看当前 Key 的 `total_available`，后者看订阅窗口和聚合消费；不要把两套数值相加。字段含义和错误处理见 [用量与额度](../references/usage.md)。
