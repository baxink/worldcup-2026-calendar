import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.models import Match
from scripts.snapshot import load_snapshot
from scripts.update_calendar import update_from_content


def make_match(match_id="match-1", status="scheduled", home_score=None, away_score=None, start_time_utc="2026-07-20T00:00:00Z"):
    return Match.from_dict(
        {
            "match_id": match_id,
            "home_team_en": "Argentina",
            "away_team_en": "France",
            "home_team_zh": "阿根廷",
            "away_team_zh": "法国",
            "start_time_utc": start_time_utc,
            "stage": "决赛",
            "venue": "MetLife Stadium",
            "status": status,
            "home_score": home_score,
            "away_score": away_score,
            "last_source_update": "2026-07-20T05:30:00Z",
            "source_url": "https://www.fifa.com/",
        }
    )


def setup_project(tmp_path: Path) -> Path:
    project = tmp_path
    (project / "data").mkdir()
    (project / "public").mkdir()
    (project / "data" / "matches.snapshot.json").write_text("[]\n", encoding="utf-8")
    (project / "data" / "teams.zh-CN.json").write_text(
        json.dumps({"Argentina": "阿根廷", "France": "法国"}, ensure_ascii=False),
        encoding="utf-8",
    )
    return project


def fixture_content(matches: list[dict]) -> str:
    return json.dumps({"matches": matches})


def test_update_from_content_writes_snapshot_calendar_and_status(tmp_path: Path):
    project = setup_project(tmp_path)
    content = fixture_content(
        [
            {
                "id": "final-2026",
                "home": "Argentina",
                "away": "France",
                "kickoff": "2026-07-20T00:00:00Z",
                "stage": "决赛",
                "venue": "MetLife Stadium",
                "status": "finished",
                "score": {"home": 2, "away": 1},
                "url": "https://www.fifa.com/",
            }
        ]
    )

    update_from_content(project, content, now_utc="2026-07-20T05:30:00Z")

    assert "🇦🇷 阿根廷 vs 🇫🇷 法国" in (project / "public" / "worldcup-2026.ics").read_text(encoding="utf-8")
    status = json.loads((project / "public" / "status.json").read_text(encoding="utf-8"))
    assert status["matches_total"] == 1
    assert status["matches_finished"] == 1


def test_status_uses_calendar_url_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CALENDAR_URL", "https://custom.example.com/my.ics")
    project = setup_project(tmp_path)
    content = fixture_content(
        [
            {
                "id": "match-1",
                "home": "Argentina",
                "away": "France",
                "kickoff": "2026-07-20T00:00:00Z",
                "stage": "决赛",
                "venue": "MetLife Stadium",
                "status": "scheduled",
                "score": {},
                "url": "https://www.fifa.com/",
            }
        ]
    )

    update_from_content(project, content, now_utc="2026-07-20T05:30:00Z")

    status = json.loads((project / "public" / "status.json").read_text(encoding="utf-8"))
    assert status["calendar_url"] == "https://custom.example.com/my.ics"


def test_status_derives_calendar_url_from_github_repository(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CALENDAR_URL", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "octo/worldcup-2026-calendar")
    project = setup_project(tmp_path)
    content = fixture_content(
        [
            {
                "id": "match-1",
                "home": "Argentina",
                "away": "France",
                "kickoff": "2026-07-20T00:00:00Z",
                "stage": "决赛",
                "venue": "MetLife Stadium",
                "status": "scheduled",
                "score": {},
                "url": "https://www.fifa.com/",
            }
        ]
    )

    update_from_content(project, content, now_utc="2026-07-20T05:30:00Z")

    status = json.loads((project / "public" / "status.json").read_text(encoding="utf-8"))
    assert status["calendar_url"] == "https://octo.github.io/worldcup-2026-calendar/worldcup-2026.ics"


def test_update_rejects_large_match_count_drop(tmp_path: Path):
    from scripts.snapshot import save_snapshot

    project = setup_project(tmp_path)
    existing = [make_match(match_id=f"match-{i}") for i in range(10)]
    save_snapshot(project / "data" / "matches.snapshot.json", existing)

    incoming_matches = [{"id": f"match-{i}", "home": "Argentina", "away": "France", "kickoff": "2026-07-20T00:00:00Z", "stage": "决赛", "venue": "MetLife Stadium", "status": "scheduled", "score": {}, "url": "https://www.fifa.com/"} for i in range(7)]
    content = fixture_content(incoming_matches)

    with pytest.raises(RuntimeError, match="Parsed match count dropped"):
        update_from_content(project, content, now_utc="2026-07-20T05:30:00Z")


def test_update_preserves_existing_omitted_match(tmp_path: Path):
    from scripts.snapshot import save_snapshot

    project = setup_project(tmp_path)
    existing = [make_match(match_id="match-1")]
    save_snapshot(project / "data" / "matches.snapshot.json", existing)

    content = fixture_content(
        [
            {
                "id": "match-2",
                "home": "Argentina",
                "away": "France",
                "kickoff": "2026-07-21T00:00:00Z",
                "stage": "半决赛",
                "venue": "AT&T Stadium",
                "status": "scheduled",
                "score": {},
                "url": "https://www.fifa.com/",
            }
        ]
    )

    update_from_content(project, content, now_utc="2026-07-20T05:30:00Z")

    snapshot = load_snapshot(project / "data" / "matches.snapshot.json")
    ids = {m.match_id for m in snapshot}
    assert ids == {"match-1", "match-2"}


def test_update_calendar_script_can_be_loaded_as_direct_file():
    result = subprocess.run(
        [sys.executable, "scripts/update_calendar.py"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "FIFA_CALENDAR_IMPORT_CHECK_ONLY": "1"},
    )
    assert result.returncode == 0, (
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
