"""Universal Memory Adapter — YAML/JSON config, intercept queries, preflight filter."""
from __future__ import annotations
from typing import Optional

class UniversalMemoryAdapter:
    def __init__(self, config: dict, api_key: str = "", api_url: str = "https://api.sgraal.com"):
        self.config = config
        self.api_key = api_key or config.get("api_key", "")
        self.api_url = api_url
        self.max_omega = config.get("max_omega", 80)

    def query(self, query_text: str, **kwargs) -> list:
        backend = self.config.get("backend", {})
        results = backend.get("mock_results", [])
        return [r for r in results if r.get("omega_score", 0) <= self.max_omega]

    @classmethod
    def from_yaml(cls, path: str, api_key: str = "") -> "UniversalMemoryAdapter":
        import json
        with open(path) as f:
            if path.endswith(".yaml") or path.endswith(".yml"):
                try:
                    import yaml; config = yaml.safe_load(f)
                except ImportError:
                    config = json.load(f)
            else:
                config = json.load(f)
        return cls(config, api_key)
