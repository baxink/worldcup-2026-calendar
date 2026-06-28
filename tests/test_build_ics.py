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
