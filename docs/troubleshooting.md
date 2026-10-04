# 常见问题

[返回首页](../README.md) · [快速开始](getting-started.md) · [图片 API 排错](../references/images.md#排错)

## 安装了，但助手没有使用 Skill

先明确说“使用 tako-skill”，确认安装给了当前 AI 工具和当前项目/个人目录。全局安装可用 `npx skills ls -g` 查看；刚更新时刷新 Skill 列表或重启会话。

也可以让助手直接读取本地克隆目录的 `SKILL.md`。安装 Skill 不会自动配置 API Key，仍需在启动助手的进程环境里设置它。

## 配置了 Key，为什么仍提示没有 Key

检查运行 helper 或启动助手的终端有没有设置 `TAKO_API_KEY`。另一个终端、已启动的桌面进程不会自动继承刚设置的变量。复制完整 Key，不要把 `cr_` 或 `sk-` 当作通用固定前缀替换。

## 出现 401、403 或额度不足

| 现象 | 先查什么 |
| --- | --- |
| 401 | Key 是否完整、过期、禁用 |
| 403 | Key 分组、模型限制、账户权限 |
| 余额或订阅额度不足 | 账户/订阅用量及计费来源 |
| 提高 Key 限额后仍失败 | Key 限额不会增加账户或订阅本身的额度 |

不要在日志、截图或求助消息里展示完整 Key。

## 请求成功，却没有收到图片文件

HTTP 200 只说明请求层面成功，还要检查有图片内容、能解码、能打开。推荐同时使用 `--out` 和 `--save-image`：前者保存响应，后者保存实际图片。

图片可能是 JPEG 或 WebP，即使你指定 `.png`，helper 也会改成真实扩展名；以它输出的保存路径为准。Grok 用 base64 避免单独下载 CDN；Gemini 原生图片位于 `candidates`，Images 兼容响应位于 `data`。

## 超时或保存失败，要不要重新生成

先查看用量日志和已保存响应。图片调用不会自动重试；超时可能已经消费额度，重复请求可能再次扣费。

如果响应里已有 `b64_json`，按[解码示例](../references/images.md#直接调用生成图片)从响应保存即可；下载或保存失败不需要重新生成。已有图片不会覆盖，换一个保存路径。

## 能用多张参考图吗

API 可以；当前游乐场和 helper 仍只接收一张。GPT Image 2、Gemini Flash Image、Grok Image Quality 均已实测两图共同生效；Grok 当前链路最多三张，GPT/Gemini 最大张数未验证。

查看[两图输入、实际结果及完整请求](../references/images.md#直接调用多张参考图)。`n` 控制结果张数，和参考图数量无关。

## 搜索成功，但没有来源列表

部分 provider 可能只返回 `answer`，`results` 为空不一定是失败。有 `results[].url` 时引用它，没有时不要编造来源。参数与例子见[搜索文档](../references/search.md)。

## System One 为什么不能写文章，或模型列表里找不到

System One 用来做 Choice / Score / Noul 判断，不是聊天或内容生成。直接调用 `/v1/systemone`，默认 `jev-latest`；不要依赖 `/v1/models` 发现它。公共模型定价目录在 2026-10-04 能看到 `jev-latest`，这不代表它支持聊天接口。

helper 只发一个 Noul 问题；Choice、Score 和多个问题请使用[完整请求例子](../references/systemone.md)。

## 语音、视频、蒙版或异步任务在哪里

当前 Skill 没有语音、视频、图片异步任务/轮询或 variations 工作流。蒙版、透明背景、所有尺寸/质量组合也没有在各模型上全面验证。不要把上游或旧版 PAR 的能力直接当作 Tako 已支持；图片边界见[模型与接口指南](../references/images.md#参数费用与限制)。
