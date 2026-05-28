from __future__ import annotations

import glob
import json
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)

CALL_PAYLOAD_TYPES = {
    "function_call",
    "custom_tool_call",
    "mcp_tool_call",
    "collab_tool_call",
    "web_search_call",
}

OUTPUT_PAYLOAD_TYPES = {
    "function_call_output",
    "custom_tool_call_output",
    "mcp_tool_call_output",
    "collab_tool_call_output",
    "web_search_end",
    "patch_apply_end",
}

SUCCESS_STATUSES = {"ok", "success", "succeeded", "completed", "complete"}


@dataclass
class SessionFileSummary:
    path: str
    byte_size: int
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    event_count: int = 0
    turn_count: int = 0
    malformed_line_count: int = 0
    token_observation_count: int = 0
    rate_limit_observation_count: int = 0
    latest_token_usage: dict[str, int] | None = None
    max_token_usage: dict[str, int] | None = None
    row_type_counts: dict[str, int] = field(default_factory=dict)
    payload_type_counts: dict[str, int] = field(default_factory=dict)
    call_counts_by_type: dict[str, int] = field(default_factory=dict)
    call_counts_by_name: dict[str, int] = field(default_factory=dict)
    output_status_counts: dict[str, int] = field(default_factory=dict)
    diagnostic_signal_counts: dict[str, int] = field(default_factory=dict)

    @property
    def diagnostic_signal_count(self) -> int:
        return sum(self.diagnostic_signal_counts.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "byte_size": self.byte_size,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "event_count": self.event_count,
            "turn_count": self.turn_count,
            "malformed_line_count": self.malformed_line_count,
            "token_observation_count": self.token_observation_count,
            "rate_limit_observation_count": self.rate_limit_observation_count,
            "latest_token_usage": self.latest_token_usage,
            "max_token_usage": self.max_token_usage,
            "row_type_counts": _sorted_mapping(self.row_type_counts),
            "payload_type_counts": _sorted_mapping(self.payload_type_counts),
            "call_counts_by_type": _sorted_mapping(self.call_counts_by_type),
            "call_counts_by_name": _sorted_mapping(self.call_counts_by_name),
            "output_status_counts": _sorted_mapping(self.output_status_counts),
            "diagnostic_signal_counts": _sorted_mapping(self.diagnostic_signal_counts),
            "diagnostic_signal_count": self.diagnostic_signal_count,
        }


@dataclass
class CodexSessionSummary:
    sessions: list[SessionFileSummary]
    row_type_counts: dict[str, int]
    payload_type_counts: dict[str, int]
    call_counts_by_type: dict[str, int]
    call_counts_by_name: dict[str, int]
    output_status_counts: dict[str, int]
    diagnostic_signal_counts: dict[str, int]
    latest_token_usage: dict[str, int] | None
    max_token_usage: dict[str, int] | None

    @property
    def total_files(self) -> int:
        return len(self.sessions)

    @property
    def total_bytes(self) -> int:
        return sum(session.byte_size for session in self.sessions)

    @property
    def total_events(self) -> int:
        return sum(session.event_count for session in self.sessions)

    @property
    def total_turns(self) -> int:
        return sum(session.turn_count for session in self.sessions)

    @property
    def malformed_line_count(self) -> int:
        return sum(session.malformed_line_count for session in self.sessions)

    @property
    def token_observation_count(self) -> int:
        return sum(session.token_observation_count for session in self.sessions)

    @property
    def rate_limit_observation_count(self) -> int:
        return sum(session.rate_limit_observation_count for session in self.sessions)

    @property
    def diagnostic_signal_count(self) -> int:
        return sum(session.diagnostic_signal_count for session in self.sessions)

    @property
    def top_sessions_by_size(self) -> list[dict[str, Any]]:
        return [
            {
                "path": session.path,
                "byte_size": session.byte_size,
                "diagnostic_signal_count": session.diagnostic_signal_count,
            }
            for session in sorted(
                self.sessions,
                key=lambda item: (-item.byte_size, _path_sort_key(item.path)),
            )[:5]
        ]

    @property
    def top_sessions_by_diagnostic_signal(self) -> list[dict[str, Any]]:
        ranked = sorted(
            self.sessions,
            key=lambda item: (-item.diagnostic_signal_count, _path_sort_key(item.path)),
        )
        return [
            {
                "path": session.path,
                "diagnostic_signal_count": session.diagnostic_signal_count,
                "malformed_line_count": session.malformed_line_count,
                "byte_size": session.byte_size,
            }
            for session in ranked[:5]
            if session.diagnostic_signal_count > 0
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "summary_type": "codex-session-diagnostics",
            "total_files": self.total_files,
            "total_bytes": self.total_bytes,
            "total_events": self.total_events,
            "total_turns": self.total_turns,
            "malformed_line_count": self.malformed_line_count,
            "token_observation_count": self.token_observation_count,
            "rate_limit_observation_count": self.rate_limit_observation_count,
            "diagnostic_signal_count": self.diagnostic_signal_count,
            "latest_token_usage": self.latest_token_usage,
            "max_token_usage": self.max_token_usage,
            "row_type_counts": _sorted_mapping(self.row_type_counts),
            "payload_type_counts": _sorted_mapping(self.payload_type_counts),
            "call_counts_by_type": _sorted_mapping(self.call_counts_by_type),
            "call_counts_by_name": _sorted_mapping(self.call_counts_by_name),
            "output_status_counts": _sorted_mapping(self.output_status_counts),
            "diagnostic_signal_counts": _sorted_mapping(self.diagnostic_signal_counts),
            "top_sessions_by_size": self.top_sessions_by_size,
            "top_sessions_by_diagnostic_signal": self.top_sessions_by_diagnostic_signal,
            "sessions": [session.to_dict() for session in self.sessions],
        }


