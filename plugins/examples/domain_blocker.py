"""Example: a plugin that always BLOCKs for a specific domain.

Demonstrates:
- Overriding `on_omega_computed` to change the decision
- Reading context to branch behavior
- Pass-through when the condition doesn't match

Use case: during a controlled rollout, force BLOCK for 'medical' domain so
no decision auto-proceeds without human review.
"""
from __future__ import annotations

from plugins.base import SgraalPlugin


class DomainBlockerPlugin(SgraalPlugin):
    name = "domain_blocker"
    version = "1.0.0"

    BLOCKED_DOMAINS: frozenset = frozenset(["medical"])

    def on_omega_computed(self, omega: float, decision: str, context: dict) -> tuple[float, str]:
        domain = context.get("domain", "general")
        if domain in self.BLOCKED_DOMAINS:
            # Force omega to max and decision to BLOCK
            return 100.0, "BLOCK"
        return omega, decision
