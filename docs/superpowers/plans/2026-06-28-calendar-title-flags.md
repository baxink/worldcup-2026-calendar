# Calendar Title Flags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Unicode flag emoji before real team names in ICS event titles while leaving knockout placeholders unflagged.

**Architecture:** Keep the change in the title-generation layer. Add a small `TEAM_FLAGS` mapping and title formatter in `scripts/models.py`, so `build_ics.py` continues to use `match.title` without knowing flag rules.

**Tech Stack:** Python 3.11 standard library, pytest, existing GitHub Actions deployment.

---

## File Structure

- Modify `scripts/models.py`: add flag mapping and title formatting.
- Modify `tests/test_models.py`: test real-team flags and placeholder no-flag behavior.
- Modify generated `data/matches.snapshot.json` and `public/worldcup-2026.ics` by running the updater.

---

### Task 1: Flagged Match Titles

**Files:**
- Modify: `worldcup-2026-calendar/scripts/models.py`
- Modify: `worldcup-2026-calendar/tests/test_models.py`
- Generated after updater: `worldcup-2026-calendar/data/matches.snapshot.json`
- Generated after updater: `worldcup-2026-calendar/public/worldcup-2026.ics`

- [ ] **Step 1: Write failing tests**

Append these tests to `worldcup-2026-calendar/tests/test_models.py`:

```python
def test_match_title_adds_flags_for_real_teams():
    match = Match.from_dict(
        {
            "match_id": "match-flag",
            "home_team_en": "Mexico",
            "away_team_en": "South Africa",
            "home_team_zh": "墨西哥",
            "away_team_zh": "南非",
            "start_time_utc": "2026-06-11T19:00:00Z",
            "stage": "小组赛 A组",
            "venue": "墨西哥 墨西哥城 墨西哥城体育场（阿兹特克体育场）",
            "status": "finished",
            "home_score": 2,
            "away_score": 0,
            "last_source_update": "2026-06-28T12:00:00Z",
            "source_url": "",
        }
    )

    assert match.title == "🇲🇽 墨西哥 vs 🇿🇦 南非"


def test_match_title_does_not_add_flags_for_placeholders():
    match = Match.from_dict(
        {
            "match_id": "match-placeholder",
            "home_team_en": "W73",
            "away_team_en": "RU101",
            "home_team_zh": "胜者73",
            "away_team_zh": "负者101",
            "start_time_utc": "2026-07-04T19:00:00Z",
            "stage": "八分之一决赛",
            "venue": "美国 费城 费城体育场（林肯金融球场）",
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "last_source_update": "2026-06-28T12:00:00Z",
            "source_url": "",
        }
    )

    assert match.title == "胜者73 vs 负者101"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_models.py -v`

Expected: FAIL on `test_match_title_adds_flags_for_real_teams` because current title lacks flags.

- [ ] **Step 3: Implement title flag mapping**

Modify `worldcup-2026-calendar/scripts/models.py` by adding this mapping near the status constants:

```python
TEAM_FLAGS = {
    "Algeria": "🇩🇿",
    "Argentina": "🇦🇷",
    "Australia": "🇦🇺",
    "Austria": "🇦🇹",
    "Belgium": "🇧🇪",
    "Bosnia and Herzegovina": "🇧🇦",
    "Brazil": "🇧🇷",
    "Cabo Verde": "🇨🇻",
    "Canada": "🇨🇦",
    "Colombia": "🇨🇴",
    "Congo DR": "🇨🇩",
    "Croatia": "🇭🇷",
    "Curaçao": "🇨🇼",
    "Czechia": "🇨🇿",
    "Côte d'Ivoire": "🇨🇮",
    "Ecuador": "🇪🇨",
    "Egypt": "🇪🇬",
    "England": "🏴",
    "France": "🇫🇷",
    "Germany": "🇩🇪",
    "Ghana": "🇬🇭",
    "Haiti": "🇭🇹",
    "IR Iran": "🇮🇷",
    "Iraq": "🇮🇶",
    "Japan": "🇯🇵",
    "Jordan": "🇯🇴",
    "Korea Republic": "🇰🇷",
    "Mexico": "🇲🇽",
    "Morocco": "🇲🇦",
    "Netherlands": "🇳🇱",
    "New Zealand": "🇳🇿",
    "Norway": "🇳🇴",
    "Panama": "🇵🇦",
    "Paraguay": "🇵🇾",
    "Portugal": "🇵🇹",
    "Qatar": "🇶🇦",
    "Saudi Arabia": "🇸🇦",
    "Scotland": "🏴",
    "Senegal": "🇸🇳",
    "South Africa": "🇿🇦",
    "Spain": "🇪🇸",
    "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭",
    "Tunisia": "🇹🇳",
    "Türkiye": "🇹🇷",
    "USA": "🇺🇸",
    "United States": "🇺🇸",
    "Uruguay": "🇺🇾",
    "Uzbekistan": "🇺🇿",
}
```

