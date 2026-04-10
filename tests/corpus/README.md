# Sgraal Benchmark Corpus

Public corpus files for the Sgraal × Grok joint benchmark.

## Files

| File | Round | Cases | Description |
|---|---|---|---|
| round4_cases.json | Round 4 | 90 | Real-world propagation |

## Format

All cases use MemCube v2 format.
See: api.sgraal.com/v1/standard/memcube-spec

## Results

| Round | Sgraal F1 | Grok F1 | Cases |
|---|---|---|---|
| 1 — Sponsored drift | 1.000 | 0.98 | 60 |
| 2 — Subtle drift | 1.000 | 0.98 | 59 |
| 3 — Hallucination | 1.000 | 1.000 | 60 |
| 4 — Real-world propagation | 1.000 | 1.000 | 90 |
| **Total** | **1.000** | **~0.995** | **329** |

## Usage

```bash
pip install sgraal
python3 tests/corpus/run_all.py
```
