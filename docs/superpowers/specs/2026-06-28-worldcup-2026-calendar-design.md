# 2026 World Cup Calendar Subscription Design

Date: 2026-06-28
Status: Draft for user review

## Goal

Build a public calendar subscription for the 2026 FIFA World Cup. The calendar must expose one full-tournament `.ics` URL that users can subscribe to from Apple Calendar, Google Calendar, Outlook, and other calendar clients.

The calendar must update automatically twice per day at Beijing time 08:30 and 13:30. Updates should include match progress, current scores when available, and final scores after matches finish. Completed matches and their final scores must remain in the calendar for the lifetime of the project.

The project should live in its own local project folder, `worldcup-2026-calendar/`, and use free GitHub resources only: GitHub repository storage, GitHub Actions for scheduled generation, and GitHub Pages for public hosting.

## Recommended Architecture

Create a dedicated local project folder and public GitHub repository named `worldcup-2026-calendar`. The project stores the scraping scripts, normalized match snapshot, Chinese team-name mapping, generated ICS file, status file, and GitHub Actions workflow.

```text
FIFA public pages or page data
  -> GitHub Actions scheduled job
  -> fetch raw FIFA data
  -> parse and normalize matches
  -> merge with persisted match snapshot
  -> generate complete worldcup-2026.ics
  -> publish public files through GitHub Pages
  -> user's calendar client subscribes to the ICS URL
```

The public subscription URL should be stable:

```text
https://<github-user>.github.io/worldcup-2026-calendar/worldcup-2026.ics
```

The project also publishes an operational status file:

```text
https://<github-user>.github.io/worldcup-2026-calendar/status.json
```

## Major Components

### Project Folder and GitHub Repository

The `worldcup-2026-calendar/` folder is the project root. The corresponding GitHub repository is the canonical remote source and runtime container for the project.

Responsibilities:

- Store scripts and tests.
- Store Chinese team-name mappings.
- Store the persisted match snapshot.
- Store generated public files for GitHub Pages.
- Store GitHub Actions workflow configuration.
- Store project-specific specs and plans under `worldcup-2026-calendar/docs/superpowers/`.

Recommended structure:

```text
worldcup-2026-calendar/
  .github/workflows/update-calendar.yml
  docs/superpowers/specs/
    2026-06-28-worldcup-2026-calendar-design.md
  scripts/
    fetch_fifa.py
    parse_fifa.py
    build_ics.py
    update_calendar.py
  data/
    teams.zh-CN.json
    matches.snapshot.json
    raw/latest/
  public/
    worldcup-2026.ics
    status.json
  tests/
    fixtures/
    test_parse_fifa.py
    test_build_ics.py
  README.md
```

### GitHub Actions Scheduler

GitHub Actions runs the update workflow twice per day.

Required Beijing-time schedule:

- 08:30 Asia/Shanghai
- 13:30 Asia/Shanghai

GitHub Actions `cron` uses UTC. The workflow should therefore schedule:

```yaml
on:
  schedule:
    - cron: "30 0 * * *"
    - cron: "30 5 * * *"
  workflow_dispatch:
```

The manual `workflow_dispatch` trigger allows an authorized maintainer to run an immediate update from GitHub when needed.

### FIFA Fetcher

`fetch_fifa.py` requests FIFA public pages or page-embedded data and stores the raw response under `data/raw/latest/` for troubleshooting.

Responsibilities:

- Use a normal browser-like `User-Agent`.
- Apply request timeout and retry limits.
- Save the raw response from the latest run.
- Return a clear failure if FIFA blocks, times out, or changes its response shape.

The fetcher should not contain ICS generation logic. It only retrieves source material.

### FIFA Parser

`parse_fifa.py` extracts match data from the raw FIFA response and converts it into the internal match model.

Responsibilities:

- Extract stable match IDs.
- Extract teams, kickoff time, stage, venue, status, and score.
- Preserve source URLs where available.
- Normalize status values into the project's controlled vocabulary.

