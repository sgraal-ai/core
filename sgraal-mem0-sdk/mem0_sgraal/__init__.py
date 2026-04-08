"""mem0-sgraal — Sgraal memory governance integration for mem0."""
from mem0_sgraal.client import Mem0SgraalClient
from mem0_sgraal.hooks import preflight_hook

__version__ = "0.1.0"
__all__ = ["Mem0SgraalClient", "preflight_hook"]
