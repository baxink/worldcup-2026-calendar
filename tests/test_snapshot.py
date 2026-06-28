import pytest

from scripts.models import Match
from scripts.snapshot import merge_matches, load_snapshot, save_snapshot, SnapshotError


def make_match(match_id="match-1", status="scheduled", home_score=None, away_score=None, venue="Old Stadium", start_time_utc="2026-07-20T00:00:00Z"):
    return Match.from_dict(
        {
            "match_id": match_id,
            "home_team_en": "Argentina",
            "away_team_en": "France",
            "home_team_zh": "阿根廷",
            "away_team_zh": "法国",
            "start_time_utc": start_time_utc,
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


def test_load_snapshot_raises_snapshot_error_for_malformed_json(tmp_path):
    bad_file = tmp_path / "matches.snapshot.json"
    bad_file.write_text("{bad json", encoding="utf-8")
    with pytest.raises(SnapshotError, match="Invalid snapshot JSON"):
        load_snapshot(bad_file)


def test_save_snapshot_round_trips_matches(tmp_path):
    m1 = make_match(match_id="match-1", start_time_utc="2026-07-21T00:00:00Z")
    m2 = make_match(match_id="match-2", start_time_utc="2026-07-20T00:00:00Z")
    path = tmp_path / "matches.snapshot.json"
    save_snapshot(path, [m1, m2])
    loaded = load_snapshot(path)
    assert len(loaded) == 2
    assert loaded[0].match_id == "match-2"
    assert loaded[1].match_id == "match-1"


def test_live_score_is_not_downgraded_by_empty_later_scrape():
    old = make_match(status="live", home_score=2, away_score=1)
    new = make_match(status="scheduled", home_score=None, away_score=None)
    merged = merge_matches([old], [new])
    assert merged[0].status == "live"
    assert merged[0].home_score == 2
    assert merged[0].away_score == 1


def test_same_start_time_sorted_by_match_id():
    m_b = make_match(match_id="match-b")
    m_a = make_match(match_id="match-a")
    merged = merge_matches([], [m_b, m_a])
    assert [m.match_id for m in merged] == ["match-a", "match-b"]
