from __future__ import annotations

import json
import re
from typing import Any

from scripts.models import Match

REQUIRED_FIELDS = ("id", "home", "away", "kickoff")

STAGE_ZH: dict[str, str] = {
    "First Stage": "小组赛",
    "Round of 32": "三十二强赛",
    "Round of 16": "八分之一决赛",
    "Quarter-final": "四分之一决赛",
    "Semi-final": "半决赛",
    "Play-off for third place": "三四名决赛",
    "Final": "决赛",
}

GROUP_ZH: dict[str, str] = {
    "Group A": "A组",
    "Group B": "B组",
    "Group C": "C组",
    "Group D": "D组",
    "Group E": "E组",
    "Group F": "F组",
    "Group G": "G组",
    "Group H": "H组",
    "Group I": "I组",
    "Group J": "J组",
    "Group K": "K组",
    "Group L": "L组",
}

COUNTRY_ZH: dict[str, str] = {
    "MEX": "墨西哥",
    "USA": "美国",
    "CAN": "加拿大",
}

CITY_ZH: dict[str, str] = {
    "Mexico City": "墨西哥城",
    "Guadalajara": "瓜达拉哈拉",
    "Monterrey": "蒙特雷",
    "Atlanta": "亚特兰大",
    "Boston": "波士顿",
    "Dallas": "达拉斯",
    "Houston": "休斯顿",
    "Kansas City": "堪萨斯城",
    "Los Angeles": "洛杉矶",
    "Miami": "迈阿密",
    "New Jersey": "新泽西",
    "Philadelphia": "费城",
    "San Francisco Bay Area": "旧金山湾区",
    "Seattle": "西雅图",
    "Toronto": "多伦多",
    "Vancouver": "温哥华",
}

STADIUM_ZH: dict[str, str] = {
    "Mexico City Stadium": "墨西哥城体育场（阿兹特克体育场）",
    "Guadalajara Stadium": "瓜达拉哈拉体育场（阿克伦体育场）",
    "Monterrey Stadium": "蒙特雷体育场（BBVA体育场）",
    "Atlanta Stadium": "亚特兰大体育场（梅赛德斯-奔驰体育场）",
    "Boston Stadium": "波士顿体育场（吉列体育场）",
    "Dallas Stadium": "达拉斯体育场（AT&T体育场）",
    "Houston Stadium": "休斯顿体育场（NRG体育场）",
    "Kansas City Stadium": "堪萨斯城体育场（箭头体育场）",
    "Los Angeles Stadium": "洛杉矶体育场（SoFi体育场）",
    "Miami Stadium": "迈阿密体育场（硬石体育场）",
    "New York/New Jersey Stadium": "纽约/新泽西体育场（大都会人寿体育场）",
    "Philadelphia Stadium": "费城体育场（林肯金融球场）",
    "San Francisco Bay Area Stadium": "旧金山湾区体育场（李维斯体育场）",
    "Seattle Stadium": "西雅图体育场（流明球场）",
    "Toronto Stadium": "多伦多体育场（BMO球场）",
    "BC Place Vancouver": "温哥华BC体育馆（BC Place）",
}


def translate(team: str, teams_zh: dict[str, str]) -> str:
    if team in teams_zh:
        return teams_zh[team]
    return _translate_placeholder(team)


_PLACEHOLDER_RE = re.compile(r"^(W|RU)(\d+)$")


def _translate_placeholder(name: str) -> str:
    m = _PLACEHOLDER_RE.match(name)
    if m:
        prefix = "胜者" if m.group(1) == "W" else "负者"
        return f"{prefix}{m.group(2)}"
    return name


