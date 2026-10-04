"""Configurable behavioral risk engine.

PRINCIPLE:
Never classify people as criminals or make inferences about intent.
Calculate an explainable behavioral risk score based strictly on observable events.

Example rules:
- restricted_zone_entry: +30
- possible_aggressive_activity: +30
- possible_abandoned_object: +20
- loitering: +20
- running_in_restricted_zone: +20
- fall_detected: emergency health event (HIGH severity, flagged as safety rather than threat)

Score levels:
 0–29: LOW
 30–59: MEDIUM
 60–79: HIGH
 80–100: CRITICAL
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings
from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class RiskEvaluation:
    score: int
    level: str  # LOW | MEDIUM | HIGH | CRITICAL
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "reasons": self.reasons,
        }


DEFAULT_RULES: dict[str, int] = {
    "restricted_zone_entry": 30,
    "possible_aggressive_activity": 30,
    "possible_abandoned_object": 20,
    "loitering": 20,
    "running_in_restricted_zone": 20,
    "fall_detected": 40,
    "high_crowd_density": 15,
    "critical_crowd_density": 35,
}


class RiskEngine:
    """Calculates explainable behavioral risk scores."""

    def __init__(self, rules_file: Path | None = None) -> None:
        settings = get_settings()
        self.rules_file = rules_file or settings.risk_rules_path
        self.rules: dict[str, int] = dict(DEFAULT_RULES)
        self._load_rules()

    def _load_rules(self) -> None:
        if self.rules_file.exists():
            try:
                with open(self.rules_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict) and "rules" in data:
                        self.rules.update(data["rules"])
                        log.info("Loaded custom risk rules from %s", self.rules_file)
            except Exception as e:
                log.warning("Failed to parse risk rules from %s (%s); using defaults", self.rules_file, e)

    def calculate(self, observed_events: list[str]) -> RiskEvaluation:
        """Calculate composite risk score and generate breakdown explanations."""
        score = 0
        reasons: list[str] = []

        # Deduplicate events for one frame evaluation
        unique_events = list(dict.fromkeys(observed_events))

        for event in unique_events:
            weight = self.rules.get(event, 10)
            score += weight
            reasons.append(f"{event.replace('_', ' ').capitalize()}: +{weight}")

        score = min(100, max(0, score))

        if score >= 80:
            level = "CRITICAL"
        elif score >= 60:
            level = "HIGH"
        elif score >= 30:
            level = "MEDIUM"
        else:
            level = "LOW"

        return RiskEvaluation(score=score, level=level, reasons=reasons)
