# haystack-sgraal

Sgraal preflight validation bridge for [Haystack](https://haystack.deepset.ai) (deepset).

## Install

```bash
pip install haystack-sgraal
```

## Usage

```python
from haystack_sgraal import HaystackSgraal

sgraal = HaystackSgraal("sg_demo_playground", domain="legal")

docs = retriever.run(query="contract liability clause")["documents"]
safe_docs = sgraal.filter_safe_documents(docs, action_type="irreversible")
```
