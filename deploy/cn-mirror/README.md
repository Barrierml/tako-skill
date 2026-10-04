# Tako Skill 国内镜像

这个目录描述国内镜像的同步和静态服务，不改变 Skill 本身的调用协议。

## 目标链路

```text
GitHub Barrierml/tako-skill main
  → mirror host `.12` 定时执行 sync.sh（原子切换 current）
  → nginx:8098 只读静态目录
  → Kong host `tako-skill.shiroha.tech`
  → 国内用户访问 README、SKILL、参考文档和完整 tar.gz
```

建议入口：`https://tako-skill.shiroha.tech/`。域名使用 DNS-only A 记录指向 `47.243.90.99`，源站在 hongkong-c9i；先以直连稳定性验收，再决定是否开启 Cloudflare proxy。镜像内容是公开仓库文件，不放 Key、日志或运行时账户数据。

## 同步纪律

`sync.sh` 从 GitHub codeload 下载指定 ref，检查 README/SKILL，尽力读取 commit SHA，写入版本目录和 `latest.json`，再用临时 symlink 原子切换 `current`。下载失败保留上一个版本；默认保留 3 个版本。`flock` 避免 cron 重入。压缩包和 SHA-256 一起发布。

示例（服务器上）：

```bash
install -d -m 0755 /srv/tako-skill-mirror
TAKO_SKILL_MIRROR_ROOT=/srv/tako-skill-mirror ./sync.sh
# 每 15 分钟执行一次；生产接入时放 systemd timer 或 cron
```

## 发布前验收

- `GET /` 返回镜像首页，含当前提交号。
- `/README.md`、`/SKILL.md`、`/docs/getting-started.md`、`/references/usage.md` 和 tar.gz 均返回 200。
- `GET /latest.json` 不被长缓存；文档/包使用短缓存并带 `stale-while-revalidate`。
- 下载包 SHA-256 与 `.sha256` 一致，包内包含 README、SKILL、scripts、docs、references、examples、assets。
- GitHub 暂时不可访问时，服务器继续提供上一次成功同步的版本。

真正创建 DNS 记录、签证书、Portainer stack 和 Kong route 前，需要按车队生产发布门禁完成一次人工验收。
