# sgraal-rag

Sgraal memory governance filter for RAG pipelines. Validates retrieved documents before generation.

```bash
pip install sgraal-rag
```

```python
from sgraal_rag import SgraalRAGFilter

f = SgraalRAGFilter(api_key="sg_demo_playground", domain="fintech")
safe_docs = f.filter(retrieved_documents)
```

Compatible with LangChain and LlamaIndex:
```python
lc_filter = f.as_langchain_filter()
li_filter = f.as_llamaindex_filter()
```

## License
Apache 2.0
