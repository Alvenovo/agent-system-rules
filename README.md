# agent-system-rules

Codex / Cursor 系统级规则备份（不含密码）。本机生效文件仍以 `C:\Users\admin\.codex\` 与 Cursor User Rules 为准。

## 内容

| 路径 | 用途 |
| --- | --- |
| `AGENTS.md` | Codex 系统级规则 |
| `cursor-user-rules.md` | Cursor User Rules 备份 |
| `references/` | 触发表外链：周报模板、用例设计规范、交付归档、执行精进 |
| `skills/zentao-testcase-csv/` | 禅道 CSV 生成 skill（禁止手写 CSV） |
| `skills/doubao-image-describe/` | 不能看图时的识图 skill |

## 注意

- 仓库保持私有。
- 不要写入禅道或其他系统密码。
- 改规则时：先改本机 `AGENTS.md` + Cursor User Rules + `references/`，再同步进本仓库。
