import pytest
from scripts.models import TEAM_FLAGS, Match, normalize_status, parse_score


def test_parse_score_float_returns_int():
    assert parse_score(2.0) == 2


def test_parse_score_float_str_returns_int():
    assert parse_score("2.0") == 2


def test_parse_score_bool_raises_value_error():
    with pytest.raises(ValueError, match="Invalid score"):
        parse_score(False)


def test_parse_score_none_is_none():
    assert parse_score(None) is None


def test_parse_score_empty_str_is_none():
    assert parse_score("") is None


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
    assert match.title == "🇦🇷 阿根廷 vs 🇫🇷 法国"


def test_normalize_status_rejects_unknown_status():
    try:
        normalize_status("abandoned")
    except ValueError as exc:
        assert "Unsupported match status" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


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


def test_match_title_uses_distinct_england_and_scotland_flags():
    england = Match.from_dict(
        {
            "match_id": "eng",
            "home_team_en": "England",
            "away_team_en": "France",
            "home_team_zh": "英格兰",
            "away_team_zh": "法国",
            "start_time_utc": "2026-06-11T19:00:00Z",
            "stage": "小组赛 A组",
            "venue": "美国 波士顿 波士顿体育场（吉列体育场）",
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "last_source_update": "2026-06-28T12:00:00Z",
            "source_url": "",
        }
    )
    scotland = Match.from_dict(
        {
            "match_id": "sco",
            "home_team_en": "Scotland",
            "away_team_en": "France",
            "home_team_zh": "苏格兰",
            "away_team_zh": "法国",
            "start_time_utc": "2026-06-11T19:00:00Z",
            "stage": "小组赛 A组",
            "venue": "美国 波士顿 波士顿体育场（吉列体育场）",
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "last_source_update": "2026-06-28T12:00:00Z",
            "source_url": "",
        }
    )

    assert england.title.startswith("🏴")
    assert scotland.title.startswith("🏴")
    assert england.title != scotland.title


def test_team_flags_use_distinct_uk_sequences():
    assert TEAM_FLAGS["England"] != TEAM_FLAGS["Scotland"]
    assert len(TEAM_FLAGS["England"]) > 1
    assert len(TEAM_FLAGS["Scotland"]) > 1
