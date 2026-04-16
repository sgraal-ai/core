### 19.6 Memory Immunology: do attack patterns mutate?

We treat each benchmark round as a 'generation' of attacks, extract a 10-component preflight signature per BLOCK-ed case, and compute cosine similarity between round centroids. A nearest-neighbour stitch produces a phylogenetic tree; the Hawkes-style mutation rate counts round pairs with cosine < 0.8.

**Signatures per round:**

| Round | Attacks analysed |
|-------|------------------|
| R1 | 16 |
| R2 | 40 |
| R3 | 13 |
| R4 | 39 |
| R5 | 45 |
| R6 | 31 |
| R7 | 67 |
| R8 | 39 |
| R9 | 99 |
| R10 | 120 |
| R11 | 115 |

**Mutation rate (cos<0.8, Hawkes-style λ):** 0.600

**Major clades (cos ≥ 0.9):** [[1, 2, 3, 4, 9, 10], [5, 11]]

**Phylogenetic tree (ASCII):**

```
R1 (root)
├── R2  (cos=0.990, edge=0.010)
│   ├── R5  (cos=0.513, edge=0.487)
│   │   ├── R8  (cos=0.857, edge=0.143)
│   │   └── R11  (cos=0.996, edge=0.004)
│   ├── R6  (cos=0.523, edge=0.477)
│   └── R7  (cos=0.694, edge=0.306)
├── R3  (cos=0.948, edge=0.052)
└── R4  (cos=0.991, edge=0.009)
    └── R9  (cos=0.974, edge=0.026)
        └── R10  (cos=0.967, edge=0.033)
```

High mutation regime: more than half of consecutive round transitions show cosine < 0.8. Attack signatures reshape aggressively across rounds; the threat landscape behaves like a rapidly mutating virus lineage. Major clades: [[1, 2, 3, 4, 9, 10], [5, 11]].

_Synthetic: signatures are derived from dry-run preflight responses on packaged benchmark corpora; the cosine geometry describes our scoring engine's view of each attack family rather than an external ground truth._
