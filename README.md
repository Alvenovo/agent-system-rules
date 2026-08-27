# agent-system-rules

Codex / Cursor 系统级规则备份（不含密码）。本机生效文件仍以 `%USERPROFILE%\.codex\` 与 Cursor User Rules 为准。

源文件是 `AGENTS.md`（Codex）。改系统级先改本机 `.codex\AGENTS.md`，再同步 Cursor，再拷进本仓库推送。

## 内容

| 路径 | 用途 |
| --- | --- |
| `AGENTS.md` | Codex 系统级规则（源） |
| `cursor-user-rules.md` | Cursor User Rules 备份 |
| `测试规则/` | 测试；仅触发表命中才读。周报走 skill，禅道访问见 `references/` |
| `references/` | PowerShell 7、飞书、Figma、禅道访问 |
| `skills/` | 周报、拷问对齐、没听懂、诊断缺陷、写给模型、知识卡片、禅道用例CSV、豆包识图 |

## 家里电脑第一次用

1. 把本仓库 clone 到任意目录（保持 **Private**）。
2. 运行：`python restore-to-codex.py`（会写入 `%USERPROFILE%\.codex\`，不碰 `skills\.system`）。
3. 打开 Cursor Settings → User Rules，把 `cursor-user-rules.md` 全文贴进「系统级工作规则（源：Codex AGENTS.md）」那条。
4. 新开一个 Agent 对话后规则才生效。

公司电脑改完规则后：在本仓库运行 `python _sync_from_codex.py`，再 `git push`。

## 注意

- 仓库保持私有。
- 不要提交 `pwsh7.ok`、`.codex` 配置、插件缓存。
