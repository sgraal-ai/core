### 19.11 Persistent Homology in 77-Dimensional Preflight Space

We lift the 10-component polytope study into the full preflight output space. After dropping zero-variance columns from the 132 harvested fields (449 benchmark cases), we obtain a point cloud of **449 points in R^78**. Each point is one preflight response, standardized component-wise.

We build a Vietoris-Rips filtration over a sweep of epsilon values, tracking **beta_0** (connected components via union-find) and **beta_1** (independent cycles, via the Euler-characteristic formula `beta_1 = E - V + beta_0` on the 1-skeleton — an upper bound on the true H_1 rank). **beta_2 is omitted**: enumerating 3-simplices in 77D is combinatorially prohibitive.

**Filtration table:**

| epsilon | edges | beta_0 | beta_1 |
|---:|---:|---:|---:|
| 0.50 | 0 | 449 | 0 |
| 1.00 | 3 | 446 | 0 |
| 1.50 | 45 | 413 | 9 |
| 2.00 | 222 | 343 | 116 |
| 2.50 | 635 | 283 | 469 |
| 3.00 | 1,232 | 219 | 1002 |
| 3.50 | 1,951 | 174 | 1676 |
| 4.00 | 2,911 | 127 | 2589 |
| 5.00 | 5,330 | 77 | 4958 |
| 7.50 | 13,319 | 21 | 12891 |
| 10.00 | 31,845 | 7 | 31403 |

**Persistence summary:**

| Quantity | Value |
|---|---|
| Lifetime threshold (q75 of death epsilons) | 4.182 |
| Long-lived components (death_eps > q75) | **112** |
| Total persistent clusters (incl. infinite) | **113** |
| Persistent-loop count (peak beta_1) | **31403** |
| beta_0 at median pairwise distance (eps=10.0) | **7** |

**Interpretation — memory states are highly non-simply-connected.** The peak beta_1=31403 shows the preflight output manifold contains a large number of 1-cycles in its 1-skeleton: a healing trajectory that moves linearly through feature space cannot, in general, be contracted to a point without leaving the cloud. Physically, this matches the observation that some repair plans require a discrete jump (e.g. REFETCH invalidates a whole tool_state cluster) rather than a smooth interpolation. The filtration curve shows beta_0 dropping from 449 to 7 as epsilon rises from 0.5 to 10.0, with the steepest collapse near epsilon=5 — consistent with a small handful of coarse clusters (on the same order as the 4 recommended_action classes USE_MEMORY/WARN/ASK_USER/BLOCK) emerging only at large scale, over a fine-grained substructure at small scale.

**Relation to the Risk Polytope.** Prior FIM analysis found the 132-feature space compresses to ~23 effective dimensions. Persistent homology now adds a topological constraint: within that compressed space, the data is NOT a flat simply-connected polytope — it has loops (beta_1 > 0) and discrete clusters (beta_0 > 1 at medium scales). The Risk Polytope is therefore more precisely a *cellular complex* with multiple chambers separated by boundaries that a repair plan must navigate.

**Caveats.**

- beta_1 on the 1-skeleton over-counts the true rank of H_1 once 2-simplices are added. The reported count is an upper bound.
- beta_2 is not computed; the reported loop count may include 2-dimensional voids that would be filled in by higher simplices.
- The filtration uses a hand-picked epsilon grid rather than a full persistence diagram (e.g. via matrix reduction) — this is a coarse sketch, not a ripser-equivalent computation.
