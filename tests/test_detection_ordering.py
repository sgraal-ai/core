"""Tests for scripts/analyze_detection_ordering.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDetectionOrdering:
    def test_module_imports(self):
        """Script must be importable."""
        from scripts.analyze_detection_ordering import (
            analyze_ordering,
            generate_synthetic_scenarios,
            DETECTION_LAYERS,
        )
        assert callable(analyze_ordering)
        assert callable(generate_synthetic_scenarios)
        assert len(DETECTION_LAYERS) == 4

    def test_basic_analysis(self):
        """analyze_ordering should return correct structure with synthetic data."""
        from scripts.analyze_detection_ordering import analyze_ordering

        scenarios = [
            {"id": "s1", "layers_fired": ["timestamp_integrity", "identity_drift"]},
            {"id": "s2", "layers_fired": ["identity_drift"]},
            {"id": "s3", "layers_fired": ["timestamp_integrity"]},
            {"id": "s4", "layers_fired": []},
        ]
        result = analyze_ordering(scenarios)

        assert result["total_scenarios"] == 4
        assert result["first_fire_counts"]["timestamp_integrity"] == 2
        assert result["first_fire_counts"]["identity_drift"] == 1
        assert "co_occurrence" in result
