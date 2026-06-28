# 2026 World Cup Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub-hosted 2026 World Cup calendar generator that publishes one full-tournament ICS feed updated at Beijing time 08:30 and 13:30.

**Architecture:** Implement a small Python static generator inside `worldcup-2026-calendar/`. The generator fetches FIFA source data, parses it into normalized match records, merges records with a persisted snapshot so completed scores are never lost, and writes `public/worldcup-2026.ics` plus `public/status.json` for GitHub Pages.

**Tech Stack:** Python 3.11+, standard library first, pytest for tests, GitHub Actions, GitHub Pages, iCalendar text generation without a runtime server.

---

## File Structure

Create these files under `worldcup-2026-calendar/`:

- `README.md`: user-facing setup, subscription URL, local commands, operational notes.
- `requirements-dev.txt`: test dependency list.
- `.gitignore`: Python cache and generated raw-response ignores.
- `.github/workflows/update-calendar.yml`: scheduled and manual update workflow.
- `scripts/models.py`: typed match model, status constants, validation helpers.
- `scripts/snapshot.py`: snapshot load/save and merge rules that preserve finished matches.
- `scripts/build_ics.py`: ICS escaping, date formatting, and calendar generation.
- `scripts/fetch_fifa.py`: FIFA HTTP retrieval with timeout, retry, and raw response persistence.
- `scripts/parse_fifa.py`: parser entry point for FIFA JSON/HTML payloads.
- `scripts/update_calendar.py`: orchestration CLI used locally and by GitHub Actions.
- `data/teams.zh-CN.json`: initial team-name mapping and common unassigned-team labels.
- `data/matches.snapshot.json`: durable match state, initialized as an empty list.
- `public/worldcup-2026.ics`: generated initial empty calendar.
- `public/status.json`: generated status file.
- `tests/test_snapshot.py`: merge-rule tests.
- `tests/test_build_ics.py`: ICS generation tests.
- `tests/test_parse_fifa.py`: parser tests with minimal fixture payload.
- `tests/test_update_calendar.py`: end-to-end orchestration test using a local fixture.

---

### Task 1: Project Skeleton and Data Model

**Files:**
- Create: `worldcup-2026-calendar/requirements-dev.txt`
- Create: `worldcup-2026-calendar/.gitignore`
- Create: `worldcup-2026-calendar/scripts/__init__.py`
- Create: `worldcup-2026-calendar/scripts/models.py`
- Create: `worldcup-2026-calendar/data/teams.zh-CN.json`
- Create: `worldcup-2026-calendar/data/matches.snapshot.json`
- Create: `worldcup-2026-calendar/public/worldcup-2026.ics`
- Create: `worldcup-2026-calendar/public/status.json`
- Test: `worldcup-2026-calendar/tests/test_models.py`

- [ ] **Step 1: Create the failing model test**

Create `worldcup-2026-calendar/tests/test_models.py`:

```python
from scripts.models import Match, normalize_status


def test_match_from_dict_normalizes_status_and_scores():
    match = Match.from_dict(
        {
            "match_id": "match-1",
            "home_team_en": "Argentina",
            "away_team_en": "France",
            "home_team_zh": "阿根廷",
            "away_team_zh": "法国",
            "start_time_utc": "2026-07-20T00:00:00Z",
            "stage": "决赛",
            "venue": "MetLife Stadium",
            "status": "Finished",
            "home_score": "2",
            "away_score": "1",
            "last_source_update": "2026-07-20T05:30:00Z",
            "source_url": "https://www.fifa.com/",
        }
    )

    assert match.status == "finished"
    assert match.home_score == 2
    assert match.away_score == 1
    assert match.title == "阿根廷 vs 法国"


def test_normalize_status_rejects_unknown_status():
    try:
        normalize_status("abandoned")
    except ValueError as exc:
        assert "Unsupported match status" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
```

