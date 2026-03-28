# RAG Guard — Sgraal Memory Governance for RAG Pipelines

Score and filter retrieved chunks before they reach the LLM.

## Quickstart

### API Endpoint

```bash
curl -X POST https://api.sgraal.com/v1/rag/filter \
  -H "Authorization: Bearer sg_live_..." \
  -H "Content-Type: application/json" \
  -d '{"chunks": [{"content": "..."}], "max_omega": 60}'
```

### LangChain

```python
from sgraal.langchain_rag_guard import SgraalRAGGuard

guard = SgraalRAGGuard(your_retriever, api_key="sg_live_...", max_omega=60)
safe_docs = guard.get_relevant_documents("What is our refund policy?")
```

### LlamaIndex

```python
from sgraal.llamaindex_rag_guard import SgraalQueryEngineWrapper

wrapper = SgraalQueryEngineWrapper(your_engine, api_key="sg_live_...", max_omega=60)
safe_nodes = wrapper.retrieve("What is our refund policy?")
```

### Direct Filter (Framework-agnostic)

```python
from sgraal.rag_filter import SgraalRAGFilter

f = SgraalRAGFilter(api_key="sg_live_...", max_omega=60)
safe_chunks = f.filter(retrieved_chunks)
```

## How It Works

1. Each chunk is scored via Sgraal's preflight engine (omega 0-100)
2. Chunks with omega > max_omega are filtered out
3. Remaining chunks include `sgraal_omega` metadata for transparency

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| max_omega | 60 | Maximum omega score to pass through |
| on_unavailable | passthrough | Behavior when API unavailable: passthrough or block |
