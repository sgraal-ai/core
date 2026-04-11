# sgraal-normalizer

Cross-provider memory normalizer for Sgraal. Converts Mem0, LlamaIndex, LangChain, and raw strings to MemCube format.

## Install
```bash
pip install sgraal-normalizer
```

## Usage
```python
from memory_normalizer import MemoryNormalizer

norm = MemoryNormalizer()

# Auto-detect provider:
memcube_entries = norm.normalize(my_data)  # works with any provider

# Explicit provider:
entries = norm.from_langchain(retriever.get_relevant_documents("query"))
entries = norm.from_llamaindex(index.as_retriever().retrieve("query"))
entries = norm.from_mem0(mem0_client.search("query"))
entries = norm.from_strings(["fact 1", "fact 2"])
```
