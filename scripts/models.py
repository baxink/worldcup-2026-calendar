from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ALLOWED_STATUSES = {"scheduled", "live", "finished", "postponed", "cancelled"}
STATUS_ALIASES = {
    "not_started": "scheduled",
    "pre_match": "scheduled",
    "in_progress": "live",
    "playing": "live",
    "full_time": "finished",
    "ended": "finished",
}


def normalize_status(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    normalized = STATUS_ALIASES.get(normalized, normalized)
    if normalized not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported match status: {value}")
    return normalized


def parse_score(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"Invalid score: {value}")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"Invalid score: {value}")
        return int(value)
    num = float(str(value))
    if not num.is_integer():
        raise ValueError(f"Invalid score: {value}")
    return int(num)


@dataclass(frozen=True)
class Match:
    match_id: str
    home_team_en: str
    away_team_en: str
    home_team_zh: str
    away_team_zh: str
    start_time_utc: str
    stage: str
    venue: str
    status: str
    home_score: int | None
    away_score: int | None
    last_source_update: str
    source_url: str

    @property
    def title(self) -> str:
        return f"{self.home_team_zh} vs {self.away_team_zh}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Match":
        return cls(
            match_id=str(data["match_id"]),
            home_team_en=str(data.get("home_team_en", "")),
            away_team_en=str(data.get("away_team_en", "")),
            home_team_zh=str(data.get("home_team_zh") or data.get("home_team_en", "")),
            away_team_zh=str(data.get("away_team_zh") or data.get("away_team_en", "")),
            start_time_utc=str(data["start_time_utc"]),
            stage=str(data.get("stage", "")),
            venue=str(data.get("venue", "")),
            status=normalize_status(str(data.get("status", "scheduled"))),
            home_score=parse_score(data.get("home_score")),
            away_score=parse_score(data.get("away_score")),
            last_source_update=str(data.get("last_source_update", "")),
            source_url=str(data.get("source_url", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team_en": self.home_team_en,
            "away_team_en": self.away_team_en,
            "home_team_zh": self.home_team_zh,
            "away_team_zh": self.away_team_zh,
            "start_time_utc": self.start_time_utc,
            "stage": self.stage,
            "venue": self.venue,
            "status": self.status,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "last_source_update": self.last_source_update,
            "source_url": self.source_url,
        }
