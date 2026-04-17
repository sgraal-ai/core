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


# Thermodynamic constants
LANDAUER_CONSTANT_JOULES_PER_BIT = 2.87e-21  # kT·ln(2) at T=300K
LANDAUER_TEMPERATURE_KELVIN = 300
LANDAUER_BITS_PER_ENTRY = 2304  # 256-bit id hash + 2048-bit content proxy

# Phase constant
KAPPA_MEM_PHASE_CONSTANT = 0.033

# Default decision thresholds
DEFAULT_WARN_THRESHOLD = 25
DEFAULT_ASK_USER_THRESHOLD = 45
DEFAULT_BLOCK_THRESHOLD = 70
