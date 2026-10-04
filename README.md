# Tako Skill

让你的 AI 助手搜索资料、生成和修改图片，以及完成分类、打分等结构化判断。使用同一个 Tako 用户 API Key，按需调用对应能力。

[快速开始](docs/getting-started.md) · [用量与额度](references/usage.md) · [图片与提示词](references/images.md) · [常见问题](docs/troubleshooting.md) · [Tako 控制台](https://tako.shiroha.tech)

![经 Tako 实际生成的陶瓷产品摄影、微缩花园插画与森林木屋](assets/images/examples-preview.webp)

上图分别使用 GPT Image 2、flare、sunburst 生成。[查看模型、完整提示词和可运行命令](references/images.md#看效果三个生图例子与一次改图)。每次请求消耗账户或订阅额度，再次生成的结果可能不同。

## 可以用它做什么

| 你想做的事 | 可以对助手这样说 | 你会得到什么 |
| --- | --- | --- |
| 查询用量 | “查看我当前 Tako Key 还剩多少额度，并说明模型限制。” | 当前 Key 的已用/可用额度、权限和过期信息 |
| 搜索资料 | “用 Tako 搜索这家公司的最新资料，并附上来源链接。” | 搜索回答；有来源时附引用链接 |
| 生成图片 | “用 Tako 生成一张暖色陶瓷杯产品图，保存图片给我。” | 可打开的图片文件 |
| 修改图片 | “把这张图的杯子改成深青绿，保留背景、构图和光线。” | 基于参考图的修改结果 |
| 使用多张参考图 | “用第一张图的主体和第二张图的场景生成一张图。” | 多参考图 API 请求；[已验证范围](references/images.md#直接调用多张参考图) |
| 分类与打分 | “用 System One 判断这份工单应该给哪个团队、是否紧急。” | Choice / Score / Noul 结构化判断 |

## 安装并开始

需要已有的 Tako 账户和用户 API Key。安装器使用 Node.js/npm；也可以把下方 `npx` 换成 `bunx`。

```bash
npx skills add Barrierml/tako-skill --skill tako-skill
```

按安装器提示选择你的 AI 工具。支持项目安装，也可加 `-g` 安装到个人目录。[指定 Claude Code / Codex、直接克隆和更新方法](docs/getting-started.md#安装与更新)。

在启动 AI 助手的同一个终端配置环境变量；Key 要复制控制台中的完整值，保留原前缀：

```bash
export TAKO_BASE_URL="https://tako.shiroha.tech"
export TAKO_API_KEY="YOUR_COMPLETE_TAKO_USER_KEY"
```

把下面这段话发给助手，先拿到一张图：

```text
使用 tako-skill，生成一张暖色陶瓷马克杯的产品摄影。
使用 gpt-image-2，把响应 JSON 和图片分别保存到 output/。
打开图片确认生成成功，再把图片给我；不要打印 API Key。
```

成功时应得到一份响应 JSON 和一张可以打开的图片。仅有 HTTP 200、模型回答“已生成”或一段 base64 都不算交付完成。

## 也可以直接运行命令

已有 Git、Bash、Python 3 和 curl 时，可以克隆仓库使用 helper，不依赖 AI 工具的 Skill 安装机制：

```bash
git clone https://github.com/Barrierml/tako-skill.git
cd tako-skill
# 在这个终端配置上面的 TAKO_API_KEY 后执行
./scripts/tako-image.sh generate "白色桌面上的红苹果，简洁摄影，无文字" \
  --out response.json --save-image output/apple.png
```

输出会显示保存路径；文件扩展名以实际图片格式为准。更多[生图、改图、搜索和判断命令](examples/calls.md)。

## 效果与提示词

- [产品摄影](references/images.md#产品摄影温暖的陶瓷马克杯)：描述材质、光线和留白。
- [3D 花园插画](references/images.md#3d-插画云上的微缩花园)：描述视角、配色和材质。
- [森林木屋](references/images.md#风景摄影清晨的森林木屋)：描述时间、天气和场景。
- [杯子改色](references/images.md#改图对照只改变杯子的颜色)：明确改变什么、保留什么。
- [双参考图](references/images.md#直接调用多张参考图)：查看两个输入与三个模型的实际输出。

## 按任务查文档

| 文档 | 什么时候看 |
| --- | --- |
| [快速开始](docs/getting-started.md) | 安装、设置 Key、第一次使用、更新旧版本 |
| [用量与额度](references/usage.md) | 查询当前 Key、订阅窗口、聚合消费和重试前检查 |
| [图片生成与改图](references/images.md) | 模型选择、提示词、单图/多图、接口、解码和保存 |
| [网页搜索](references/search.md) | 搜索参数、provider、回答与来源链接 |
| [System One](references/systemone.md) | Choice / Score / Noul 请求及读取 `answers` |
| [命令与任务示例](examples/calls.md) | 复制一条命令或给助手一段具体任务 |
| [常见问题](docs/troubleshooting.md) | Skill 没触发、Key/额度报错、图片没保存、多图怎么调用 |
| [SKILL.md](SKILL.md) | AI 助手的任务路由、调用与交付规则 |

## 当前能力边界

图片核验日期：**2026-10-04**。六个模型均验证了生图和可用的单图编辑路径；具体接口与限制见图片指南。搜索和 System One 的说明来自既有契约与历史记录，本轮图片核验没有重新测试这两项。

- **多图 API 已有可用路径，helper / 游乐场仍只收一张参考图。** 两张参考图已在 GPT Image 2、Gemini Flash Image、Grok Image Quality 实测；Grok 当前链路最多三张，GPT/Gemini 最大数量未验证。
- 图片编辑会重绘，不能保证区域外每个像素保持不变；蒙版、多图精确保留和所有尺寸/质量组合没有跨模型全面验证。
- 当前 Skill 不提供视频、语音、图片异步任务轮询或 variations 工作流。
- Key 的分组、模型权限、额度会影响你能调用的模型。超时或保存失败时先检查响应与用量，避免重复付费生成。

本仓库旧名 `Barrierml/agent-skills` 已重定向到此处；新安装使用 `Barrierml/tako-skill`。更新命令见快速开始。

国内访问镜像的部署文件在 [`deploy/cn-mirror`](deploy/cn-mirror/README.md)，镜像上线后可从服务器域名获取文档和完整压缩包。

[MIT License](LICENSE)