def parse_json_payload(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("FIFA parser currently expects JSON or extracted JSON fixture data") from exc


def require_field(item: dict[str, Any], field: str, index: int) -> Any:
    value = item.get(field)
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ValueError(f"Missing required FIFA match field '{field}' at index {index}")
    return value


def text_description(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and "Description" in item:
                return str(item["Description"])
            return str(item) if item else ""
    if isinstance(value, dict) and "Description" in value:
        return str(value["Description"])
    return str(value)


def parse_fifa_status(value: Any, home_score: Any, away_score: Any) -> str:
    if value is not None:
        s = str(value).strip()
        if s == "0":
            return "finished"
        if s == "1":
            return "scheduled"
        if s in ("3", "12"):
            return "live"
        if s in ("7", "8"):
            return "finished"
        if s and home_score is not None and away_score is not None:
            return "finished"
        if s:
            return "scheduled"
    return "scheduled"


def team_name_from_result(item: dict[str, Any], side: str, placeholder_field: str) -> str:
    node = item.get(side)
    if isinstance(node, dict):
        name = text_description(node.get("TeamName"))
        if name:
            return name
    return item.get(placeholder_field) or "To Be Determined"


def _build_stage(item: dict[str, Any]) -> str:
    stage_en = text_description(item.get("StageName"))
    group_en = text_description(item.get("GroupName"))
    stage_zh = STAGE_ZH.get(stage_en, stage_en)
    if group_en and stage_en == "First Stage":
        group_zh = GROUP_ZH.get(group_en, group_en)
        return f"{stage_zh} {group_zh}"
    return stage_zh


def _build_venue(stadium: dict[str, Any]) -> str:
    country_id = str(stadium.get("IdCountry", ""))
    city_en = text_description(stadium.get("CityName"))
    name_en = text_description(stadium.get("Name"))
    country_zh = COUNTRY_ZH.get(country_id, country_id)
    city_zh = CITY_ZH.get(city_en, city_en)
    stadium_zh = STADIUM_ZH.get(name_en, name_en)
    parts = [p for p in [country_zh, city_zh, stadium_zh] if p]
    return " ".join(parts)


def _parse_results_matches(payload: dict[str, Any], teams_zh: dict[str, str], source_update_utc: str) -> list[Match]:
    results = payload.get("Results", [])
    matches: list[Match] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        home_en = team_name_from_result(item, "Home", "PlaceHolderA")
        away_en = team_name_from_result(item, "Away", "PlaceHolderB")
        home_score = item.get("HomeTeamScore")
        away_score = item.get("AwayTeamScore")
        matches.append(
            Match.from_dict(
                {
                    "match_id": str(item.get("IdMatch", "")),
                    "home_team_en": home_en,
                    "away_team_en": away_en,
                    "home_team_zh": translate(home_en, teams_zh),
                    "away_team_zh": translate(away_en, teams_zh),
                    "start_time_utc": str(item.get("Date", "")),
                    "stage": _build_stage(item),
                    "venue": _build_venue(item.get("Stadium", {})),
                    "status": parse_fifa_status(item.get("MatchStatus"), home_score, away_score),
                    "home_score": home_score,
                    "away_score": away_score,
                    "last_source_update": source_update_utc,
                    "source_url": "",
                }
            )
        )
    return matches


def parse_matches(content: str, teams_zh: dict[str, str], source_update_utc: str) -> list[Match]:
    payload = parse_json_payload(content)
    if "Results" in payload:
        return _parse_results_matches(payload, teams_zh, source_update_utc)
    if "matches" in payload:
        raw_matches = payload.get("matches", [])
        matches: list[Match] = []
        for idx, item in enumerate(raw_matches):
            home = str(require_field(item, "home", idx))
            away = str(require_field(item, "away", idx))
            score = item.get("score") or {}
            matches.append(
                Match.from_dict(
                    {
                        "match_id": require_field(item, "id", idx),
                        "home_team_en": home,
                        "away_team_en": away,
                        "home_team_zh": translate(home, teams_zh),
                        "away_team_zh": translate(away, teams_zh),
                        "start_time_utc": require_field(item, "kickoff", idx),
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
    return []
