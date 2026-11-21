# 快速开始

先准备 Tako 用户 Key，安装 Skill，再完成一次能看到结果的任务。图片、视频、语音与会诊请求都会消耗真实额度，首次先用最小任务验收。

[返回首页](../README.md) · [图片示例](../references/images.md) · [视频生成](../references/video.md) · [冰糖语音](../references/audio.md) · [外脑会诊](../references/consult.md) · [常见问题](troubleshooting.md)

> **桌面客户端懒人方式**：如果你在 macOS / Windows 上使用 **Claude Desktop**、**Codex Desktop** 或 **Google Antigravity**，可以直接安装 [Tako Switch](https://tako.shiroha.tech/tako-switch) 一键挂载内置 **6 合 1 超级 MCP**（生图、视频、冰糖语音、联网、外脑、额度查询全部开箱即用）。

## 1. 准备账户和 Key

登录 [Tako 控制台](https://tako.shiroha.tech)，在密钥管理创建用户 API Key。确认账户或订阅有额度，Key 的分组和模型限制允许目标模型。

在你将用来启动 AI 助手或 helper 的终端配置：

```bash
export TAKO_BASE_URL="https://tako.shiroha.tech"
export TAKO_API_KEY="YOUR_COMPLETE_TAKO_USER_KEY"
```

把占位符换成控制台复制的完整 Key，保留原前缀；不要提交到仓库或发送到聊天。配置后需要从同一终端启动助手，已运行的进程不会自动获得新环境变量。

`TAKO_BASE_URL` 是根域，不带 `/v1`；脚本会自行添加路径。只有 OpenAI SDK 的 `base_url` 通常要带 `/v1`。

## 安装与更新

### 使用 Skill 安装器

需要 Node.js/npm，也可以使用 Bun。先执行交互安装，选择实际使用的 AI 工具：

```bash
npx skills add tako-dev/tako-skill --skill tako-skill
```

默认安装在项目；加 `-g` 安装到个人目录。指定工具的例子：

```bash
# Claude Code，全局安装
npx skills add tako-dev/tako-skill --skill tako-skill -a claude-code -g

# Codex，全局安装
npx skills add tako-dev/tako-skill --skill tako-skill -a codex -g
```

安装后，在相应工具中明确说“使用 tako-skill”。如果没有被发现，可以直接让助手读取本地 `SKILL.md`；不要把 API Key 写进提示词。

查看和更新已安装的全局副本：

```bash
npx skills ls -g
npx skills update tako-skill -g
```

项目副本用 `npx skills update tako-skill -p`。以上命令来自 [skills 安装器文档](https://github.com/vercel-labs/skills#skills-update)；使用 Bun 时把 `npx` 换成 `bunx`。刷新助手的 Skill 列表或重启会话，使其读取更新。

### 直接克隆并使用 helper

需要 Git、Bash、Python 3、curl；不需要安装 Python 第三方包或 OpenAI SDK：

```bash
git clone https://github.com/tako-dev/tako-skill.git
cd tako-skill
```

助手可以读取克隆目录中的 `SKILL.md`。Claude Code 项目安装也可将仓库克隆到 `.claude/skills/tako-skill`。

更新自己克隆的副本，在该目录执行：

```bash
git pull --ff-only
```

如果有本地修改导致拉取失败，先保留自己的修改再处理；不用覆盖或删除目录。

## 2. 完成第一次生图

先在这个终端配置前面的 Key，再运行：

```bash
./scripts/tako-image.sh generate "白色桌面上的红苹果，简洁摄影，无文字" \
  --model gpt-image-2 --out response.json --save-image output/apple.png
```

成功时会保存 `response.json`，并输出 `Saved image: output/apple.png` 等实际路径。扩展名以返回图片格式为准。打开图片检查后再使用；已有输出文件不会被覆盖，再次生成要换一个保存路径。

若通过 AI 助手使用，可以发：

```text
使用 tako-skill，生成一张白色桌面上的红苹果图片，使用 gpt-image-2。
保存响应 JSON 和图片，打开确认后把图片给我，不要打印 API Key。
```

助手会按自己的 Skill 安装目录运行 helper，命令路径不一定是当前项目的 `./scripts/`。

## 3. 试试改图、视频、语音或外脑会诊

修改刚才保存的图片（若实际扩展名不同，替换输入路径）：

```bash
./scripts/tako-image.sh edit output/apple.png \
  "只把苹果改成绿色，保留位置、形状、桌面和光照" \
  --out edited-response.json --save-image output/green-apple.png
```

每次修改都会消费新的额度。参考图越多，越要明确各图用途；目前图片 helper 只收一张，多图用[直接 API 示例](../references/images.md#直接调用多张参考图)。

生成一段短视频（任务异步执行，helper 会轮询并保存 MP4；视频按秒计费，先用 480p 短时长验收）：

```bash
./scripts/tako-video.sh generate "白色桌面上的红苹果缓慢旋转，简洁摄影，无文字" \
  --duration 5 --resolution 480p \
  --out video-task.json --save-video output/apple-clip.mp4
```

也可以把刚才的图片作为参考图做图生视频：`--image output/apple.png`（可选传）。视频模型为 `grok-imagine-video-1.5`，画质更好且支持 1080p。

合成一段默认「冰糖」语音并试跑转写：

```bash
./scripts/tako-audio.sh tts "你好，欢迎体验 Tako 冰糖语音合成。" \
  --save-audio output/hello-bingtang.mp3 --out output/hello-bingtang.json
./scripts/tako-audio.sh asr output/hello-bingtang.mp3 --language zh
```

发起一次跨模型架构/代码外脑会诊（默认 `gpt-6.2-sol`）：

```bash
./scripts/tako-consult.sh "异步任务超时重试与支付回调并发到达时，怎样避免重复扣费？" \
  --focus "幂等键与状态单调性" --out output/consult.json
```

- 看漂亮效果：[图片与完整提示词](../references/images.md#看效果三个生图例子与一次改图)。
- 视频模型、轮询与恢复：[视频生成](../references/video.md)。
- 冰糖配音、情绪控制、声音克隆与 ASR：[冰糖语音与克隆](../references/audio.md)。
- 找资料并引用来源：[网页搜索](../references/search.md)。
- 外脑深度会诊与对比选型：[外脑会诊](../references/consult.md)。
- 分类、路由、打分：[System One](../references/systemone.md)。
- Key、权限或保存失败：[常见问题](troubleshooting.md)。