def summarize_codex_sessions(paths: Sequence[str | Path]) -> CodexSessionSummary:
    session_paths = resolve_codex_session_paths(paths)
    sessions = [parse_codex_session_file(path) for path in session_paths]

    row_type_counts: Counter[str] = Counter()
    payload_type_counts: Counter[str] = Counter()
    call_counts_by_type: Counter[str] = Counter()
    call_counts_by_name: Counter[str] = Counter()
    output_status_counts: Counter[str] = Counter()
    diagnostic_signal_counts: Counter[str] = Counter()
    latest_token_usage: dict[str, int] | None = None
    latest_token_timestamp: str | None = None
    max_token_usage: dict[str, int] | None = None

    for session in sessions:
        row_type_counts.update(session.row_type_counts)
        payload_type_counts.update(session.payload_type_counts)
        call_counts_by_type.update(session.call_counts_by_type)
        call_counts_by_name.update(session.call_counts_by_name)
        output_status_counts.update(session.output_status_counts)
        diagnostic_signal_counts.update(session.diagnostic_signal_counts)
        if session.latest_token_usage is not None:
            if latest_token_timestamp is None or (
                session.last_timestamp is not None
                and session.last_timestamp >= latest_token_timestamp
            ):
                latest_token_usage = dict(session.latest_token_usage)
                latest_token_timestamp = session.last_timestamp
        max_token_usage = _merge_max_token_usage(max_token_usage, session.max_token_usage)

    return CodexSessionSummary(
        sessions=sessions,
        row_type_counts=_sorted_mapping(row_type_counts),
        payload_type_counts=_sorted_mapping(payload_type_counts),
        call_counts_by_type=_sorted_mapping(call_counts_by_type),
        call_counts_by_name=_sorted_mapping(call_counts_by_name),
        output_status_counts=_sorted_mapping(output_status_counts),
        diagnostic_signal_counts=_sorted_mapping(diagnostic_signal_counts),
        latest_token_usage=latest_token_usage,
        max_token_usage=max_token_usage,
    )


def resolve_codex_session_paths(paths: Sequence[str | Path]) -> list[Path]:
    matched: dict[str, Path] = {}
    for raw_path in paths:
        raw_text = str(raw_path)
        candidates: Iterable[str]
        if glob.has_magic(raw_text):
            candidates = glob.glob(raw_text)
        else:
            candidates = [raw_text]
        for candidate in candidates:
            path = Path(candidate)
            if not path.is_file():
                continue
            resolved = path.resolve()
            matched[str(resolved)] = resolved
    if not matched:
        raise ValueError("no Codex session files matched the supplied path(s)")
    return [matched[key] for key in sorted(matched, key=_path_sort_key)]


