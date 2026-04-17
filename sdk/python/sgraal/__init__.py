# Lazy imports: the heavy modules (client, guard, integrations) depend on
# `requests` and other external packages. Importing them eagerly would make
# `from sgraal.edge import edge_preflight` load requests — defeating the
# zero-dependency promise of edge mode.
#
# Instead, we import lazily via __getattr__ so that:
#   from sgraal import SgraalClient       → works (loads client on first access)
#   from sgraal.edge import edge_preflight → works WITHOUT loading requests
#
from .tracker import StepTracker  # stdlib-only, safe to import eagerly

__all__ = [
    "SgraalClient",
    "PreflightResult",
    "guard",
    "StepTracker",
    "GeminiGuard",
    "OpenAIGuard",
    "edge_preflight",
]


def __getattr__(name):
    if name in ("SgraalClient", "PreflightResult"):
        from .client import SgraalClient, PreflightResult
        return SgraalClient if name == "SgraalClient" else PreflightResult
    if name == "guard":
        from .guard import guard
        return guard
    if name in ("GeminiGuard", "OpenAIGuard"):
        from .integrations import GeminiGuard, OpenAIGuard
        return GeminiGuard if name == "GeminiGuard" else OpenAIGuard
    if name == "edge_preflight":
        from .edge import edge_preflight
        return edge_preflight
    raise AttributeError(f"module 'sgraal' has no attribute {name!r}")
