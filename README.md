# agent-system-rules

Codex / Cursor 系统级规则的 Git 权威源（不含密码）。`%USERPROFILE%\.codex\` 与 Cursor User Rules 是部署目标，不在其中直接编辑。

规则修改流程：编辑本仓库 → `python deploy-to-local.py` → 更新 Cursor User Rule → `python validate-rules.py`。文件校验和 Cursor Settings 都一致后才完成；默认不 commit、不 push。

## 内容

| 路径 | 用途 |
| --- | --- |
| `AGENTS.md` | Codex / Cursor 共享正文（权威源） |
| `cursor-overrides.md` | Cursor 专属差异 |
| `cursor-user-rules.md` | 自动生成的 Cursor User Rules，请勿手改 |
| `managed-files.json` | 部署到 `.codex` 的托管清单 |
| `deploy-to-local.py` | 备份本机差异并部署托管文件 |
| `validate-rules.py` | 校验生成文件与本机部署结果 |
| `测试规则/` | 测试；仅触发表命中才读。周报走 skill，禅道访问见 `references/` |
| `references/` | PowerShell 7、飞书、Figma、禅道访问 |
| `skills/` | 周报、拷问对齐、没听懂、诊断缺陷、写给模型、知识卡片、禅道用例CSV、豆包识图 |
| `knowledge/` | 知识卡片资料，不部署到 `.codex` |

## 首次安装或更新

1. 将私有仓库 clone 到 `%USERPROFILE%\Documents\agent-system-rules`。
2. 在仓库运行 `python deploy-to-local.py`。脚本只覆盖 `managed-files.json` 中的内容，保留 `skills\.system`、插件及其他本机文件；本机差异先备份到系统临时目录。
3. Cursor Agent 自动把 `cursor-user-rules.md` 更新到标题为「系统级工作规则（源：agent-system-rules）」的 User Rule，并再次读取确认。
4. 运行 `python validate-rules.py`；输出 `ok` 后新开 Agent 对话使规则生效。

其他电脑更新：`git pull` 后重复第 2～4 步。

## 修改完成标准

- Git 工作区是唯一编辑源。
- 部署前的本机差异已有备份，托管文件与仓库一致。
- `cursor-user-rules.md` 可由 `AGENTS.md + cursor-overrides.md` 重建。
- Cursor Settings 中对应 User Rule 与生成文件一致。
- `python validate-rules.py` 通过。
- commit / push 仅在用户明确要求时执行。

## 注意

- 仓库保持私有。
- 不要提交 `pwsh7.ok`、`.codex` 配置、插件缓存。
