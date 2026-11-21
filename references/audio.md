# 冰糖语音合成、声音克隆与语音转写

用同一把 Tako 用户 API Key，可以通过 Speech API 完成**冰糖默认配音**、**情绪/语速/口吻指令控制**、**零样本声音克隆**以及**高精度语音转写（ASR）**。音频请求会消耗账户或订阅额度，费用以模型广场与用量日志为准。

[返回首页](../README.md) · [快速开始](../docs/getting-started.md) · [外脑会诊](consult.md) · [常见问题](../docs/troubleshooting.md)

## 模型与能力一览

| 能力 | 模型 | 端点 | Helper 子命令 / 关键参数 |
| --- | --- | --- | --- |
| 冰糖默认配音（TTS） | `mimo-v2.5-tts` | `POST /v1/audio/speech` | `tako-audio.sh tts "<text>"`（默认 `voice="冰糖"`、`--format mp3`） |
| 情绪 / 语速 / 口吻控制 | `mimo-v2.5-tts-instruct` | `POST /v1/audio/speech` | 传 `--instructions` 且未显式指定 `--model` 时自动切换 |
| 零样本声音克隆 | `mimo-v2.5-tts-voiceclone` | `POST /v1/audio/speech` | 传 `--voice-sample <file>`（≤ 10 MiB）且未显式指定 `--model` 时自动切换 |
| 语音转写（ASR） | `speech_asr` | `POST /v1/audio/transcriptions` | `tako-audio.sh asr <audio_file>`（可选 `--language`、`--prompt`） |

> 显式传入 `--model` 时，helper 始终尊重用户选择，不会静默替换模型。

## 冰糖真声实景试听（3 段真实 `mimo-v2.5-tts` 输出）

