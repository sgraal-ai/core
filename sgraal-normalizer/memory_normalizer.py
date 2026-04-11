"""sgraal-normalizer: Cross-provider memory normalizer for Sgraal MemCube format."""


class MemoryNormalizer:
    """Normalizes memory entries from different providers to Sgraal MemCube format."""

    def from_mem0(self, memories: list) -> list:
        return [{"id": m.get("id", f"mem0_{i:03d}"), "content": m.get("memory", str(m))[:500],
                 "type": "semantic", "timestamp_age_days": 0, "source_trust": m.get("score", 0.8),
                 "source_conflict": 0.05, "downstream_count": 1}
                for i, m in enumerate(memories, 1)]

    def from_llamaindex(self, nodes: list) -> list:
        result = []
        for i, node in enumerate(nodes, 1):
            if hasattr(node, 'node'):
                content = getattr(node.node, 'text', str(node))
                score = getattr(node, 'score', 0.8) or 0.8
            elif hasattr(node, 'text'):
                content, score = node.text, 0.8
            else:
                content, score = str(node), 0.8
            result.append({"id": f"llamaindex_{i:03d}", "content": content[:500], "type": "semantic",
                           "timestamp_age_days": 0, "source_trust": min(float(score), 1.0),
                           "source_conflict": 0.05, "downstream_count": 1})
        return result

    def from_langchain(self, documents: list) -> list:
        result = []
        for i, doc in enumerate(documents, 1):
            if hasattr(doc, 'page_content'):
                content = doc.page_content
            elif isinstance(doc, dict):
                content = doc.get('page_content', str(doc))
            else:
                content = str(doc)
            result.append({"id": f"langchain_{i:03d}", "content": content[:500], "type": "semantic",
                           "timestamp_age_days": 0, "source_trust": 0.82, "source_conflict": 0.06, "downstream_count": 1})
        return result

    def from_strings(self, strings: list, source_trust: float = 0.8) -> list:
        return [{"id": f"raw_{i:03d}", "content": s[:500], "type": "semantic", "timestamp_age_days": 0,
                 "source_trust": source_trust, "source_conflict": 0.1, "downstream_count": 1}
                for i, s in enumerate(strings, 1)]

    def normalize(self, data, provider: str = "auto", source_trust: float = 0.8) -> list:
        if provider == "mem0" or (provider == "auto" and isinstance(data, list) and data and isinstance(data[0], dict) and "memory" in data[0]):
            return self.from_mem0(data)
        elif provider == "llamaindex" or (provider == "auto" and isinstance(data, list) and data and hasattr(data[0], 'get_content')):
            return self.from_llamaindex(data)
        elif provider == "langchain" or (provider == "auto" and isinstance(data, list) and data and hasattr(data[0], 'page_content')):
            return self.from_langchain(data)
        elif isinstance(data, list) and all(isinstance(x, str) for x in data):
            return self.from_strings(data, source_trust)
        return self.from_strings([str(x) for x in data], source_trust)
