from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.models import Match


class SnapshotError(RuntimeError):
    pass


def load_snapshot(path: Path) -> list[Match]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"Invalid snapshot JSON: {path}") from exc
    return [Match.from_dict(item) for item in data]


def save_snapshot(path: Path, matches: list[Match]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [match.to_dict() for match in sorted(matches, key=lambda item: (item.start_time_utc, item.match_id))]
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def has_valid_score(match: Match) -> bool:
    return match.status in {"finished", "live"} and match.home_score is not None and match.away_score is not None


def merge_match(old: Match | None, new: Match) -> Match:
    if old is None:
        return new
    if has_valid_score(old) and not has_valid_score(new):
        return old
    return new


def merge_matches(existing: list[Match], incoming: list[Match]) -> list[Match]:
    by_id = {match.match_id: match for match in existing}
    for new_match in incoming:
        by_id[new_match.match_id] = merge_match(by_id.get(new_match.match_id), new_match)
    return sorted(by_id.values(), key=lambda item: (item.start_time_utc, item.match_id))
