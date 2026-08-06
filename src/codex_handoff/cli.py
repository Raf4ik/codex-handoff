from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .exceptions import HandoffError
from .service import HandoffService, create_provider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-handoff", description="Secure Codex state handoff")
    parser.add_argument("--config", type=Path, help="Configuration JSON path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("gui", help="Open the desktop interface")
    sub.add_parser("status", help="Show local and remote state")
    sub.add_parser("baseline", help="Create the protected parent baseline")
    sub.add_parser("push", help="Publish this device state")
    sub.add_parser("pull", help="Apply the current remote version")
    sub.add_parser("versions", help="List remote versions")
    restore = sub.add_parser("restore", help="Restore a version or baseline")
    restore.add_argument("artifact_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "gui":
        from .gui.app import launch_gui
        return launch_gui(args.config)
    try:
        config = load_config(args.config)
        service = HandoffService(config, create_provider(config))
        if args.command == "status":
            print(json.dumps(service.status(), indent=2))
        elif args.command == "baseline":
            print(service.create_baseline().version_id)
        elif args.command == "push":
            print(service.push().version_id)
        elif args.command == "pull":
            result = service.pull()
            print(result.version_id if result else "up-to-date")
        elif args.command == "versions":
            for version in service.list_versions():
                print(f"{version.version_id}\t{version.source_device}\t{version.created_at}")
        elif args.command == "restore":
            print(service.restore(args.artifact_id).version_id)
        return 0
    except HandoffError as exc:
        print(f"error: {exc}")
        return 2
