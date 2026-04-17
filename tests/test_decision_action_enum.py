"""Tests for #4: DecisionAction enum prevents string-literal typos.

DecisionAction(str, Enum) is the canonical type for preflight decisions.
It inherits from str so existing comparisons work unchanged, but typos
like "Block" or "BLCK" raise ValueError at call time instead of silently
producing invalid responses.
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from scoring_engine.constants import DecisionAction


class TestDecisionActionEnum:
    def test_enum_equals_string(self):
        """DecisionAction values must compare equal to their string literals.
        This is the backward-compatibility guarantee that lets existing code
        continue to work after the enum is introduced."""
        assert DecisionAction.BLOCK == "BLOCK"
        assert DecisionAction.WARN == "WARN"
        assert DecisionAction.ASK_USER == "ASK_USER"
        assert DecisionAction.USE_MEMORY == "USE_MEMORY"

        # Reverse comparison
        assert "BLOCK" == DecisionAction.BLOCK
        assert "USE_MEMORY" == DecisionAction.USE_MEMORY

        # In-set membership
        assert DecisionAction.BLOCK in ("BLOCK", "WARN")
        assert "BLOCK" in (DecisionAction.BLOCK, DecisionAction.WARN)

    def test_typo_raises_value_error(self):
        """A typo like 'Block', 'block', or 'BLCK' must raise ValueError
        when passed to DecisionAction(). This is the safety guarantee that
        prevents silent invalid decisions."""
        with pytest.raises(ValueError):
            DecisionAction("Block")   # wrong case

        with pytest.raises(ValueError):
            DecisionAction("block")   # all lowercase

        with pytest.raises(ValueError):
            DecisionAction("BLCK")    # misspelling

        with pytest.raises(ValueError):
            DecisionAction("USE MEMORY")  # space instead of underscore

        with pytest.raises(ValueError):
            DecisionAction("")  # empty string
