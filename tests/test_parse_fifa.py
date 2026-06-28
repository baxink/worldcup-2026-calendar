import json

import pytest

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


def test_parse_matches_empty_list_returns_empty_list():
    payload = json.dumps({"matches": []})
    matches = parse_matches(payload, {}, source_update_utc="2026-07-20T00:00:00Z")
    assert matches == []


def test_parse_matches_falls_back_to_original_team_name():
    payload = json.dumps(
        {
            "matches": [
                {
                    "id": "m1",
                    "home": "Argentina",
                    "away": "France",
                    "kickoff": "2026-07-20T00:00:00Z",
                }
            ]
        }
    )
    matches = parse_matches(payload, {}, source_update_utc="2026-07-20T00:00:00Z")
    assert matches[0].home_team_zh == "Argentina"
    assert matches[0].away_team_zh == "France"


def test_parse_matches_allows_partial_score():
    payload = json.dumps(
        {
            "matches": [
                {
                    "id": "m1",
                    "home": "Argentina",
                    "away": "France",
                    "kickoff": "2026-07-20T00:00:00Z",
                    "score": {"home": 1},
                }
            ]
        }
    )
    matches = parse_matches(payload, {}, source_update_utc="2026-07-20T00:00:00Z")
    assert matches[0].home_score == 1
    assert matches[0].away_score is None


def test_parse_matches_reports_missing_required_field():
    payload = json.dumps(
        {
            "matches": [
                {
                    "id": "m1",
                    "home": "Argentina",
                    "away": "France",
                }
            ]
        }
    )
    with pytest.raises(ValueError, match="Missing required FIFA match field"):
        parse_matches(payload, {}, source_update_utc="2026-07-20T00:00:00Z")
    with pytest.raises(ValueError, match="kickoff"):
        parse_matches(payload, {}, source_update_utc="2026-07-20T00:00:00Z")


def _fifa_item(
    *,
    IdMatch="m1",
    HomeTeamName="Argentina",
    AwayTeamName="France",
    Date="2026-07-20T00:00:00Z",
    StageName="决赛",
    StadiumName="MetLife Stadium",
    MatchStatus="0",
    HomeTeamScore=None,
    AwayTeamScore=None,
):
    home = {"TeamName": [{"Description": HomeTeamName}]}
    away = {"TeamName": [{"Description": AwayTeamName}]}
    stage = [{"Description": StageName}]
    stadium = {"Name": [{"Description": StadiumName}]}
    item = {
        "IdMatch": IdMatch,
        "Home": home,
        "Away": away,
        "Date": Date,
        "StageName": stage,
        "Stadium": stadium,
        "MatchStatus": MatchStatus,
    }
    if HomeTeamScore is not None:
        item["HomeTeamScore"] = HomeTeamScore
    if AwayTeamScore is not None:
        item["AwayTeamScore"] = AwayTeamScore
    return item


def test_parse_matches_from_fifa_results_payload():
    payload = json.dumps({"Results": [_fifa_item(IdMatch="final-2026", HomeTeamScore=2, AwayTeamScore=1)]})
    teams = {"Argentina": "阿根廷", "France": "法国"}
    matches = parse_matches(payload, teams, source_update_utc="2026-07-20T05:30:00Z")

    assert len(matches) == 1
    m = matches[0]
    assert m.match_id == "final-2026"
    assert m.home_team_en == "Argentina"
    assert m.away_team_en == "France"
    assert m.home_team_zh == "阿根廷"
    assert m.away_team_zh == "法国"
    assert m.start_time_utc == "2026-07-20T00:00:00Z"
    assert m.stage == "决赛"
    assert m.venue == "MetLife Stadium"
    assert m.status == "scheduled"
    assert m.home_score == 2
    assert m.away_score == 1


def test_parse_matches_from_fifa_results_payload_without_scores_is_scheduled():
    payload = json.dumps({"Results": [_fifa_item(IdMatch="m1")]})
    teams = {}
    matches = parse_matches(payload, teams, source_update_utc="2026-07-20T00:00:00Z")
    m = matches[0]
    assert m.status == "scheduled"
    assert m.home_score is None
    assert m.away_score is None


def test_parse_matches_from_fifa_results_payload_finished_from_scores_when_status_unknown():
    payload = json.dumps({"Results": [_fifa_item(IdMatch="m2", MatchStatus="X", HomeTeamScore=3, AwayTeamScore=2)]})
    teams = {}
    matches = parse_matches(payload, teams, source_update_utc="2026-07-20T00:00:00Z")
    m = matches[0]
    assert m.status == "finished"
    assert m.home_score == 3
    assert m.away_score == 2


def _fifa_knockout_item(
    *,
    IdMatch="400",
    PlaceHolderA="W73",
    PlaceHolderB="W75",
    Date="2026-07-15T00:00:00Z",
    StageName="Round of 16",
    StadiumName="MetLife Stadium",
    MatchStatus="1",
):
    stage = [{"Description": StageName}]
    stadium = {"Name": [{"Description": StadiumName}]}
    return {
        "IdMatch": IdMatch,
        "Home": None,
        "Away": None,
        "PlaceHolderA": PlaceHolderA,
        "PlaceHolderB": PlaceHolderB,
        "Date": Date,
        "StageName": stage,
        "Stadium": stadium,
        "MatchStatus": MatchStatus,
    }


def test_parse_matches_from_fifa_results_uses_placeholders_when_teams_null():
    payload = json.dumps({"Results": [_fifa_knockout_item()]})
    teams = {}
    matches = parse_matches(payload, teams, source_update_utc="2026-07-20T00:00:00Z")
    assert len(matches) == 1
    m = matches[0]
    assert m.home_team_en == "W73"
    assert m.away_team_en == "W75"
    assert m.home_team_zh == "W73"
    assert m.away_team_zh == "W75"
    assert m.status == "scheduled"


def test_parse_matches_from_fifa_results_falls_back_to_to_be_determined_without_placeholders():
    payload = json.dumps(
        {"Results": [_fifa_knockout_item(PlaceHolderA="", PlaceHolderB="")]}
    )
    teams = {"To Be Determined": "待定"}
    matches = parse_matches(payload, teams, source_update_utc="2026-07-20T00:00:00Z")
    assert len(matches) == 1
    m = matches[0]
    assert m.home_team_en == "To Be Determined"
    assert m.away_team_en == "To Be Determined"
    assert m.home_team_zh == "待定"
    assert m.away_team_zh == "待定"