Add this helper:

```python
def team_title(team_en: str, team_zh: str) -> str:
    flag = TEAM_FLAGS.get(team_en)
    if not flag:
        return team_zh
    return f"{flag} {team_zh}"
```

Change `Match.title` to:

```python
    @property
    def title(self) -> str:
        return f"{team_title(self.home_team_en, self.home_team_zh)} vs {team_title(self.away_team_en, self.away_team_zh)}"
```

- [ ] **Step 4: Run model tests and full suite**

Run: `cd worldcup-2026-calendar && python -m pytest tests/test_models.py -v`

Expected: PASS.

Run: `cd worldcup-2026-calendar && python -m pytest -v`

Expected: PASS.

- [ ] **Step 5: Regenerate calendar from FIFA API**

Run: `cd worldcup-2026-calendar && GITHUB_REPOSITORY=baxink/worldcup-2026-calendar python scripts/update_calendar.py`

Expected: command exits 0 and regenerates `public/worldcup-2026.ics`.

- [ ] **Step 6: Verify generated ICS title examples**

Run:

```bash
cd worldcup-2026-calendar && python3 - <<'PY'
from pathlib import Path
ics = Path('public/worldcup-2026.ics').read_text(encoding='utf-8')
assert 'SUMMARY:🇲🇽 墨西哥 vs 🇿🇦 南非' in ics
assert 'SUMMARY:胜者73 vs 胜者75' in ics
print('flag title checks passed')
PY
```

Expected: prints `flag title checks passed`.

- [ ] **Step 7: Commit and deploy**

Run:

```bash
cd worldcup-2026-calendar && git add scripts/models.py tests/test_models.py public/worldcup-2026.ics data/matches.snapshot.json public/status.json && git commit -m "feat: add flags to calendar titles" && git push
```

Expected: push succeeds.

Run:

```bash
cd worldcup-2026-calendar && gh workflow run "Update World Cup Calendar" --repo baxink/worldcup-2026-calendar
```

Expected: workflow starts.

- [ ] **Step 8: Verify public ICS after deployment**

Run:

```bash
cd worldcup-2026-calendar && python3 - <<'PY'
import ssl
import urllib.request
ctx = ssl._create_unverified_context()
url = 'https://baxink.github.io/worldcup-2026-calendar/worldcup-2026.ics'
with urllib.request.urlopen(url, timeout=30, context=ctx) as response:
    body = response.read().decode('utf-8', errors='replace')
assert 'SUMMARY:🇲🇽 墨西哥 vs 🇿🇦 南非' in body
assert 'SUMMARY:胜者73 vs 胜者75' in body
print('public flag title checks passed')
PY
```

Expected: prints `public flag title checks passed`.

---

## Plan Self-Review

Spec coverage:

- Real teams get flags: Task 1 tests and implements `TEAM_FLAGS`.
- Placeholders stay unflagged: Task 1 tests `W73` and `RU101` with no flag.
- ICS title changes only: implementation changes `Match.title`, which `build_ics.py` already uses for `SUMMARY`.
- No image/attachment complexity: plan uses Unicode emoji only.

Placeholder scan:

- The plan contains no incomplete implementation placeholders. The word placeholder appears only as a domain term for knockout placeholders.

Type consistency:

- `TEAM_FLAGS`, `team_title`, and `Match.title` are defined and used consistently.
