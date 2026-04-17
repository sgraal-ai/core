"""Shared constants for the Sgraal scoring engine.

DecisionAction is the canonical enum for preflight decisions. It inherits
from str so existing string comparisons still work:

    DecisionAction.BLOCK == "BLOCK"  # True
    "BLOCK" == DecisionAction.BLOCK  # True

All new code should use the enum. Existing string literals will be migrated
incrementally — the str inheritance ensures backward compatibility.
"""
from enum import Enum


class DecisionAction(str, Enum):
    """The four possible preflight decision actions, ordered by severity."""
    USE_MEMORY = "USE_MEMORY"
    WARN = "WARN"
    ASK_USER = "ASK_USER"
    BLOCK = "BLOCK"
