from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.build_ics import build_calendar
from scripts.fetch_fifa import fetch_url, save_raw_response
from scripts.parse_fifa import parse_matches
from scripts.snapshot import load_snapshot, merge_matches, save_snapshot


def calendar_url() -> str:
    configured = os.environ.get("CALENDAR_URL")
    if configured:
        return configured
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repository:
        owner, repo = repository.split("/", 1)
        return f"https://{owner}.github.io/{repo}/worldcup-2026.ics"
    return ""


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_teams(project_root: Path) -> dict[str, str]:
    path = project_root / "data" / "teams.zh-CN.json"
    return json.loads(path.read_text(encoding="utf-8"))


def write_status(project_root: Path, matches_count: int, finished_count: int, now_utc: str) -> None:
    status = {
        "last_success_at": now_utc,
        "matches_total": matches_count,
        "matches_finished": finished_count,
        "source": "fifa",
        "calendar_url": calendar_url(),
    }
    path = project_root / "public" / "status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_incoming(existing_count: int, incoming_count: int) -> None:
    if existing_count >= 10 and incoming_count < int(existing_count * 0.8):
        raise RuntimeError(f"Parsed match count dropped from {existing_count} to {incoming_count}")


def update_from_content(project_root: Path, content: str, now_utc: str) -> None:
    teams = load_teams(project_root)
    snapshot_path = project_root / "data" / "matches.snapshot.json"
    existing = load_snapshot(snapshot_path)
    incoming = parse_matches(content, teams, source_update_utc=now_utc)
    validate_incoming(len(existing), len(incoming))
    merged = merge_matches(existing, incoming)
    save_snapshot(snapshot_path, merged)
    calendar = build_calendar(merged, generated_at_utc=now_utc)
    public_dir = project_root / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "worldcup-2026.ics").write_text(calendar, encoding="utf-8")
    write_status(project_root, len(merged), sum(1 for match in merged if match.status == "finished"), now_utc)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    now_utc = utc_now_text()
    content = fetch_url()
    save_raw_response(project_root / "data" / "raw" / "latest", content)
    update_from_content(project_root, content, now_utc)


if __name__ == "__main__":
    if os.environ.get("FIFA_CALENDAR_IMPORT_CHECK_ONLY"):
        sys.exit(0)
    main()
