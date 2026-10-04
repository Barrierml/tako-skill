# 快速开始

先准备 Tako 用户 Key，安装 Skill，再完成一次能看到结果的任务。图片请求有真实额度消费，首次先生成一张。

[返回首页](../README.md) · [图片示例](../references/images.md) · [常见问题](troubleshooting.md)

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
npx skills add Barrierml/tako-skill --skill tako-skill
```

默认安装在项目；加 `-g` 安装到个人目录。指定工具的例子：

```bash
# Claude Code，全局安装
npx skills add Barrierml/tako-skill --skill tako-skill -a claude-code -g

# Codex，全局安装
npx skills add Barrierml/tako-skill --skill tako-skill -a codex -g
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
git clone https://github.com/Barrierml/tako-skill.git
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

## 3. 试试改图或其他任务

修改刚才保存的图片（若实际扩展名不同，替换输入路径）：

```bash
./scripts/tako-image.sh edit output/apple.png \
  "只把苹果改成绿色，保留位置、形状、桌面和光照" \
  --out edited-response.json --save-image output/green-apple.png
```

每次修改都会消费新的额度。参考图越多，越要明确各图用途；目前 helper 只收一张，多图用[直接 API 示例](../references/images.md#直接调用多张参考图)。

- 看漂亮效果：[图片与完整提示词](../references/images.md#看效果三个生图例子与一次改图)。
- 找资料并引用来源：[网页搜索](../references/search.md)。
- 分类、路由、打分：[System One](../references/systemone.md)。
- Key、权限或保存失败：[常见问题](troubleshooting.md)。
