import json

import pytest

from scripts.parse_fifa import STADIUM_ZH, parse_matches


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
    GroupName=None,
    IdCountry=None,
    CityName=None,
    StadiumName="MetLife Stadium",
    MatchStatus="0",
    HomeTeamScore=None,
    AwayTeamScore=None,
):
    home = {"TeamName": [{"Description": HomeTeamName}]}
    away = {"TeamName": [{"Description": AwayTeamName}]}
    stage = [{"Description": StageName}]
    stadium = {"Name": [{"Description": StadiumName}]}
    if IdCountry is not None:
        stadium["IdCountry"] = IdCountry
    if CityName is not None:
        stadium["CityName"] = [{"Description": CityName}]
    item = {
        "IdMatch": IdMatch,
        "Home": home,
        "Away": away,
        "Date": Date,
        "StageName": stage,
        "Stadium": stadium,
        "MatchStatus": MatchStatus,
    }
    if GroupName is not None:
        item["GroupName"] = [{"Description": GroupName}]
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
    assert m.status == "finished"
    assert m.home_score == 2
    assert m.away_score == 1


def test_parse_matches_from_fifa_results_payload_without_scores_is_scheduled():
    payload = json.dumps({"Results": [_fifa_item(IdMatch="m1", MatchStatus="1")]})
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
    assert m.home_team_zh == "胜者73"
    assert m.away_team_zh == "胜者75"
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


def test_parse_matches_from_fifa_results_localizes_team_stage_venue_and_finished_status():
    item = _fifa_item(
        IdMatch="400021443",
        HomeTeamName="Mexico",
        AwayTeamName="South Africa",
        Date="2026-06-11T19:00:00Z",
        StageName="First Stage",
        GroupName="Group A",
        IdCountry="MEX",
        CityName="Mexico City",
        StadiumName="Mexico City Stadium",
        MatchStatus="0",
        HomeTeamScore=2,
        AwayTeamScore=0,
    )
    payload = json.dumps({"Results": [item]})
    teams = {"Mexico": "墨西哥", "South Africa": "南非"}
    matches = parse_matches(payload, teams, source_update_utc="2026-06-28T10:00:00Z")

    assert len(matches) == 1
    m = matches[0]
    assert m.match_id == "400021443"
    assert m.home_team_zh == "墨西哥"
    assert m.away_team_zh == "南非"
    assert m.stage == "小组赛 A组"
    assert m.venue == "墨西哥 墨西哥城 墨西哥城体育场（阿兹特克体育场）"
    assert m.status == "finished"
    assert m.home_score == 2
    assert m.away_score == 0


def test_parse_matches_from_fifa_results_localizes_knockout_stage_and_venue():
    item = _fifa_item(
        IdMatch="400100101",
        HomeTeamName="W73",
        AwayTeamName="W74",
        Date="2026-07-10T01:00:00Z",
        StageName="Quarter-final",
        IdCountry="USA",
        CityName="Kansas City",
        StadiumName="Kansas City Stadium",
        MatchStatus="1",
    )
    payload = json.dumps({"Results": [item]})
    teams = {}
    matches = parse_matches(payload, teams, source_update_utc="2026-06-28T10:00:00Z")

    assert len(matches) == 1
    m = matches[0]
    assert m.stage == "四分之一决赛"
    assert m.venue == "美国 堪萨斯城 堪萨斯城体育场（箭头体育场）"
    assert m.status == "scheduled"
    assert m.home_score is None
    assert m.away_score is None


def test_parse_matches_from_fifa_results_uses_chinese_placeholder_labels():
    item = _fifa_knockout_item(
        IdMatch="400999001",
        PlaceHolderA="W73",
        PlaceHolderB="RU101",
        Date="2026-07-15T01:00:00Z",
        StageName="Round of 16",
        StadiumName="MetLife Stadium",
        MatchStatus="1",
    )
    payload = json.dumps({"Results": [item]})
    teams = {}
    matches = parse_matches(payload, teams, source_update_utc="2026-06-28T10:00:00Z")

    assert len(matches) == 1
    m = matches[0]
    assert m.home_team_en == "W73"
    assert m.away_team_en == "RU101"
    assert m.home_team_zh == "胜者73"
    assert m.away_team_zh == "负者101"
    assert m.status == "scheduled"


def test_parse_matches_from_fifa_results_venue_includes_real_stadium_aliases():
    item_mexico = _fifa_item(
        IdMatch="m1",
        HomeTeamName="Mexico",
        AwayTeamName="Canada",
        IdCountry="MEX",
        CityName="Mexico City",
        StadiumName="Mexico City Stadium",
        MatchStatus="1",
    )
    payload = json.dumps({"Results": [item_mexico]})
    teams = {"Mexico": "墨西哥", "Canada": "加拿大"}
    matches = parse_matches(payload, teams, source_update_utc="2026-06-28T10:00:00Z")
    assert matches[0].venue == "墨西哥 墨西哥城 墨西哥城体育场（阿兹特克体育场）"

    item_boston = _fifa_item(
        IdMatch="m2",
        HomeTeamName="USA",
        AwayTeamName="Mexico",
        IdCountry="USA",
        CityName="Boston",
        StadiumName="Boston Stadium",
        MatchStatus="1",
    )
    payload = json.dumps({"Results": [item_boston]})
    teams = {"USA": "美国", "Mexico": "墨西哥"}
    matches = parse_matches(payload, teams, source_update_utc="2026-06-28T10:00:00Z")
    assert matches[0].venue == "美国 波士顿 波士顿体育场（吉列体育场）"


def test_all_known_stadium_mappings_include_alias_parentheses():
    expected = {
        "Atlanta Stadium": "亚特兰大体育场（梅赛德斯-奔驰体育场）",
        "BC Place Vancouver": "温哥华BC体育馆（BC Place）",
        "Boston Stadium": "波士顿体育场（吉列体育场）",
        "Dallas Stadium": "达拉斯体育场（AT&T体育场）",
        "Guadalajara Stadium": "瓜达拉哈拉体育场（阿克伦体育场）",
        "Houston Stadium": "休斯顿体育场（NRG体育场）",
        "Kansas City Stadium": "堪萨斯城体育场（箭头体育场）",
        "Los Angeles Stadium": "洛杉矶体育场（SoFi体育场）",
        "Mexico City Stadium": "墨西哥城体育场（阿兹特克体育场）",
        "Miami Stadium": "迈阿密体育场（硬石体育场）",
        "Monterrey Stadium": "蒙特雷体育场（BBVA体育场）",
        "New York/New Jersey Stadium": "纽约/新泽西体育场（大都会人寿体育场）",
        "Philadelphia Stadium": "费城体育场（林肯金融球场）",
        "San Francisco Bay Area Stadium": "旧金山湾区体育场（李维斯体育场）",
        "Seattle Stadium": "西雅图体育场（流明球场）",
        "Toronto Stadium": "多伦多体育场（BMO球场）",
    }
    for en_name, zh_expected in expected.items():
        assert STADIUM_ZH.get(en_name) == zh_expected, f"Mismatch for {en_name}"
