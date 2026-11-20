"""Non-patient-specific screening workflow definition.

This module deliberately contains no persistence or patient data. It defines the
allowed lifecycle transitions that the consent-gated workflow service will use.
"""
from __future__ import annotations

STATES = (
    "requested",
    "sample_collected",
    "lab_received",
    "processing",
    "result_received",
    "clinical_review",
    "clinically_reviewed",
    "follow_up_required",
    "completed",
    "cancelled",
)

TRANSITIONS = {
    "requested": ("sample_collected", "cancelled"),
    "sample_collected": ("lab_received", "cancelled"),
    "lab_received": ("processing", "cancelled"),
    "processing": ("result_received", "cancelled"),
    "result_received": ("clinical_review",),
    "clinical_review": ("clinically_reviewed",),
    "clinically_reviewed": ("follow_up_required", "completed"),
    "follow_up_required": ("completed",),
    "completed": (),
    "cancelled": (),
}

TERMINAL_STATES = ("completed", "cancelled")


def is_valid_transition(from_state: str, to_state: str) -> bool:
    """Return whether a lifecycle transition is explicitly allowed."""
    return to_state in TRANSITIONS.get(from_state, ())


def workflow_definition() -> dict:
    """Return a JSON-safe workflow definition without any patient information."""
    return {
        "workflow": "genetic_screening",
        "version": "0.1.0",
        "initial_state": "requested",
        "states": list(STATES),
        "terminal_states": list(TERMINAL_STATES),
        "transitions": {
            state: list(next_states)
            for state, next_states in TRANSITIONS.items()
        },
        "release_rule": (
            "A result must not be released to an individual until an authorised "
            "clinician has completed clinical review."
        ),
        "creation_rule": (
            "A screening request must not be created until valid, purpose-specific "
            "consent has been recorded for the individual."
        ),
    }
