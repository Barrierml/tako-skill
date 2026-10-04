# 命令与任务示例

先完成[安装和 Key 配置](../docs/getting-started.md)。下面命令从克隆仓库根目录运行；助手按自己的 Skill 安装目录解析脚本路径。

[返回首页](../README.md) · [图片提示词与实际效果](../references/images.md)

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

## 搜索并引用来源

```bash
./scripts/tako-search.sh "capital of Japan" --count 3
```

引用真实返回的 `results[].url`；如果只有 `answer`，明确说明没有来源列表。[参数与响应](../references/search.md)。

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
