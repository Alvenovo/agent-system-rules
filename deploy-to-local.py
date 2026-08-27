# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from rule_tools import (
    LOCAL_MANIFEST,
    LOCAL_ROOT,
    ROOT,
    copy_path,
    load_manifest,
    managed_paths,
    paths_equal,
    remove_path,
    write_cursor_rules,
)


def load_previous_paths() -> set[str]:
    if not LOCAL_MANIFEST.exists():
        return set()
    previous = json.loads(LOCAL_MANIFEST.read_text(encoding="utf-8"))
    return set(managed_paths(previous))


def backup_changed(paths: set[str]) -> Path | None:
    existing = [relative for relative in sorted(paths) if (LOCAL_ROOT / relative).exists()]
    if not existing:
        return None

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = Path(tempfile.gettempdir()) / "agent-system-rules-backups" / stamp
    for relative in existing:
        copy_path(LOCAL_ROOT / relative, backup_root / relative)
    return backup_root


def main() -> None:
    write_cursor_rules()
    manifest = load_manifest()
    current_paths = set(managed_paths(manifest))
    previous_paths = load_previous_paths()

    missing = [relative for relative in sorted(current_paths) if not (ROOT / relative).exists()]
    if missing:
        raise SystemExit("仓库缺少托管路径：\n- " + "\n- ".join(missing))

    changed = {
        relative
        for relative in current_paths
        if not paths_equal(ROOT / relative, LOCAL_ROOT / relative)
    }
    removed = previous_paths - current_paths
    backup_root = backup_changed(changed | removed)

    for relative in sorted(removed):
        remove_path(LOCAL_ROOT / relative)
        print("removed", LOCAL_ROOT / relative)

    for relative in sorted(current_paths):
        copy_path(ROOT / relative, LOCAL_ROOT / relative)
        print("deployed", LOCAL_ROOT / relative)

    LOCAL_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if backup_root:
        print("backup", backup_root)
    else:
        print("backup not-needed")
    print("cursor-rule", ROOT / "cursor-user-rules.md")
    print("ok: local files deployed; Cursor agent must update User Rules and verify it")


if __name__ == "__main__":
    main()
