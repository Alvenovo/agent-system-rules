# agent-system-rules

Codex / Cursor / Qoder 系统级规则的 Git 权威源（不含密码）。`%USERPROFILE%\.codex\`、Cursor User Rules 与 `~/.qoder-cn\` 是部署目标，不在其中直接编辑。

规则修改流程：编辑本仓库 → `python deploy-to-local.py` → 更新并复核 Cursor User Rule → `python deploy-to-local.py --cursor-verified` → `python validate-rules.py`。全部通过后才完成；默认不 commit、不 push。

## 内容

| 路径 | 用途 |
| --- | --- |
| `AGENTS.md` | Codex / Cursor / Qoder 共享正文（权威源） |
| `cursor-overrides.md` | Cursor 专属差异 |
| `cursor-user-rules.md` | 自动生成的 Cursor User Rules，请勿手改 |
| `qoder-overrides.md` | Qoder 专属差异（浏览器原则等），由 `deploy-to-qoder.sh` 拼进 Qoder 正文 |
| `deploy-to-qoder.sh` | 把 `AGENTS.md + qoder-overrides.md` 生成到 `~/.qoder-cn/AGENTS.md`，并把中文 skill 重命名注册到 `~/.qoder-cn/skills/` |
| `managed-files.json` | 部署到 `.codex` 的托管清单 |
| `deploy-to-local.py` | 备份本机差异并部署托管文件 |
| `validate-rules.py` | 校验生成文件与本机部署结果 |
| `tests/` | 部署事务与测试包生成器回归测试 |
| `测试规则/` | 测试；仅触发表命中才读。周报走 skill，禅道访问见 `references/` |
| `references/` | 飞书、Figma、禅道访问、项目知识库 |
| `skills/` | 周报、拷问对齐、没听懂、诊断缺陷、砍复杂度、写给模型、知识卡片、禅道用例CSV、豆包识图 |
| `knowledge/` | 知识卡片资料，不部署到 `.codex` |

## 首次安装或更新

1. 将私有仓库 clone 到 `%USERPROFILE%\Documents\agent-system-rules`。
2. 运行 `python -m pip install -r requirements.txt`。
3. 在仓库运行 `python deploy-to-local.py`。脚本镜像 `managed-files.json` 中的托管路径；托管目录内的多余文件会删除，其他本机目录不受影响。差异持久备份到 `%LOCALAPPDATA%\agent-system-rules\backups\`。
4. Cursor Agent 把 `cursor-user-rules.md` 更新到标题为「系统级工作规则（源：agent-system-rules）」的 User Rule，并再次读取确认。
5. 运行 `python deploy-to-local.py --cursor-verified`，再运行 `python validate-rules.py`；输出 `ok` 后新开 Agent 对话使规则生效。

其他电脑更新：`git pull` 后重复第 2～5 步。

Qoder CLI（可选，独立于上面的 Codex/Cursor 流程）：`git pull` 后运行 `bash deploy-to-qoder.sh`，它只读仓库与 `~/.codex/skills`，只写 `~/.qoder-cn/AGENTS.md` 与 `~/.qoder-cn/skills/`，不碰仓库既有文件；生效需新开会话或 `/skills reload`。

部署中断后运行 `python deploy-to-local.py --resume` 继续，或运行 `python deploy-to-local.py --rollback` 恢复本机文件；回滚后按脚本给出的旧规则文件恢复 Cursor User Rule，再运行 `--cursor-verified`。默认保留最近 20 份且不超过 90 天的备份。

## 修改完成标准

- Git 工作区是唯一编辑源。
- 部署前的本机差异已有备份，托管文件与仓库一致。
- `cursor-user-rules.md` 可由 `AGENTS.md + cursor-overrides.md` 重建。
- Cursor Settings 中对应 User Rule 与生成文件一致。
- `python validate-rules.py` 通过。
- `python -m unittest discover -s tests -v` 通过。
- commit / push 仅在用户明确要求时执行。

## 测试用例归档生成

复制 `测试规则/templates/test-manifest.example.json`，填写材料、覆盖表、稳定 `case_key`、执行状态和证据映射，然后运行：

```powershell
python 测试规则/scripts/generate_test_package.py <manifest.json> <需求归档目录>
python 测试规则/scripts/generate_test_package.py --check <需求归档目录>
```

归档根目录生成四件套；唯一真源保存为 `source/manifest.json`，证据保存在 `证据/`。

## 注意

- 仓库保持私有。
- 不要提交 `.codex` 配置、插件缓存。
