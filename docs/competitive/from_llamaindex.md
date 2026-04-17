# Adding Sgraal to LlamaIndex

## What LlamaIndex does well

LlamaIndex is a data framework for building LLM applications with retrieval-augmented generation (RAG). It excels at ingesting diverse data sources (documents, databases, APIs), building indexes over them, and providing query engines that retrieve relevant context before the LLM generates a response. Its composable index architecture — vector stores, knowledge graphs, summary indexes — makes it the go-to framework for grounding LLM responses in private data. LlamaIndex handles the hard parts of chunking, embedding, retrieval, and response synthesis.

## What Sgraal adds

Sgraal sits between LlamaIndex's retrieval and your agent's decision logic. LlamaIndex handles data ingestion and retrieval — it answers *what relevant context can we find for this query?* Sgraal answers *is the retrieved context reliable enough to act on?* Before your agent consumes query results and makes a decision, Sgraal scores the retrieved nodes against 80+ reliability signals and returns a governance decision. LlamaIndex continues to own retrieval; Sgraal owns the safety gate.

## Migration

```python
from llama_index.core import VectorStoreIndex
from sgraal import SgraalClient

sg = SgraalClient(api_key="sg_live_...")
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()

# Before: query and act on results directly
# response = query_engine.query("What is the patient's dosage?")

# After: preflight the retrieved nodes before acting
retriever = index.as_retriever()
nodes = retriever.retrieve("What is the patient's dosage?")
entries = [{"id": n.node_id, "content": n.text, "type": "semantic",
            "timestamp_age_days": 0, "source_trust": n.score or 0.8,
            "source_conflict": 0.1, "downstream_count": 1}
           for n in nodes]
r = sg.preflight(entries, domain="medical", action_type="irreversible")
if r["recommended_action"] != "BLOCK":
    response = query_engine.query("What is the patient's dosage?")
```

## Key message

You don't replace LlamaIndex with Sgraal. You preflight it. LlamaIndex is data retrieval for LLMs; Sgraal is the preflight check that sits between LlamaIndex's retrieved context and your agent's decision logic.

> **Bridge available**: See the [`sgraal-llamaindex`](../../sgraal-llamaindex/) bridge SDK for a drop-in integration that wires this pattern into existing LlamaIndex workflows.