If FIFA changes its page structure, this parser should be the primary file that needs maintenance.

### Match Snapshot

`data/matches.snapshot.json` is the durable project state. It prevents completed results from being lost when later scrapes are incomplete or wrong.

Each match should use this model:

```json
{
  "match_id": "stable-fifa-match-id",
  "home_team_en": "Argentina",
  "away_team_en": "France",
  "home_team_zh": "阿根廷",
  "away_team_zh": "法国",
  "start_time_utc": "2026-06-14T00:00:00Z",
  "stage": "小组赛",
  "venue": "Example Stadium",
  "status": "scheduled",
  "home_score": null,
  "away_score": null,
  "last_source_update": "2026-06-28T05:30:00Z",
  "source_url": "https://www.fifa.com/..."
}
```

Allowed statuses:

- `scheduled`
- `live`
- `finished`
- `postponed`
- `cancelled`

### Chinese Team Name Mapping

`data/teams.zh-CN.json` maps FIFA team names or abbreviations to Chinese display names.

The first version should use a static mapping file rather than a translation API. This avoids runtime cost, API keys, and inconsistent translations.

### ICS Builder

`build_ics.py` generates `public/worldcup-2026.ics` from the merged snapshot.

Responsibilities:

- Output one full-tournament calendar file.
- Keep completed matches in the calendar.
- Use stable event `UID` values derived from `match_id`.
- Write Chinese event titles.
- Include Beijing-time details in the event description.
- Preserve standard UTC event start times so calendar clients can convert to the user's local timezone.

Event title format:

```text
阿根廷 vs 法国
```

Event description format:

```text
状态：已结束
比分：2-1
阶段：决赛
场地：Example Stadium
北京时间：2026-07-20 08:00
最近更新时间：2026-07-20 13:30
数据来源：https://www.fifa.com/...
```

## Update Rules

Each scheduled run should parse the latest FIFA data and merge it with the existing snapshot instead of replacing the snapshot blindly.

Rules:

- New matches are added to the snapshot and ICS.
- Scheduled matches can update kickoff time, venue, stage, teams, and source URL.
- Live matches update status and current score.
- Finished matches update status and final score.
- Once a match has a finished status and final score, later scrapes cannot downgrade it to `scheduled`, remove the score, or delete it.
- Missing matches in a single scrape are retained from the previous snapshot.
- Matches are removed only through an explicit `cancelled` state or a deliberate maintainer change.

The ICS file is regenerated from the full merged snapshot on every successful run. This keeps the public calendar complete while allowing individual events to update cleanly in subscribed clients.

## Publishing Flow

The update workflow should run these steps:

1. Check out the repository.
2. Set up Python.
3. Install minimal dependencies.
4. Run parser and builder tests.
5. Run `scripts/update_calendar.py`.
6. Validate that `public/worldcup-2026.ics` and `public/status.json` exist.
7. Commit changed generated files back to the repository or deploy `public/` through the official GitHub Pages artifact workflow.
8. Publish `public/` through GitHub Pages.

The recommended first implementation can commit generated files back to the repository because it makes the latest snapshot and generated ICS easy to inspect. If commit noise becomes undesirable, the project can later switch to Pages artifact-only deployment while still persisting `matches.snapshot.json` through repository commits.

## Error Handling

Expected failures and required behavior:

- FIFA request timeout: fail the workflow and keep the previous public ICS unchanged.
- FIFA returns an unexpected response: fail the workflow and keep the previous public ICS unchanged.
- Parser extracts far fewer matches than the previous snapshot: fail the workflow and keep the previous public ICS unchanged.
- A completed match appears without score in a later scrape: keep the previous final score.
- A scheduled match changes kickoff time or venue: update the event while preserving the same UID.

The workflow should write `public/status.json` after successful runs.

Suggested status shape:

