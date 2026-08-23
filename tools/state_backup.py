"""Manual backup/restore for data/state.json (TODO STATE-001).

Usage:
    python tools/state_backup.py export
    python tools/state_backup.py restore <backup_file> [--apply]

Without --apply, restore only verifies the backup against a temporary copy;
the live state file is never touched. Old backups are never deleted.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personality.persistence import DEFAULT_PATH, SCHEMA_VERSION, load_state

BACKUP_VERSION = 1
DEFAULT_BACKUP_DIR = os.path.join("data", "backups")

_REQUIRED_FIELDS = ("backup_version", "created_at", "schema_version", "checksum", "payload")


def checksum_payload(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def export_backup(state_path: str = DEFAULT_PATH, backup_dir: str = DEFAULT_BACKUP_DIR) -> str:
    with open(state_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    envelope = {
        "backup_version": BACKUP_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "schema_version": int(payload.get("version", 0)),
        "source": state_path,
        "checksum": checksum_payload(payload),
        "payload": payload,
    }

    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join(backup_dir, f"state_v{envelope['schema_version']}_{stamp}.json")
    fd, tmp_path = tempfile.mkstemp(dir=backup_dir, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(envelope, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, out_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    print(f"Backup written: {out_path}")
    return out_path


def restore_backup(backup_path: str, state_path: str = DEFAULT_PATH, apply: bool = False) -> bool:
    with open(backup_path, "r", encoding="utf-8") as f:
        envelope = json.load(f)

    missing = [k for k in _REQUIRED_FIELDS if k not in envelope]
    if missing:
        raise ValueError(f"Not a valid state backup, missing fields: {', '.join(missing)}")
    if envelope["backup_version"] != BACKUP_VERSION:
        raise ValueError(f"Unsupported backup version: {envelope['backup_version']}")
    if checksum_payload(envelope["payload"]) != envelope["checksum"]:
        raise ValueError("Checksum mismatch: backup file is corrupted or was edited")

    schema = int(envelope["schema_version"])
    if schema > SCHEMA_VERSION:
        raise ValueError(
            f"Backup schema v{schema} is newer than runtime schema v{SCHEMA_VERSION}; "
            "upgrade the runtime first."
        )

    target_dir = os.path.dirname(os.path.abspath(state_path))
    fd, tmp_path = tempfile.mkstemp(dir=target_dir, prefix=".restore_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(envelope["payload"], f, indent=4, ensure_ascii=False)
        state = load_state(tmp_path)
        print(
            "Verified: "
            f"affection={state.affection:.3f} trust={state.trust:.3f} "
            f"attachment={state.attachment:.3f} comfort={state.comfort:.3f} "
            f"dependency={state.dependency:.3f} stage={state.stage_label()}"
        )
        if apply:
            os.replace(tmp_path, state_path)
            print(f"State restored to: {state_path}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return True


def main():
    parser = argparse.ArgumentParser(description="Backup/restore data/state.json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("export", help="Create a timestamped backup")
    p_restore = sub.add_parser("restore", help="Verify (and optionally apply) a backup")
    p_restore.add_argument("backup_file")
    p_restore.add_argument("--apply", action="store_true",
                           help="Overwrite the live state file (default: verify only)")
    args = parser.parse_args()

    try:
        if args.command == "export":
            export_backup()
        else:
            restore_backup(args.backup_file, apply=args.apply)
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
