# -*- coding: utf-8 -*-
"""把本仓库同步回本机 %USERPROFILE%\\.codex（家里电脑 clone 后运行）。不覆盖 skills/.system。"""
from pathlib import Path
import shutil

src = Path(__file__).resolve().parent
dst = Path.home() / ".codex"

def copy_file(rel: str) -> None:
    s, d = src / rel, dst / rel
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s, d)
    print("file", d)

def copy_dir(rel: str) -> None:
    s, d = src / rel, dst / rel
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(s, d)
    print("dir", d)

copy_file("AGENTS.md")
copy_file("cursor-user-rules.md")
copy_dir("references")
copy_dir("测试规则")

skills_src = src / "skills"
skills_dst = dst / "skills"
skills_dst.mkdir(parents=True, exist_ok=True)
for child in skills_src.iterdir():
    if not child.is_dir():
        continue
    target = skills_dst / child.name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(child, target)
    print("skill", child.name)

print("ok")
print("还要把 cursor-user-rules.md 全文贴进 Cursor Settings → User Rules（标题：系统级工作规则（源：Codex AGENTS.md））。")
