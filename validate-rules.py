# -*- coding: utf-8 -*-
from __future__ import annotations

from rule_tools import (
    CURSOR_RECEIPT,
    DEPLOYMENT_STATE,
    LOCAL_MANIFEST,
    LOCAL_ROOT,
    ROOT,
    build_cursor_rules,
    load_manifest,
    managed_paths,
    paths_equal,
    read_json,
    text_sha256,
)


def main() -> None:
    failures: list[str] = []
    generated = build_cursor_rules()
    cursor_file = ROOT / "cursor-user-rules.md"

    if DEPLOYMENT_STATE.exists():
        state = read_json(DEPLOYMENT_STATE)
        failures.append(
            f"部署事务未完成：{state.get('transaction_id', 'unknown')} "
            f"({state.get('phase', 'unknown')})"
        )
    if not cursor_file.exists() or cursor_file.read_text(encoding="utf-8") != generated:
        failures.append("cursor-user-rules.md 不是由当前 AGENTS.md + cursor-overrides.md 生成")
    if len(generated) > 20_000:
        failures.append("Cursor User Rule 超过 20000 字符")

    manifest = load_manifest()
    if not LOCAL_MANIFEST.exists():
        failures.append("本机缺少部署 manifest")
    elif read_json(LOCAL_MANIFEST) != manifest:
        failures.append("本机部署 manifest 与仓库不一致")
    for relative in managed_paths(manifest):
        source = ROOT / relative
        deployed = LOCAL_ROOT / relative
        if not source.exists():
            failures.append(f"仓库缺少：{relative}")
        elif not paths_equal(source, deployed):
            failures.append(f"本机不一致：{relative}")
    if not CURSOR_RECEIPT.exists():
        failures.append("缺少 Cursor User Rule 核验回执")
    else:
        receipt = read_json(CURSOR_RECEIPT)
        if receipt.get("title") != manifest["cursor_rule_title"]:
            failures.append("Cursor User Rule 回执标题不一致")
        if receipt.get("content_sha256") != text_sha256(generated):
            failures.append("Cursor User Rule 回执内容已过期")

    if failures:
        raise SystemExit("校验失败：\n- " + "\n- ".join(failures))

    print("ok: generated file, local deployment, and Cursor verification receipt are consistent")


if __name__ == "__main__":
    main()
