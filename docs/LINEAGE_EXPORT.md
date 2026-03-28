# Memory Lineage Export

Export your agent memory lineage graph in multiple formats.

## Formats

### JSON (default)
```bash
curl https://api.sgraal.com/v1/store/lineage/export \
  -H "Authorization: Bearer sg_live_..."
```

### GraphML (Grafana, yEd, Gephi)
```bash
curl "https://api.sgraal.com/v1/store/lineage/export?format=graphml" \
  -H "Authorization: Bearer sg_live_..." \
  -o lineage.graphml
```

Import into Grafana via the NodeGraph panel or open in yEd/Gephi for visualization.

### RDF/Turtle (Knowledge Graphs, SPARQL)
```bash
curl "https://api.sgraal.com/v1/store/lineage/export?format=rdf" \
  -H "Authorization: Bearer sg_live_..." \
  -o lineage.ttl
```

Load into Apache Jena, Blazegraph, or any SPARQL endpoint.

## Power BI Integration

1. Export as JSON: `GET /v1/store/lineage/export?format=json`
2. In Power BI: Get Data > Web > paste URL with auth header
3. Transform JSON into table using Power Query
4. Build relationship diagrams with the built-in graph visual

## Grafana Integration

1. Export as GraphML
2. Install the NodeGraph panel plugin
3. Use the JSON API datasource pointing to `/v1/store/lineage/export`
4. Map `entries[].id` to node IDs
