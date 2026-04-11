# Sgraal Examples

Runnable examples demonstrating Sgraal memory governance.

## Setup

```bash
pip install sgraal
```

## Examples

| File | Description |
|---|---|
| `01_basic_preflight.py` | Basic preflight validation — single memory entry |
| `02_rag_guardrail.py` | RAG pipeline guardrail — validate chunks before LLM |
| `03_multi_agent_chain.py` | Multi-agent provenance chain — detect circular references |
| `04_compound_attack_detection.py` | Compound attack surface — trigger multiple detection layers |

## Run

```bash
python examples/01_basic_preflight.py
python examples/02_rag_guardrail.py
python examples/03_multi_agent_chain.py
python examples/04_compound_attack_detection.py
```

All examples use the demo key `sg_demo_playground` (rate limited, no signup needed).
