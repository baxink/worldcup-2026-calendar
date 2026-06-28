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