def parse_codex_session_file(path: Path) -> SessionFileSummary:
    summary = SessionFileSummary(path=str(path.resolve()), byte_size=path.stat().st_size)
    row_type_counts: Counter[str] = Counter()
    payload_type_counts: Counter[str] = Counter()
    call_counts_by_type: Counter[str] = Counter()
    call_counts_by_name: Counter[str] = Counter()
    output_status_counts: Counter[str] = Counter()
    diagnostic_signal_counts: Counter[str] = Counter()

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                summary.malformed_line_count += 1
                diagnostic_signal_counts["malformed_line"] += 1
                continue
            if not isinstance(event, dict):
                summary.malformed_line_count += 1
                diagnostic_signal_counts["malformed_line"] += 1
                continue

            summary.event_count += 1
            timestamp = event.get("timestamp")
            if isinstance(timestamp, str) and timestamp:
                summary.first_timestamp = summary.first_timestamp or timestamp
                summary.last_timestamp = timestamp
            row_type = _safe_name(event.get("type"), "unknown")
            row_type_counts[row_type] += 1
            if row_type == "turn_context":
                summary.turn_count += 1

            payload = event.get("payload")
            if isinstance(payload, dict) and isinstance(payload.get("type"), str):
                _consume_payload(
                    payload,
                    payload_type_counts=payload_type_counts,
                    call_counts_by_type=call_counts_by_type,
                    call_counts_by_name=call_counts_by_name,
                    output_status_counts=output_status_counts,
                    diagnostic_signal_counts=diagnostic_signal_counts,
                    summary=summary,
                )

    summary.row_type_counts = _sorted_mapping(row_type_counts)
    summary.payload_type_counts = _sorted_mapping(payload_type_counts)
    summary.call_counts_by_type = _sorted_mapping(call_counts_by_type)
    summary.call_counts_by_name = _sorted_mapping(call_counts_by_name)
    summary.output_status_counts = _sorted_mapping(output_status_counts)
    summary.diagnostic_signal_counts = _sorted_mapping(diagnostic_signal_counts)
    return summary


def _consume_payload(
    payload: dict[str, Any],
    *,
    payload_type_counts: Counter[str],
    call_counts_by_type: Counter[str],
    call_counts_by_name: Counter[str],
    output_status_counts: Counter[str],
    diagnostic_signal_counts: Counter[str],
    summary: SessionFileSummary,
) -> None:
    payload_type = _safe_name(payload.get("type"), "unknown")
    payload_type_counts[payload_type] += 1

    if payload_type == "token_count":
        summary.token_observation_count += 1
        usage = _token_usage_from_payload(payload)
        if usage is not None:
            summary.latest_token_usage = usage
            summary.max_token_usage = _merge_max_token_usage(summary.max_token_usage, usage)
        if payload.get("rate_limits") is not None:
            summary.rate_limit_observation_count += 1
        rate_limits = payload.get("rate_limits")
        if isinstance(rate_limits, dict) and rate_limits.get("rate_limit_reached_type"):
            diagnostic_signal_counts["rate_limit_reached"] += 1

    if payload_type in CALL_PAYLOAD_TYPES:
        call_counts_by_type[payload_type] += 1
        call_name = _call_name(payload, payload_type)
        if call_name:
            call_counts_by_name[call_name] += 1

    if payload_type in OUTPUT_PAYLOAD_TYPES:
        status = _status_name(payload.get("status"))
        output_status_counts[status] += 1

    status = payload.get("status")
    if _is_non_success_status(status):
        diagnostic_signal_counts["non_success_status"] += 1
    if payload_type == "thread_rolled_back":
        diagnostic_signal_counts["thread_rolled_back"] += 1
    if "error" in payload_type or "failed" in payload_type:
        diagnostic_signal_counts["error"] += 1


def _token_usage_from_payload(payload: dict[str, Any]) -> dict[str, int] | None:
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    usage = info.get("total_token_usage")
    if not isinstance(usage, dict):
        return None
    normalized: dict[str, int] = {}
    for token_field in TOKEN_FIELDS:
        value = usage.get(token_field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        normalized[token_field] = value
    return normalized


def _merge_max_token_usage(
    current: dict[str, int] | None,
    incoming: dict[str, int] | None,
) -> dict[str, int] | None:
    if incoming is None:
        return current
    if current is None:
        return dict(incoming)
    return {field: max(current.get(field, 0), incoming[field]) for field in TOKEN_FIELDS}


def _call_name(payload: dict[str, Any], payload_type: str) -> str | None:
    for key in ("name", "tool"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if payload_type == "web_search_call":
        return "web_search"
    return None


def _status_name(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _is_non_success_status(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return value.strip().lower() not in SUCCESS_STATUSES


def _safe_name(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _sorted_mapping(mapping: dict[str, int] | Counter[str]) -> dict[str, int]:
    return {key: int(mapping[key]) for key in sorted(mapping)}


def _path_sort_key(path: str | Path) -> str:
    return str(path).casefold()
