"""Agent adapter implementations."""

from context_eval.adapters.base import (
    AgentAdapter,
    NoOpTelemetryCollector,
    TelemetryCollectionPreparation,
    TelemetryCollectionResult,
    TelemetryCollector,
)
from context_eval.adapters.command import CommandTemplateAgent, render_command_template

__all__ = [
    "AgentAdapter",
    "CommandTemplateAgent",
    "NoOpTelemetryCollector",
    "TelemetryCollectionPreparation",
    "TelemetryCollectionResult",
    "TelemetryCollector",
    "render_command_template",
]
