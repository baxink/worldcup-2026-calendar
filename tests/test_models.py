import pytest
from scripts.models import Match, normalize_status, parse_score


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
    assert match.title == "阿根廷 vs 法国"


def test_normalize_status_rejects_unknown_status():
    try:
        normalize_status("abandoned")
    except ValueError as exc:
        assert "Unsupported match status" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