- [ ] **Step 2: Run the model test and verify it fails**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_models.py -v`

Expected: FAIL because `scripts.models` does not exist.

- [ ] **Step 3: Create base files and the match model**

Create `worldcup-2026-calendar/requirements-dev.txt`:

```text
pytest==8.2.2
```

Create `worldcup-2026-calendar/.gitignore`:

```text
__pycache__/
.pytest_cache/
*.pyc
data/raw/latest/*
!data/raw/latest/.gitkeep
```

Create `worldcup-2026-calendar/scripts/__init__.py` as an empty file.

Create `worldcup-2026-calendar/scripts/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ALLOWED_STATUSES = {"scheduled", "live", "finished", "postponed", "cancelled"}
STATUS_ALIASES = {
    "not_started": "scheduled",
    "pre_match": "scheduled",
    "in_progress": "live",
    "playing": "live",
    "full_time": "finished",
    "ended": "finished",
}


def normalize_status(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    normalized = STATUS_ALIASES.get(normalized, normalized)
    if normalized not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported match status: {value}")
    return normalized


def parse_score(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    return int(str(value))


@dataclass(frozen=True)
class Match:
    match_id: str
    home_team_en: str
    away_team_en: str
    home_team_zh: str
    away_team_zh: str
    start_time_utc: str
    stage: str
    venue: str
    status: str
    home_score: int | None
    away_score: int | None
    last_source_update: str
    source_url: str

    @property
    def title(self) -> str:
        return f"{self.home_team_zh} vs {self.away_team_zh}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Match":
        return cls(
            match_id=str(data["match_id"]),
            home_team_en=str(data.get("home_team_en", "")),
            away_team_en=str(data.get("away_team_en", "")),
            home_team_zh=str(data.get("home_team_zh") or data.get("home_team_en", "")),
            away_team_zh=str(data.get("away_team_zh") or data.get("away_team_en", "")),
            start_time_utc=str(data["start_time_utc"]),
            stage=str(data.get("stage", "")),
            venue=str(data.get("venue", "")),
            status=normalize_status(str(data.get("status", "scheduled"))),
            home_score=parse_score(data.get("home_score")),
            away_score=parse_score(data.get("away_score")),
            last_source_update=str(data.get("last_source_update", "")),
            source_url=str(data.get("source_url", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team_en": self.home_team_en,
            "away_team_en": self.away_team_en,
            "home_team_zh": self.home_team_zh,
            "away_team_zh": self.away_team_zh,
            "start_time_utc": self.start_time_utc,
            "stage": self.stage,
            "venue": self.venue,
            "status": self.status,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "last_source_update": self.last_source_update,
            "source_url": self.source_url,
        }
```

Create `worldcup-2026-calendar/data/teams.zh-CN.json`:

```json
{
  "Argentina": "阿根廷",
  "France": "法国",
  "United States": "美国",
  "Canada": "加拿大",
  "Mexico": "墨西哥",
  "To Be Determined": "待定"
}
```

Create `worldcup-2026-calendar/data/matches.snapshot.json`:

```json
[]
```

Create `worldcup-2026-calendar/public/worldcup-2026.ics`:

```text
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//worldcup-2026-calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:2026 世界杯赛程
END:VCALENDAR
```

Create `worldcup-2026-calendar/public/status.json`:

```json
{
  "last_success_at": null,
  "matches_total": 0,
  "matches_finished": 0,
  "source": "fifa",
  "calendar_url": ""
}
```

- [ ] **Step 4: Run the model test and verify it passes**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_models.py -v`

Expected: PASS with 2 tests passing.

- [ ] **Step 5: Commit**

Run:

```bash
cd worldcup-2026-calendar && git add . && git commit -m "feat: add calendar project skeleton"
```

Expected: commit succeeds if the project folder is its own git repository. If it is still inside the parent repository, do not commit from the subfolder; instead report that commit ownership should be decided before committing.

---

### Task 2: Snapshot Load, Save, and Merge Rules

**Files:**
- Create: `worldcup-2026-calendar/scripts/snapshot.py`
- Test: `worldcup-2026-calendar/tests/test_snapshot.py`

- [ ] **Step 1: Create failing snapshot tests**

Create `worldcup-2026-calendar/tests/test_snapshot.py`:

```python
from scripts.models import Match
from scripts.snapshot import merge_matches


def make_match(match_id="match-1", status="scheduled", home_score=None, away_score=None, venue="Old Stadium"):
    return Match.from_dict(
        {
            "match_id": match_id,
            "home_team_en": "Argentina",
            "away_team_en": "France",
            "home_team_zh": "阿根廷",
            "away_team_zh": "法国",
            "start_time_utc": "2026-07-20T00:00:00Z",
            "stage": "决赛",
            "venue": venue,
            "status": status,
            "home_score": home_score,
            "away_score": away_score,
            "last_source_update": "2026-07-20T05:30:00Z",
            "source_url": "https://www.fifa.com/",
        }
    )


def test_new_match_is_added():
    merged = merge_matches([], [make_match()])
    assert [match.match_id for match in merged] == ["match-1"]


def test_scheduled_match_can_update_venue():
    old = make_match(venue="Old Stadium")
    new = make_match(venue="New Stadium")
    merged = merge_matches([old], [new])
    assert merged[0].venue == "New Stadium"


def test_finished_score_is_not_downgraded_by_empty_later_scrape():
    old = make_match(status="finished", home_score=2, away_score=1)
    new = make_match(status="scheduled", home_score=None, away_score=None)
    merged = merge_matches([old], [new])
    assert merged[0].status == "finished"
    assert merged[0].home_score == 2
    assert merged[0].away_score == 1


def test_missing_match_is_retained():
    old = make_match(match_id="match-1")
    merged = merge_matches([old], [])
    assert merged[0].match_id == "match-1"
```

- [ ] **Step 2: Run the snapshot tests and verify they fail**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_snapshot.py -v`

Expected: FAIL because `scripts.snapshot` does not exist.

- [ ] **Step 3: Implement snapshot merge logic**

Create `worldcup-2026-calendar/scripts/snapshot.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.models import Match


def load_snapshot(path: Path) -> list[Match]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Match.from_dict(item) for item in data]


def save_snapshot(path: Path, matches: list[Match]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [match.to_dict() for match in sorted(matches, key=lambda item: item.start_time_utc)]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_finished_with_score(match: Match) -> bool:
    return match.status == "finished" and match.home_score is not None and match.away_score is not None


def merge_match(old: Match | None, new: Match) -> Match:
    if old is None:
        return new
    if is_finished_with_score(old) and not is_finished_with_score(new):
        return old
    return new


def merge_matches(existing: list[Match], incoming: list[Match]) -> list[Match]:
    by_id = {match.match_id: match for match in existing}
    for new_match in incoming:
        by_id[new_match.match_id] = merge_match(by_id.get(new_match.match_id), new_match)
    return sorted(by_id.values(), key=lambda item: item.start_time_utc)
```

- [ ] **Step 4: Run snapshot tests and full current suite**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_models.py tests/test_snapshot.py -v`

Expected: PASS with all model and snapshot tests passing.

- [ ] **Step 5: Commit**

Run:

```bash
cd worldcup-2026-calendar && git add scripts/snapshot.py tests/test_snapshot.py && git commit -m "feat: preserve completed match snapshots"
```

Expected: commit succeeds only if `worldcup-2026-calendar/` is a git repository.

---

### Task 3: ICS Calendar Generation

**Files:**
- Create: `worldcup-2026-calendar/scripts/build_ics.py`
- Test: `worldcup-2026-calendar/tests/test_build_ics.py`

- [ ] **Step 1: Create failing ICS tests**

Create `worldcup-2026-calendar/tests/test_build_ics.py`:

```python
from scripts.build_ics import build_calendar
from scripts.models import Match


def make_finished_match():
    return Match.from_dict(
        {
            "match_id": "final-2026",
            "home_team_en": "Argentina",
            "away_team_en": "France",
            "home_team_zh": "阿根廷",
            "away_team_zh": "法国",
            "start_time_utc": "2026-07-20T00:00:00Z",
            "stage": "决赛",
            "venue": "MetLife Stadium",
            "status": "finished",
            "home_score": 2,
            "away_score": 1,
            "last_source_update": "2026-07-20T05:30:00Z",
            "source_url": "https://www.fifa.com/",
        }
    )


def test_calendar_contains_stable_uid_title_and_score():
    ics = build_calendar([make_finished_match()], generated_at_utc="2026-07-20T05:30:00Z")
    assert "BEGIN:VCALENDAR" in ics
    assert "UID:final-2026@worldcup-2026-calendar" in ics
    assert "SUMMARY:阿根廷 vs 法国" in ics
    assert "比分：2-1" in ics
    assert "北京时间：2026-07-20 08:00" in ics


def test_calendar_escapes_commas_and_backslashes():
    match = make_finished_match()
    changed = Match.from_dict({**match.to_dict(), "venue": "A, B\\C"})
    ics = build_calendar([changed], generated_at_utc="2026-07-20T05:30:00Z")
    assert "场地：A\\, B\\\\C" in ics
```

- [ ] **Step 2: Run the ICS tests and verify they fail**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_build_ics.py -v`

Expected: FAIL because `scripts.build_ics` does not exist.

- [ ] **Step 3: Implement ICS generation**

Create `worldcup-2026-calendar/scripts/build_ics.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.models import Match


BEIJING = timezone(timedelta(hours=8))
STATUS_LABELS = {
    "scheduled": "未开始",
    "live": "进行中",
    "finished": "已结束",
    "postponed": "延期",
    "cancelled": "取消",
}


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_ics_datetime(value: str) -> str:
    return parse_utc(value).strftime("%Y%m%dT%H%M%SZ")


def format_beijing(value: str) -> str:
    return parse_utc(value).astimezone(BEIJING).strftime("%Y-%m-%d %H:%M")


def escape_ics(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def score_text(match: Match) -> str:
    if match.home_score is None or match.away_score is None:
        return "未定"
    return f"{match.home_score}-{match.away_score}"


def build_description(match: Match) -> str:
    lines = [
        f"状态：{STATUS_LABELS[match.status]}",
        f"比分：{score_text(match)}",
        f"阶段：{match.stage}",
        f"场地：{match.venue}",
        f"北京时间：{format_beijing(match.start_time_utc)}",
        f"最近更新时间：{format_beijing(match.last_source_update)}" if match.last_source_update else "最近更新时间：未知",
        f"数据来源：{match.source_url}",
    ]
    return "\\n".join(escape_ics(line) for line in lines)


def build_event(match: Match, generated_at_utc: str) -> str:
    start = parse_utc(match.start_time_utc)
    end = start + timedelta(hours=2)
    return "\n".join(
        [
            "BEGIN:VEVENT",
            f"UID:{escape_ics(match.match_id)}@worldcup-2026-calendar",
            f"DTSTAMP:{format_ics_datetime(generated_at_utc)}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{escape_ics(match.title)}",
            f"DESCRIPTION:{build_description(match)}",
            f"LOCATION:{escape_ics(match.venue)}",
            "END:VEVENT",
        ]
    )


def build_calendar(matches: list[Match], generated_at_utc: str) -> str:
    events = [build_event(match, generated_at_utc) for match in sorted(matches, key=lambda item: item.start_time_utc)]
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//worldcup-2026-calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:2026 世界杯赛程",
        *events,
        "END:VCALENDAR",
    ]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run ICS tests and current suite**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_models.py tests/test_snapshot.py tests/test_build_ics.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
cd worldcup-2026-calendar && git add scripts/build_ics.py tests/test_build_ics.py && git commit -m "feat: generate world cup ICS feed"
```

Expected: commit succeeds only if `worldcup-2026-calendar/` is a git repository.

---

### Task 4: FIFA Fetcher and Parser Interface

**Files:**
- Create: `worldcup-2026-calendar/scripts/fetch_fifa.py`
- Create: `worldcup-2026-calendar/scripts/parse_fifa.py`
- Test: `worldcup-2026-calendar/tests/test_parse_fifa.py`

- [ ] **Step 1: Create failing parser tests**

Create `worldcup-2026-calendar/tests/test_parse_fifa.py`:

```python
import json

from scripts.parse_fifa import parse_matches


def test_parse_matches_from_fixture_json():
    payload = json.dumps(
        {
            "matches": [
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
        }
    )
    teams = {"Argentina": "阿根廷", "France": "法国"}
    matches = parse_matches(payload, teams, source_update_utc="2026-07-20T05:30:00Z")

    assert len(matches) == 1
    assert matches[0].match_id == "final-2026"
    assert matches[0].home_team_zh == "阿根廷"
    assert matches[0].away_score == 1
```

- [ ] **Step 2: Run parser tests and verify they fail**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_parse_fifa.py -v`

Expected: FAIL because `scripts.parse_fifa` does not exist.

- [ ] **Step 3: Implement fetcher and parser**

Create `worldcup-2026-calendar/scripts/fetch_fifa.py`:

```python
from __future__ import annotations

import time
import urllib.request
from pathlib import Path


DEFAULT_URL = "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026"


def fetch_url(url: str = DEFAULT_URL, timeout: int = 20, attempts: int = 2) -> str:
    headers = {"User-Agent": "Mozilla/5.0 worldcup-2026-calendar/1.0"}
    request = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2)
    raise RuntimeError(f"Failed to fetch FIFA data from {url}: {last_error}")


def save_raw_response(raw_dir: Path, content: str) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "fifa-latest.txt"
    path.write_text(content, encoding="utf-8")
    return path
```

Create `worldcup-2026-calendar/scripts/parse_fifa.py`:

```python
from __future__ import annotations

import json
from typing import Any

from scripts.models import Match


def translate(team: str, teams_zh: dict[str, str]) -> str:
    return teams_zh.get(team, team)


def parse_json_payload(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("FIFA parser currently expects JSON or extracted JSON fixture data") from exc


def parse_matches(content: str, teams_zh: dict[str, str], source_update_utc: str) -> list[Match]:
    payload = parse_json_payload(content)
    raw_matches = payload.get("matches", [])
    matches: list[Match] = []
    for item in raw_matches:
        home = str(item["home"])
        away = str(item["away"])
        score = item.get("score") or {}
        matches.append(
            Match.from_dict(
                {
                    "match_id": item["id"],
                    "home_team_en": home,
                    "away_team_en": away,
                    "home_team_zh": translate(home, teams_zh),
                    "away_team_zh": translate(away, teams_zh),
                    "start_time_utc": item["kickoff"],
                    "stage": item.get("stage", ""),
                    "venue": item.get("venue", ""),
                    "status": item.get("status", "scheduled"),
                    "home_score": score.get("home"),
                    "away_score": score.get("away"),
                    "last_source_update": source_update_utc,
                    "source_url": item.get("url", ""),
                }
            )
        )
    return matches
```

- [ ] **Step 4: Run parser tests and current suite**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_models.py tests/test_snapshot.py tests/test_build_ics.py tests/test_parse_fifa.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
cd worldcup-2026-calendar && git add scripts/fetch_fifa.py scripts/parse_fifa.py tests/test_parse_fifa.py && git commit -m "feat: parse FIFA match payloads"
```

Expected: commit succeeds only if `worldcup-2026-calendar/` is a git repository.

---

### Task 5: Update Orchestrator and End-to-End Generation

**Files:**
- Create: `worldcup-2026-calendar/scripts/update_calendar.py`
- Test: `worldcup-2026-calendar/tests/test_update_calendar.py`

- [ ] **Step 1: Create failing orchestration test**

Create `worldcup-2026-calendar/tests/test_update_calendar.py`:

```python
import json
from pathlib import Path

from scripts.update_calendar import update_from_content


def test_update_from_content_writes_snapshot_calendar_and_status(tmp_path: Path):
    project = tmp_path
    (project / "data").mkdir()
    (project / "public").mkdir()
    (project / "data" / "matches.snapshot.json").write_text("[]\n", encoding="utf-8")
    (project / "data" / "teams.zh-CN.json").write_text(
        json.dumps({"Argentina": "阿根廷", "France": "法国"}, ensure_ascii=False),
        encoding="utf-8",
    )
    content = json.dumps(
        {
            "matches": [
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
        }
    )

    update_from_content(project, content, now_utc="2026-07-20T05:30:00Z")

    assert "阿根廷 vs 法国" in (project / "public" / "worldcup-2026.ics").read_text(encoding="utf-8")
    status = json.loads((project / "public" / "status.json").read_text(encoding="utf-8"))
    assert status["matches_total"] == 1
    assert status["matches_finished"] == 1
```

- [ ] **Step 2: Run orchestration test and verify it fails**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_update_calendar.py -v`

Expected: FAIL because `scripts.update_calendar` does not exist.

- [ ] **Step 3: Implement orchestrator**

Create `worldcup-2026-calendar/scripts/update_calendar.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_ics import build_calendar
from scripts.fetch_fifa import fetch_url, save_raw_response
from scripts.parse_fifa import parse_matches
from scripts.snapshot import load_snapshot, merge_matches, save_snapshot


CALENDAR_URL = "https://<github-user>.github.io/worldcup-2026-calendar/worldcup-2026.ics"


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
        "calendar_url": CALENDAR_URL,
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
    main()
```

- [ ] **Step 4: Run full Python test suite**

Run: `cd worldcup-2026-calendar && python -m pytest -v`

Expected: PASS.

- [ ] **Step 5: Run local generator against fixture path through test only**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_update_calendar.py -v`

Expected: PASS and verifies snapshot, ICS, and status output are written in a temporary project directory.

- [ ] **Step 6: Commit**

Run:

```bash
cd worldcup-2026-calendar && git add scripts/update_calendar.py tests/test_update_calendar.py && git commit -m "feat: orchestrate calendar updates"
```

Expected: commit succeeds only if `worldcup-2026-calendar/` is a git repository.

---

### Task 6: GitHub Actions and Pages Publishing

**Files:**
- Create: `worldcup-2026-calendar/.github/workflows/update-calendar.yml`

- [ ] **Step 1: Create workflow file**

Create `worldcup-2026-calendar/.github/workflows/update-calendar.yml`:

```yaml
name: Update World Cup Calendar

on:
  schedule:
    - cron: "30 0 * * *"
    - cron: "30 5 * * *"
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: update-worldcup-calendar
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install test dependencies
        run: python -m pip install -r requirements-dev.txt

      - name: Run tests
        run: python -m pytest -v

      - name: Update calendar files
        run: python scripts/update_calendar.py

      - name: Commit generated changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: update generated world cup calendar"
          file_pattern: data/matches.snapshot.json data/raw/latest/fifa-latest.txt public/worldcup-2026.ics public/status.json

      - name: Configure Pages
        uses: actions/configure-pages@v5

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: public

      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Validate workflow syntax is parseable as YAML**

Run: `cd worldcup-2026-calendar && python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/update-calendar.yml').read_text())"`

Expected: command succeeds if PyYAML is installed. If PyYAML is unavailable, skip this local check and rely on GitHub Actions validation after pushing.

- [ ] **Step 3: Run tests after adding workflow**

Run: `cd worldcup-2026-calendar && python -m pytest -v`

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
cd worldcup-2026-calendar && git add .github/workflows/update-calendar.yml && git commit -m "ci: schedule calendar updates"
```

Expected: commit succeeds only if `worldcup-2026-calendar/` is a git repository.

---

### Task 7: README and Operational Documentation

**Files:**
- Create: `worldcup-2026-calendar/README.md`

- [ ] **Step 1: Create README**

Create `worldcup-2026-calendar/README.md`:

```markdown
# 2026 World Cup Calendar

Public ICS subscription calendar for the 2026 FIFA World Cup.

## Subscription

After GitHub Pages is enabled, subscribe to:

```text
https://<github-user>.github.io/worldcup-2026-calendar/worldcup-2026.ics
```

The feed contains the full tournament schedule. Completed matches remain in the calendar with final scores.

## Update Schedule

GitHub Actions updates the calendar twice per day:

- Beijing time 08:30
- Beijing time 13:30

Calendar apps may refresh subscribed calendars later than the publication time.

## Local Development

Install test dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
python -m pytest -v
```

Run the updater:

```bash
python scripts/update_calendar.py
```

Generated files:

- `data/matches.snapshot.json`
- `public/worldcup-2026.ics`
- `public/status.json`

## Operations

Use the GitHub Actions `Update World Cup Calendar` workflow to trigger a manual refresh.

Check publication status at:

```text
https://<github-user>.github.io/worldcup-2026-calendar/status.json
```

If FIFA source parsing fails, the workflow fails and the previous published ICS remains available.
```

- [ ] **Step 2: Run tests**

Run: `cd worldcup-2026-calendar && python -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
cd worldcup-2026-calendar && git add README.md && git commit -m "docs: document calendar operations"
```

Expected: commit succeeds only if `worldcup-2026-calendar/` is a git repository.

---

### Task 8: Repository Setup and GitHub Deployment

**Files:**
- Modify only repository metadata and GitHub settings unless a deployment error requires code changes.

- [ ] **Step 1: Decide repository ownership**

Confirm the GitHub owner and repository name. Use repository name `worldcup-2026-calendar` unless explicitly changed.

- [ ] **Step 2: Initialize git repository if needed**

Run: `cd worldcup-2026-calendar && git status --short`

Expected: If this reports `fatal: not a git repository`, initialize a dedicated repository with `git init`. If it reports normal status, use the existing repository.

- [ ] **Step 3: Create GitHub repository**

Run: `gh repo create worldcup-2026-calendar --public --source=. --remote=origin --push`

Expected: GitHub repository is created and local files are pushed. If the repository already exists, use `gh repo view worldcup-2026-calendar` and set `origin` to the existing remote.

- [ ] **Step 4: Enable GitHub Pages through Actions**

Run: `gh api -X POST repos/:owner/worldcup-2026-calendar/pages -f build_type=workflow`

Expected: GitHub Pages is enabled for workflow deployment. If GitHub returns that Pages already exists, continue.

- [ ] **Step 5: Trigger workflow manually**

Run: `gh workflow run "Update World Cup Calendar" --repo :owner/worldcup-2026-calendar`

Expected: workflow starts.

- [ ] **Step 6: Verify workflow result**

Run: `gh run list --repo :owner/worldcup-2026-calendar --workflow "Update World Cup Calendar" --limit 1`

Expected: latest run eventually reaches `completed` with `success`. If it fails due to FIFA parsing, preserve the failure output and adjust `parse_fifa.py` in a follow-up task.

- [ ] **Step 7: Verify public files**

Run: `python3 - <<'PY'
import urllib.request
for url in [
    'https://<github-user>.github.io/worldcup-2026-calendar/worldcup-2026.ics',
    'https://<github-user>.github.io/worldcup-2026-calendar/status.json',
]:
    with urllib.request.urlopen(url, timeout=20) as response:
        print(url, response.status, response.getheader('content-type'))
PY`

Expected: both URLs return HTTP 200. The ICS response contains `BEGIN:VCALENDAR`; the status response is JSON.

---

## Plan Self-Review

Spec coverage:

- Dedicated project folder: Task 1 and file structure place all files under `worldcup-2026-calendar/`.
- Twice-daily Beijing schedule: Task 6 uses UTC cron `30 0` and `30 5`.
- Full-tournament ICS: Task 3 builds a complete calendar from all snapshot matches.
- Completed scores retained: Task 2 implements and tests finished-score preservation.
- FIFA source path: Task 4 creates fetcher and parser boundaries.
- GitHub Pages output: Task 6 deploys `public/`.
- Status file: Task 5 writes `public/status.json`.
- GitHub authorization path: Task 8 covers repo creation, Pages, workflow, and URL verification.

Placeholder scan:

- The plan intentionally uses `<github-user>` and `:owner` only where GitHub account-specific values must be substituted at deployment time.
- No implementation steps are left without file paths, commands, or expected results.

Type consistency:

- `Match`, `merge_matches`, `build_calendar`, `parse_matches`, and `update_from_content` names are consistent across tests and implementation steps.