仓库 [`assets/audio/`](../assets/audio/) 收录了 3 段由 Tako `mimo-v2.5-tts` 实际生成的冰糖语音资产（与 [Tako Switch](https://tako.shiroha.tech/tako-switch) 内置实景剧场同源），可直接点击本地试听或用下面命令复现同类配音：

| 风格 | 试听音频 | 对应台词 | 可运行命令 |
| --- | --- | --- | --- |
| 🌤 温柔叙述 | [voice-bingtang-warm.mp3](../assets/audio/voice-bingtang-warm.mp3) | “在 Tako Switch 一键挂载之后，不管是写方案、做产品原型，还是给视频配一段有温度的旁白，一句话就能直接合成出来。” |见下方「1. 冰糖默认配音」 |
| ⚡ 灵动解说 | [voice-bingtang-lively.mp3](../assets/audio/voice-bingtang-lively.mp3) | “嗨！现在的演示已经不是冷冰冰的参数表啦，你可以直接左右拖动改图滑块，或者改一句词，马上体验现场真跑的效果！” | 见下方「2. 情绪与口吻指令控制」 |
| 🌙 深夜电台 | [voice-bingtang-radio.mp3](../assets/audio/voice-bingtang-radio.mp3) | “深夜改完最后一行代码，窗外正下着细雨。把繁琐的配置留给本地网关，把专注留给你真正想创造的作品。” | 见下方「2. 情绪与口吻指令控制」 |

## 最快方式：使用 `tako-audio.sh`

需要 Git、Bash、Python 3（仅使用标准库，无需安装额外依赖）。在已配置 `TAKO_API_KEY` 的 Skill 根目录运行：

### 1. 冰糖默认配音（`mimo-v2.5-tts`）

```bash
./scripts/tako-audio.sh tts \
  "在 Tako Switch 一键挂载之后，不管是写方案、做产品原型，还是给视频配一段有温度的旁白，一句话就能直接合成出来。" \
  --save-audio output/bingtang-warm.mp3 \
  --out output/bingtang-warm.json
```

- 默认参数：`--model mimo-v2.5-tts`、`--voice 冰糖`、`--format mp3`。
- `--save-audio` 必填且**拒绝覆盖已有文件**；helper 会校验 HTTP 2xx、非空字节且不是 `{` 开头的 JSON 错误响应后再原子落盘。
- `--out` 可选保存元数据 JSON，记录 `saved_path`、`model`、`voice`、`response_format`、`bytes` 以及响应头 `x-speech-final-text-preview`。

### 2. 情绪、语速与口吻控制（`mimo-v2.5-tts-instruct`）

传入 `--instructions` 且未显式传 `--model` 时，helper 自动切换到 `mimo-v2.5-tts-instruct`；支持 `--format mp3|wav|opus` 与可选 `--speed`：

```bash
# ⚡ 灵动解说风格
./scripts/tako-audio.sh tts \
  "嗨！现在的演示已经不是冷冰冰的参数表啦，你可以直接左右拖动改图滑块，或者改一句词，马上体验现场真跑的效果！" \
  --instructions "轻快活泼的年轻女声解说，节奏明快、有互动感" \
  --format mp3 \
  --save-audio output/bingtang-lively.mp3

# 🌙 深夜电台风格（WAV 无损输出 + 稍慢语速）
./scripts/tako-audio.sh tts \
  "深夜改完最后一行代码，窗外正下着细雨。把繁琐的配置留给本地网关，把专注留给你真正想创造的作品。" \
  --instructions "深夜电台旁白，声音沉静温暖，语速略慢，带轻微气声停顿" \
  --format wav --speed 0.92 \
  --save-audio output/bingtang-radio.wav \
  --out output/bingtang-radio.json
```

### 3. 零样本声音克隆（`mimo-v2.5-tts-voiceclone`）

传入本地参考音频 `--voice-sample`（支持 `.mp3` / `.wav` / `.opus` / `.m4a` / `.flac` 等常见格式，文件大小不得超过 `10485760` 字节 = 10 MiB）且未显式指定 `--model` 时，helper 自动切换到 `mimo-v2.5-tts-voiceclone`，并将参考音频编码为 `data:<audio-mime>;base64,...` 写入请求体 `voice` 字段：

```bash
./scripts/tako-audio.sh tts \
  "欢迎来到本周的技术更新速递，今天我们来看看跨模型外脑会诊的实战案例。" \
  --voice-sample assets/audio/voice-bingtang-warm.mp3 \
  --format mp3 \
  --save-audio output/cloned-briefing.mp3 \
  --out output/cloned-briefing.json
```

> 请仅使用获得明确授权的说话人样本进行声音克隆。

### 4. 语音转写 ASR（`speech_asr`）

使用 `asr` 子命令上传本地音频文件到 `POST /v1/audio/transcriptions`（multipart 表单），输出识别出的 `text` 字段；可选 `--language`、`--prompt` 与 `--out` 保存完整响应 JSON：

```bash
./scripts/tako-audio.sh asr assets/audio/voice-bingtang-warm.mp3 \
  --language zh \
  --prompt "Tako Switch, MCP" \
  --out output/asr-warm.json
```

## 直接调用 API

### TTS (`POST /v1/audio/speech`)

```bash
curl --fail-with-body -sS --max-time 120 "$TAKO_BASE_URL/v1/audio/speech" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  --output output/bingtang.mp3 \
  -d '{
    "model": "mimo-v2.5-tts",
    "input": "你好，这是来自 Tako Speech API 的冰糖配音。",
    "voice": "冰糖",
    "response_format": "mp3"
  }'
```

### ASR (`POST /v1/audio/transcriptions`)

```bash
curl --fail-with-body -sS --max-time 120 "$TAKO_BASE_URL/v1/audio/transcriptions" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -F "model=speech_asr" \
  -F "language=zh" \
  -F "file=@./assets/audio/voice-bingtang-warm.mp3"
```

## 交付与恢复规则

- TTS 仅在得到非空、非 JSON 错误且校验通过的本地音频文件后才算交付完成；不要直接覆盖已有音频或元数据文件。
- 收到 HTTP 非 2xx 或 JSON 错误响应时，helper 会直接报错并保持目标路径干净，不会写入坏文件。
- 语音请求不自动重试；若超时或怀疑重复计费，先运行 `./scripts/tako-usage.sh token` 检查当前 Key 额度与消费记录。
