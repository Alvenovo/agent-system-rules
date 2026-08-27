# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from rule_tools import (
    BACKUP_ROOT,
    CURSOR_RECEIPT,
    DEPLOYMENT_STATE,
    LOCAL_MANIFEST,
    LOCAL_ROOT,
    ROOT,
    STAGING_ROOT,
    copy_path,
    read_json,
    load_manifest,
    managed_paths,
    paths_equal,
    remove_path,
    text_sha256,
    write_json,
    write_cursor_rules,
)


def load_previous_paths() -> set[str]:
    if not LOCAL_MANIFEST.exists():
        return set()
    previous = load_manifest(LOCAL_MANIFEST)
    return set(managed_paths(previous))


def load_state() -> dict | None:
    if not DEPLOYMENT_STATE.exists():
        return None
    state = read_json(DEPLOYMENT_STATE)
    if not isinstance(state, dict) or state.get("phase") not in {
        "prepared", "local_deploying", "cursor_pending", "cursor_rollback_pending"
    }:
        raise SystemExit("部署事务状态无效")
    for key in ("changed", "removed", "existing_before"):
        values = state.get(key)
        if not isinstance(values, list):
            raise SystemExit(f"部署事务缺少 {key}")
        for relative in values:
            if not isinstance(relative, str):
                raise SystemExit(f"部署事务包含非法路径：{relative}")
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts:
                raise SystemExit(f"部署事务包含非法路径：{relative}")
    backup_root = Path(state.get("backup_root", "")).resolve()
    stage_root = Path(state.get("stage_root", "")).resolve()
    if BACKUP_ROOT not in backup_root.parents or STAGING_ROOT not in stage_root.parents:
        raise SystemExit("部署事务的数据目录无效")
    return state


def prepare_transaction() -> dict:
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
    if not changed and not removed:
        print("ok: local managed files already match the repository")
        return {}

    transaction_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    backup_root = BACKUP_ROOT / transaction_id
    stage_root = STAGING_ROOT / transaction_id
    existing: list[str] = []
    for relative in sorted(changed | removed):
        local = LOCAL_ROOT / relative
        if local.exists():
            copy_path(local, backup_root / "files" / relative)
            existing.append(relative)
    if LOCAL_MANIFEST.exists():
        copy_path(LOCAL_MANIFEST, backup_root / "local-manifest.json")
    for relative in sorted(changed):
        copy_path(ROOT / relative, stage_root / "files" / relative)

    state = {
        "transaction_id": transaction_id,
        "phase": "prepared",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "changed": sorted(changed),
        "removed": sorted(removed),
        "applied": [],
        "existing_before": existing,
        "had_local_manifest": LOCAL_MANIFEST.exists(),
        "manifest": manifest,
        "backup_root": str(backup_root),
        "stage_root": str(stage_root),
        "cursor_rule_title": manifest["cursor_rule_title"],
        "cursor_expected_sha256": text_sha256((ROOT / "cursor-user-rules.md").read_text(encoding="utf-8")),
        "cursor_previous_sha256": (
            text_sha256((LOCAL_ROOT / "cursor-user-rules.md").read_text(encoding="utf-8"))
            if (LOCAL_ROOT / "cursor-user-rules.md").is_file()
            else None
        ),
    }
    write_json(backup_root / "metadata.json", state)
    write_json(DEPLOYMENT_STATE, state)
    return state


def save_state(state: dict) -> None:
    write_json(DEPLOYMENT_STATE, state)
    write_json(Path(state["backup_root"]) / "metadata.json", state)


def apply_transaction(state: dict) -> None:
    state["phase"] = "local_deploying"
    save_state(state)
    stage_root = Path(state["stage_root"]) / "files"
    applied = set(state["applied"])
    for relative in state["removed"]:
        operation = f"remove:{relative}"
        if operation not in applied:
            remove_path(LOCAL_ROOT / relative)
            state["applied"].append(operation)
            save_state(state)
            print("removed", LOCAL_ROOT / relative)
    for relative in state["changed"]:
        operation = f"copy:{relative}"
        if operation not in applied:
            copy_path(stage_root / relative, LOCAL_ROOT / relative)
            state["applied"].append(operation)
            save_state(state)
            print("deployed", LOCAL_ROOT / relative)
    write_json(LOCAL_MANIFEST, state["manifest"])
    state["phase"] = "cursor_pending"
    save_state(state)
    print("backup", state["backup_root"])
    print("cursor-rule", ROOT / "cursor-user-rules.md")
    print("pending: update and verify Cursor User Rule, then run deploy-to-local.py --cursor-verified")


