# -*- coding: utf-8 -*-
from __future__ import annotations

import filecmp
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("AGENT_RULES_ROOT", Path(__file__).resolve().parent)).resolve()
LOCAL_ROOT = Path(os.environ.get("AGENT_RULES_LOCAL_ROOT", Path.home() / ".codex")).resolve()
DATA_ROOT = Path(
    os.environ.get(
        "AGENT_RULES_DATA_ROOT",
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "agent-system-rules",
    )
).resolve()
LOCAL_MANIFEST = LOCAL_ROOT / ".agent-system-rules-manifest.json"
DEPLOYMENT_STATE = DATA_ROOT / "deployment-state.json"
CURSOR_RECEIPT = DATA_ROOT / "cursor-verification.json"
BACKUP_ROOT = DATA_ROOT / "backups"
STAGING_ROOT = DATA_ROOT / "staging"


def load_manifest(path: Path = ROOT / "managed-files.json") -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("managed-files.json 顶层必须是对象")
    for key in ("files", "directories", "skills"):
        values = manifest.get(key)
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"managed-files.json 的 {key} 必须是非空字符串数组")
    title = manifest.get("cursor_rule_title")
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise ValueError("managed-files.json 的 cursor_rule_title 必须是 1～200 字符")
    paths = managed_paths(manifest)
    if len(paths) != len(set(paths)):
        raise ValueError("managed-files.json 存在重复托管路径")
    normalized: list[Path] = []
    for relative in paths:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
            raise ValueError(f"非法托管路径：{relative}")
        normalized.append(path)
    for index, left in enumerate(normalized):
        for right in normalized[index + 1:]:
            if left in right.parents or right in left.parents:
                raise ValueError(f"托管路径重叠：{left} / {right}")
    return manifest


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


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        temp.write_text(content, encoding="utf-8", newline="")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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
    generated = build_cursor_rules()
    if len(generated) > 20_000:
        raise ValueError("Cursor User Rule 超过 20000 字符")
    atomic_write_text(output, generated)
    return output
