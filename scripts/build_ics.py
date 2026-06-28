from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.models import Match


BEIJING = timezone(timedelta(hours=8))
STATUS_LABELS = {
    "scheduled": "未开始",
    "live": "进行中",
    "finished": "已结束",
    "postponed": "延期",
    "cancelled": "取消",
}


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_ics_datetime(value: str) -> str:
    return parse_utc(value).strftime("%Y%m%dT%H%M%SZ")


def format_beijing(value: str) -> str:
    return parse_utc(value).astimezone(BEIJING).strftime("%Y-%m-%d %H:%M")


def escape_ics(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def score_text(match: Match) -> str:
    if match.home_score is None or match.away_score is None:
        return "未定"
    return f"{match.home_score}-{match.away_score}"


def build_description(match: Match) -> str:
    lines = [
        f"状态：{STATUS_LABELS[match.status]}",
        f"比分：{score_text(match)}",
        f"阶段：{match.stage}",
        f"场地：{match.venue}",
        f"北京时间：{format_beijing(match.start_time_utc)}",
        f"最近更新时间：{format_beijing(match.last_source_update)}" if match.last_source_update else "最近更新时间：未知",
        f"数据来源：{match.source_url}",
    ]
    return "\\n".join(escape_ics(line) for line in lines)


def build_event(match: Match, generated_at_utc: str) -> str:
    start = parse_utc(match.start_time_utc)
    end = start + timedelta(hours=2)
    return "\n".join(
        [
            "BEGIN:VEVENT",
            f"UID:{escape_ics(match.match_id)}@worldcup-2026-calendar",
            f"DTSTAMP:{format_ics_datetime(generated_at_utc)}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{escape_ics(match.title)}",
            f"DESCRIPTION:{build_description(match)}",
            f"LOCATION:{escape_ics(match.venue)}",
            "END:VEVENT",
        ]
    )


def build_calendar(matches: list[Match], generated_at_utc: str) -> str:
    events = [build_event(match, generated_at_utc) for match in sorted(matches, key=lambda item: item.start_time_utc)]
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//worldcup-2026-calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:2026 世界杯赛程",
        *events,
        "END:VCALENDAR",
    ]
    return "\n".join(lines) + "\n"