def rollback_transaction(state: dict) -> None:
    backup_files = Path(state["backup_root"]) / "files"
    existing = set(state["existing_before"])
    for relative in sorted(set(state["changed"]) | set(state["removed"])):
        target = LOCAL_ROOT / relative
        if relative in existing:
            copy_path(backup_files / relative, target)
        else:
            remove_path(target)
    backup_manifest = Path(state["backup_root"]) / "local-manifest.json"
    if state["had_local_manifest"]:
        copy_path(backup_manifest, LOCAL_MANIFEST)
    else:
        remove_path(LOCAL_MANIFEST)
    state["phase"] = "cursor_rollback_pending"
    state["rolled_back_at"] = datetime.now().isoformat(timespec="seconds")
    save_state(state)
    previous_cursor = backup_files / "cursor-user-rules.md"
    print("local rollback complete")
    if previous_cursor.exists():
        print("pending: restore Cursor User Rule from", previous_cursor)
    print("after Cursor verification run deploy-to-local.py --cursor-verified")


def prune_backups(keep: int, max_days: int) -> None:
    if not BACKUP_ROOT.exists():
        return
    cutoff = datetime.now() - timedelta(days=max_days)
    backups = sorted(
        (path for path in BACKUP_ROOT.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for index, path in enumerate(backups):
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if index >= keep or modified < cutoff:
            shutil.rmtree(path)


def main() -> None:
    parser = ArgumentParser(description="事务式部署 agent-system-rules 到本机")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--resume", action="store_true", help="继续未完成事务")
    actions.add_argument("--rollback", action="store_true", help="回滚当前事务")
    actions.add_argument("--cursor-verified", action="store_true", help="记录 Cursor User Rule 已核验")
    parser.add_argument("--keep-backups", type=int, default=20)
    parser.add_argument("--max-backup-days", type=int, default=90)
    args = parser.parse_args()

    if args.keep_backups < 1 or args.max_backup_days < 1:
        raise SystemExit("备份保留数量和天数必须为正整数")
    state = load_state()
    if args.cursor_verified:
        if not state or state["phase"] not in {"cursor_pending", "cursor_rollback_pending"}:
            raise SystemExit("没有等待 Cursor 核验的部署事务")
        verified_at = datetime.now().isoformat(timespec="seconds")
        state["cursor_verified_at"] = verified_at
        expected_hash = (
            state["cursor_expected_sha256"]
            if state["phase"] == "cursor_pending"
            else state["cursor_previous_sha256"]
        )
        write_json(
            CURSOR_RECEIPT,
            {
                "transaction_id": state["transaction_id"],
                "title": state["cursor_rule_title"],
                "content_sha256": expected_hash,
                "verified_at": verified_at,
            },
        )
        state["phase"] = "completed" if state["phase"] == "cursor_pending" else "rolled_back"
        save_state(state)
        shutil.rmtree(Path(state["stage_root"]), ignore_errors=True)
        DEPLOYMENT_STATE.unlink()
        prune_backups(args.keep_backups, args.max_backup_days)
        print(f"ok: transaction {state['phase']}")
        return
    if args.rollback:
        if not state:
            raise SystemExit("没有可回滚的部署事务")
        rollback_transaction(state)
        return
    if state:
        if not args.resume:
            raise SystemExit(
                f"存在未完成事务 {state['transaction_id']} ({state['phase']})；"
                "使用 --resume 或 --rollback"
            )
        if state["phase"] in {"prepared", "local_deploying"}:
            apply_transaction(state)
        elif state["phase"] == "cursor_pending":
            print("pending: Cursor User Rule verification")
        elif state["phase"] == "cursor_rollback_pending":
            print("pending: restore and verify previous Cursor User Rule")
        else:
            raise SystemExit(f"无法继续事务阶段：{state['phase']}")
        return
    state = prepare_transaction()
    if state:
        apply_transaction(state)


if __name__ == "__main__":
    main()
