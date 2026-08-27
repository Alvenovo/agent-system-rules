# -*- coding: utf-8 -*-
from __future__ import annotations

from rule_tools import LOCAL_ROOT, ROOT, build_cursor_rules, load_manifest, managed_paths, paths_equal


def main() -> None:
    failures: list[str] = []
    generated = build_cursor_rules()
    cursor_file = ROOT / "cursor-user-rules.md"

    if not cursor_file.exists() or cursor_file.read_text(encoding="utf-8") != generated:
        failures.append("cursor-user-rules.md 不是由当前 AGENTS.md + cursor-overrides.md 生成")

    manifest = load_manifest()
    for relative in managed_paths(manifest):
        source = ROOT / relative
        deployed = LOCAL_ROOT / relative
        if not source.exists():
            failures.append(f"仓库缺少：{relative}")
        elif not paths_equal(source, deployed):
            failures.append(f"本机不一致：{relative}")

    if failures:
        raise SystemExit("校验失败：\n- " + "\n- ".join(failures))

    print("ok: generated Cursor file and local managed files are consistent")
    print("pending external check: Cursor Settings User Rule content")


if __name__ == "__main__":
    main()
