
## Family 5 — Domain-adjusted half-life for CC detector

- **Cases it would resolve:** CC-016, CC-017
- **Description:** Add fintech-specific decay rates in `_check_confidence_calibration`. Financial data (FX rates, pricing) decays faster than the Weibull semantic default (half-life 69 days). Fintech entries older than hours may warrant staleness flags.
- **Effort:** 20-30 lines + domain half-life data table validation
- **Risk:** Fintech over-sensitivity if threshold too aggressive. All fintech entries in CC detector would be affected.
- **Priority:** LOW (2 cases, not blocking any commit or benchmark)
- **Origin:** Round 12 Phase 6.5 resolution family analysis, 2026-04-20
