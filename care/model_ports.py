"""Boundary for separately trained models. Neither implementation is shipped here.

An adapter can classify a participant's note and generate a conversational response
after evaluation. Keep the rule alerts and human review independent of that adapter.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    label: str
    confidence: float


def classify_note(text: str) -> Classification | None:
    return None


def generate_response(text: str, context: dict) -> str | None:
    return None
