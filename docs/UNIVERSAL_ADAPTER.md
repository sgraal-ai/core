# Universal Memory Adapter
Configure any vector DB backend with YAML/JSON. Auto-preflight on every query.
```yaml
backend:
  type: pinecone  # or weaviate, milvus, qdrant
  api_key: env:PINECONE_API_KEY
max_omega: 80
api_key: env:SGRAAL_API_KEY
```
