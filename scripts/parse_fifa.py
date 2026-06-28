from __future__ import annotations

import json
from typing import Any

from scripts.models import Match

REQUIRED_FIELDS = ("id", "home", "away", "kickoff")


def translate(team: str, teams_zh: dict[str, str]) -> str:
    return teams_zh.get(team, team)


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
        if s in ("0", "1"):
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
                    "stage": text_description(item.get("StageName")),
                    "venue": text_description(item.get("Stadium", {}).get("Name")),
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
