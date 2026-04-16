"""Example: a plugin that adjusts s_freshness scores.

This plugin applies a 10% discount to s_freshness scores — simulating a
customer who believes memory decays slower in their domain and wants a less
aggressive freshness penalty. It demonstrates:

- Overriding `on_component_score` to selectively modify one component
- Pass-through for other components (return unchanged)
- Plugin metadata via `name` and `version`

Activate via POST /v1/plugins/activate {"name": "custom_freshness"} after
the plugin is loaded at startup.
"""
from __future__ import annotations

from plugins.base import SgraalPlugin


class CustomFreshnessPlugin(SgraalPlugin):
    name = "custom_freshness"
    version = "1.0.0"

    DISCOUNT = 0.90  # reduce s_freshness by 10%

    def on_component_score(self, component_name: str, score: float, memory_state: list) -> float:
        if component_name == "s_freshness":
            return score * self.DISCOUNT
        return score