```json
{
  "last_success_at": "2026-06-28T05:30:00Z",
  "matches_total": 104,
  "matches_finished": 0,
  "source": "fifa",
  "calendar_url": "https://<github-user>.github.io/worldcup-2026-calendar/worldcup-2026.ics"
}
```

For failed runs, the GitHub Actions run itself is the primary alert. The implementation can optionally create or update a GitHub Issue for repeated failures.

## Security and Permissions

The project should use the smallest practical GitHub permission set.

Required GitHub capabilities:

- Create or update a public repository.
- Enable GitHub Pages for the repository.
- Allow GitHub Actions to write generated files or deploy Pages artifacts.

No runtime secrets are required for the initial design. The project should avoid cookies, private FIFA credentials, paid API keys, or third-party services unless the FIFA public pages become unusable.

If repository commits are used for generated files, the workflow needs `contents: write`. If Pages artifact deployment is used, the workflow needs `pages: write` and `id-token: write`.

## Testing Strategy

### Parser Tests

Store representative FIFA raw responses under `tests/fixtures/`. Tests should verify extraction of:

- match ID
- home and away teams
- kickoff time
- stage
- venue
- status
- score

### Snapshot Merge Tests

Test the rules that protect completed matches.

Required cases:

- A new match is added.
- A scheduled match changes time.
- A live score updates.
- A finished match keeps its final score when a later scrape has missing score data.
- A missing match is retained rather than deleted.

### ICS Tests

Tests should verify:

- The generated calendar has valid iCalendar structure.
- Each match creates one event.
- Event `UID` stays stable across updates.
- Chinese team names appear in titles.
- Beijing-time text appears in descriptions.
- Completed scores remain visible.

### Workflow Verification

The repository should support a local command equivalent to the GitHub Actions run:

```text
python scripts/update_calendar.py
```

After the command runs, these files must exist:

- `data/matches.snapshot.json`
- `public/worldcup-2026.ics`
- `public/status.json`

## Acceptance Criteria

- A public GitHub Pages URL serves `worldcup-2026.ics`.
- The ICS URL can be subscribed to by Apple Calendar and Google Calendar.
- GitHub Actions runs automatically at Beijing time 08:30 and 13:30.
- A manual GitHub Actions run can trigger an immediate update.
- The calendar contains the full tournament schedule, not only upcoming matches.
- Match status and score update when FIFA data changes.
- Completed matches and final scores remain in the calendar after later updates.
- Failed scrapes do not replace the public calendar with empty or partial data.
- `status.json` reports the last successful update and match counts.

## Non-Goals

- No web application UI in the first version.
- No per-team calendar feeds in the first version.
- No paid football API.
- No database, server, worker, or cloud function outside GitHub.
- No near-real-time score tracking beyond the two daily scheduled updates.
- No private user accounts or personalized calendars.

## Risks

### FIFA Page Changes

FIFA may change page markup or embedded data shape.

Mitigation: isolate parsing in `parse_fifa.py`, keep raw fixtures, and test parser behavior.

### FIFA Access Limits

GitHub Actions may occasionally be blocked or rate limited.

Mitigation: use a browser-like User-Agent, low-frequency schedule, timeouts, retries, and previous-file preservation.

### Calendar Client Refresh Delays

Calendar clients decide when to refetch subscribed calendars. GitHub may update twice daily, but clients may display changes later.

Mitigation: document that update time means publication time, not guaranteed client-visible time.

### Team Name Variants

FIFA may use names or abbreviations that are not in the Chinese mapping file.

Mitigation: fall back to FIFA's original name and report missing translations in the workflow output.

## Implementation Recommendation

Implement this as a small Python static generator in the dedicated `worldcup-2026-calendar/` project folder and matching GitHub repository. Start with the full-tournament ICS only. Add per-team or per-stage feeds later only if the single public feed proves stable.

The design intentionally avoids a web app and any persistent service. The durable state is the repository snapshot, and the runtime is GitHub Actions plus GitHub Pages.
