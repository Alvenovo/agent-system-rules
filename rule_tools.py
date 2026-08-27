# -*- coding: utf-8 -*-
from __future__ import annotations

import filecmp
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
LOCAL_ROOT = Path.home() / ".codex"
LOCAL_MANIFEST = LOCAL_ROOT / ".agent-system-rules-manifest.json"


def load_manifest(path: Path = ROOT / "managed-files.json") -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def managed_paths(manifest: dict[str, Any]) -> list[str]:
    paths = [*manifest["files"], *manifest["directories"]]
    paths.extend(f"skills/{name}" for name in manifest["skills"])
    return paths


def paths_equal(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return left.exists() == right.exists()
    if left.is_file() != right.is_file():
        return False
    if left.is_file():
        return filecmp.cmp(left, right, shallow=False)

    left_entries = sorted(path.relative_to(left) for path in left.rglob("*"))
    right_entries = sorted(path.relative_to(right) for path in right.rglob("*"))
    if left_entries != right_entries:
        return False
    return all(
        paths_equal(left / relative, right / relative)
        for relative in left_entries
        if (left / relative).is_file()
    )


def copy_path(source: Path, target: Path) -> None:
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        source_entries = {path.relative_to(source) for path in source.rglob("*")}
        target_entries = {path.relative_to(target) for path in target.rglob("*")}

        for relative in sorted(source_entries):
            source_entry = source / relative
            target_entry = target / relative
            if source_entry.is_dir():
                target_entry.mkdir(parents=True, exist_ok=True)
            else:
                target_entry.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_entry, target_entry)

        for relative in sorted(target_entries - source_entries, reverse=True):
            remove_path(target / relative)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def build_cursor_rules() -> str:
    source = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    lines = source.splitlines()
    lines[0] = "# 系统级规则（Cursor User Rules；由 agent-system-rules 生成）"

    heading = "## 浏览器使用原则"
    try:
        index = lines.index(heading)
    except ValueError as exc:
        raise RuntimeError(f"AGENTS.md 缺少生成锚点：{heading}") from exc

    override = (ROOT / "cursor-overrides.md").read_text(encoding="utf-8").strip()
    lines[index + 1:index + 1] = ["", override]
    return "\n".join(lines) + "\n"


def write_cursor_rules() -> Path:
    output = ROOT / "cursor-user-rules.md"
    output.write_text(build_cursor_rules(), encoding="utf-8")
    return output
