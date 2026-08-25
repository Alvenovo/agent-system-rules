# -*- coding: utf-8 -*-
from pathlib import Path
import shutil

src = Path.home() / ".codex"
dst = Path(r"C:\Users\admin\Documents\agent-system-rules")

def copy_file(rel: str) -> None:
    s, d = src / rel, dst / rel
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s, d)
    print("file", d)

def copy_dir(rel: str) -> None:
    s, d = src / rel, dst / rel
    if not s.exists():
        raise SystemExit(f"missing {s}")
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(s, d)
    print("dir", d)

copy_file("AGENTS.md")
copy_file("cursor-user-rules.md")

# references: only non-test
ref = dst / "references"
if ref.exists():
    shutil.rmtree(ref)
ref.mkdir()
copy_file("references/PowerShell7一次性安装.md")
copy_file("references/飞书访问.md")

copy_dir("测试规则")

skills_keep = [
    "zentao-testcase-csv",
    "doubao-image-describe",
    "拷问对齐",
    "没听懂",
    "诊断缺陷",
    "写给模型",
    "知识卡片",
]
skills_dst = dst / "skills"
skills_dst.mkdir(exist_ok=True)
for child in list(skills_dst.iterdir()):
    if child.is_dir() and child.name not in skills_keep:
        shutil.rmtree(child)
        print("removed skill", child.name)
for name in skills_keep:
    copy_dir(f"skills/{name}")

print("ok")
