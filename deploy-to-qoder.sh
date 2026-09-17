#!/usr/bin/env bash
# 把 agent-system-rules 部署到 Qoder CLI（用户级）。
# 只读仓库与 ~/.codex，只写 ~/.qoder-cn/{AGENTS.md,skills/}。不改动仓库既有文件。
# 用法：git pull && python deploy-to-local.py（或 bash 镜像到 ~/.codex）后运行本脚本。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$(cd ~ && pwd)"
CODEX="$HOME_DIR/.codex"
QODER="$HOME_DIR/.qoder-cn"
QODER_SKILLS="$QODER/skills"

[ -d "$CODEX/skills" ] || { echo "blocked: $CODEX/skills 不存在，先部署 ~/.codex"; exit 1; }

# 中文 skill → Qoder 名（Qoder 的 name 只允许 ^[a-z0-9-]+$ 且须与目录名一致）。
# 第三列非空则整行替换 description：补中文触发词，或保留"点名才用"的意图。
MAP=(
  "周报|weekly-report|"
  "拷问对齐|grill-align|高成本、不可逆或有明显架构分支时，用决策树逐轮对齐方案。仅当用户点名 /grill-align 或说「拷问对齐」「逐轮追问」「帮我把方案问清楚」时调用，不要自动触发。"
  "没听懂|ask-again|补充必要上下文，用短句和项目术语把上一段重新讲清楚。仅当用户点名 /ask-again 或说「没听懂」「重新讲一遍」「讲清楚点」时调用，不要自动触发。"
  "砍复杂度|cut-complexity|对着 diff 或指定范围列出可删的过度设计，只列不改。仅当用户点名 /cut-complexity 或说「砍复杂度」「哪里能删」「精简这块」时调用，不要自动触发。"
  "诊断缺陷|bug-diagnose|"
  "知识卡片|knowledge-card|"
  "写给模型|write-for-model|"
  "禅道用例CSV|zentao-case-csv|独立禅道CSV：把清单或现有 JSON 转成团队 12 列可导入 CSV；完整测试四件套走测试规则统一生成器。用户说「禅道 CSV」「导出用例 CSV」或点名 /zentao-case-csv 时用。"
  "豆包识图|doubao-vision|"
)

gen_agents() {
  local out="$QODER/AGENTS.md" tmp
  tmp="$(mktemp)"
  awk -v src="$ROOT/AGENTS.md" -v ovr="$ROOT/qoder-overrides.md" '
    BEGIN {
      while ((getline line < src) > 0) lines[++n] = line
      close(src)
      m = 0
      while ((getline line < ovr) > 0) if (line != "") o[++m] = line
      close(ovr)
      heading = "## 浏览器使用原则"
      print "# 系统级规则（Qoder CLI；由 agent-system-rules 生成）"
      for (i = 2; i <= n; i++) {
        print lines[i]
        if (lines[i] == heading) { print ""; for (j = 1; j <= m; j++) print o[j] }
      }
    }
  ' /dev/null >"$tmp"

  cat >>"$tmp" <<'APPENDIX'

# 四、Qoder 端适配（部署目标为 Qoder CLI 时生效）

## 细则根目录

- 触发表里的 `%USERPROFILE%\.codex\` 就是本机共用细则根，已部署且与仓库一致。细则禁止复制进 `.qoder-cn`，避免两个真源。
- 图片识别一节指向的 `%USERPROFILE%\.codex\skills\豆包识图\SKILL.md` 是 Codex 侧原文件，路径有效；但 Qoder 内优先用英文名调用下面已注册的 skill。

## Skill 名称映射

Qoder 的 `name` 只接受 `^[a-z0-9-]+$` 且必须与目录名一致，中文 skill 已按此重命名注册到 `%USERPROFILE%\.qoder-cn\skills\`，正文与相对引用不变：

| Qoder 名 | 源目录（`~/.codex/skills/`） |
| --- | --- |
| `weekly-report` | 周报 |
| `grill-align` | 拷问对齐 |
| `ask-again` | 没听懂 |
| `cut-complexity` | 砍复杂度 |
| `bug-diagnose` | 诊断缺陷 |
| `knowledge-card` | 知识卡片 |
| `write-for-model` | 写给模型 |
| `zentao-case-csv` | 禅道用例CSV |
| `doubao-vision` | 豆包识图 |

源目录改了正文或触发条件，改完 `AGENTS.md`/`skills` 需重跑 `bash deploy-to-qoder.sh`。

## 与 Qoder 记忆层的关系

- Qoder 另有自动记忆：`~/.qoder-cn/memory/`（用户级）与 `~/.qoder-cn/projects/<项目>/memory/`（项目级），索引是各自的 `MEMORY.md`。
- 本文件的规则优先于记忆。记忆只是历史推断，可能过期；据它下结论前先读代码、文件或 `git log` 核实。
- 稳定的项目规范写进项目 `AGENTS.md` 或 `.qoder/rules/*.md`，不要留在记忆里。

## 与内置默认行为冲突时

以下 Qoder 内置默认与本文件冲突时，以本文件为准：

- 内置默认「不主动创建文档」——本文件要求维护《会话交接.md》，照常创建与更新。
- 内置默认「结束时一两句总结」——不违反本文件时保留。
APPENDIX

  if [ -f "$out" ] && cmp -s "$tmp" "$out"; then
    echo "ok: $out 已是最新"
    rm -f "$tmp"
  else
    [ -f "$out" ] && cp -a "$out" "$out.prev"
    mv "$tmp" "$out"
    echo "deployed $out"
  fi
}

gen_skills() {
  mkdir -p "$QODER_SKILLS"
  local entry zh en desc src dst
  for entry in "${MAP[@]}"; do
    IFS='|' read -r zh en desc <<<"$entry"
    src="$CODEX/skills/$zh"
    [ -d "$src" ] || { echo "blocked: 缺少源 skill $src"; exit 1; }
    dst="$QODER_SKILLS/$en"
    rm -rf "$dst"
    mkdir -p "$dst"
    # agents/ 是 Codex 的界面元数据，Qoder 不读
    (cd "$src" && find . -mindepth 1 -maxdepth 1 ! -name agents -exec cp -a {} "$dst/" \;)
    [ -f "$dst/SKILL.md" ] || { echo "blocked: $dst/SKILL.md 不存在"; exit 1; }
    if [ -n "$desc" ]; then
      awk -v en="$en" -v desc="$desc" 'NR<=6 { if ($0 ~ /^name: /) { print "name: " en; next } if ($0 ~ /^description: /) { print "description: " desc; next } } { print }' "$dst/SKILL.md" >"$dst/.SKILL.md.tmp"
    else
      awk -v en="$en" 'NR<=6 && $0 ~ /^name: / { print "name: " en; next } { print }' "$dst/SKILL.md" >"$dst/.SKILL.md.tmp"
    fi
    mv "$dst/.SKILL.md.tmp" "$dst/SKILL.md"
    printf 'ok: %s ← %s\n' "$en" "$zh"
  done
}

mkdir -p "$QODER"
gen_agents
gen_skills
echo "---"
echo "生效需要新开会话或执行 /skills reload"
