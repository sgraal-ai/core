# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sgraal is a memory governance protocol for AI agents. It provides a preflight scoring engine that evaluates whether an AI agent's memory state is reliable enough to act on, returning a risk score (Ω_MEM) and a recommended action (USE_MEMORY, WARN, ASK_USER, BLOCK).

## Architecture

- **`scoring_engine/`** — Core Ω_MEM computation engine (pure Python, no dependencies). `omega_mem.py` contains the weighted scoring formula using 10 risk components (freshness, drift, provenance, propagation, recall, encode, interference, recovery, r_belief, s_relevance), scaled by action-type and domain criticality multipliers. S_freshness uses Weibull decay per memory type: tool_state (0.15, fast) > shared_workflow > episodic > preference > semantic > policy > identity (0.002, near-permanent). R_belief (weight 0.05) measures model belief divergence. S_relevance (weight 0.06) detects intent-drift via cosine similarity. Tier 1 self-healing generates a `repair_plan` with actions: REFETCH (freshness>60), VERIFY_WITH_SOURCE (conflict>50), REBUILD_WORKING_SET (belief<0.3), each with projected_improvement and priority. `healing_counter` tracks cumulative heals across entries. Healing policies defined in `healing_policy.yaml` (rule_id, condition, action, tier, idempotent). A2 axiom enforced: identical memory state + identical healing_counter = identical Ω_MEM score (deterministic, no randomness). `importance_detector.py` provides 4-signal importance detection: return_frequency, blast_radius, irreversibility, uniqueness → importance_score (0–10). At-risk when score >= 5.0 AND age > 70% of type threshold (tool_state=7d, semantic=100d, policy=200d, identity=500d). Preflight response includes `at_risk_warnings` with data-driven natural language warnings. `client_optimizer.py` provides generic client optimization — activated via `client` field in preflight request (any profile: grok, langchain, autogen, crewai, etc.), prioritizes REFETCH for stale tool_state entries, re-orders repair plan. Response includes `client_optimized` and `optimizer_version` (v2). `compliance_engine.py` evaluates against regulatory profiles (GENERAL, EU_AI_ACT, FDA_510K, HIPAA) — EU AI Act enforces Article 12 (blocks irreversible+high risk), Article 9 (medical oversight), Article 13 (transparency). Critical violations override recommended_action to BLOCK. `healing_policy_matrix.py` maps memory_type × domain × profile to healing tier and approval requirements. Preflight accepts optional `compliance_profile`, response includes `compliance_result`. `formal_verification.py` provides Z3 SMT verification of healing policies (no contradictions, BLOCK reachable, counter monotonic) and compliance rules (no rule both allows and blocks same action). Graceful fallback to logical verification when Z3 unavailable. `GET /v1/verify` endpoint runs both checks and accepts optional `history` parameter (comma-separated scores) for Kalman filter trend forecasting. `kalman_forecast.py` provides `KalmanForecaster` (1D Kalman, process_noise=0.1, measurement_noise=1.0) → trend (improving/stable/degrading), collapse_risk (0–1, probability of hitting BLOCK), and forecast_scores. `dependency_graph.py` enables surgical BLOCK — tracks step → entry dependencies, only halts steps that depend on stale entries while safe steps proceed. Preflight accepts optional `steps` field, returns `surgical_result` (blocked_steps, safe_steps, partial_execution_possible). `memory_tracker.py` auto-detects step→entry dependencies without manual declaration — when no `steps` provided, each entry becomes its own step (`auto:{id}`), response includes `auto_tracked: true`. Python SDK `StepTracker` context manager tracks access within step blocks. `privacy_layer.py` provides 3-layer protection: Layer 1 HMAC-SHA256 entry ID obfuscation per session, Layer 2 reason abstraction to categories (STALE/CONFLICT/LOW_TRUST/PROPAGATION_RISK/INTENT_DRIFT), Layer 3 ZK commitment hash. Default `detail_level="obfuscated"`, opt-in `detail_level="full"` for original IDs. Response includes `session_key` and `zk_commitment`. `thread_manager.py` provides thread bucketing + adaptive sampling for million-scale deployments — consistent hashing assigns threads to buckets, domain-based sample rates (medical/fintech/legal=100%, coding/customer_support=10%, general=50%). Sampled-out threads get lightweight USE_MEMORY response. Preflight accepts optional `thread_id`, response includes `sampled`, `bucket_id`, `sample_rate`. `shapley_explain.py` computes per-component Shapley values showing each component's contribution to the final Ω_MEM score (positive = increases risk, negative = decreases risk). Included in `/v1/preflight` and `/v1/preflight/batch` responses as `shapley_values`. `lyapunov.py` provides formal stability guarantee for the heal loop — V(x) = ω²/200 (positive definite), V̇(x) = -decay × V(x) (negative definite), proving asymptotic convergence. `/v1/heal` response includes `lyapunov_stability` (V, V_dot, converging, guaranteed). `importance_detector.py` also computes Value of Information (VoI) per entry — `voi_score` = expected Ω_MEM improvement if that entry were healed. At-risk warnings sorted by VoI descending (highest ROI first). `differential_privacy.py` implements ε-Differential Privacy via Laplace mechanism — Pr[M(D)∈S] ≤ exp(ε)·Pr[M(D')∈S] guaranteed. Deterministic seeded noise preserves A2 axiom. Preflight accepts optional `dp_epsilon`, response includes `privacy_guarantee` (epsilon, mechanism, dp_satisfied). Custom decision thresholds via `thresholds` field (e.g. `{"warn": 40, "ask_user": 60, "block": 80}`). Audit logging: every preflight/heal call logged to Supabase `audit_log` with request_id, api_key_id, decision, omega_mem_final, agent_id, domain, action_type. Supabase column is `created_at` (not `timestamp`). `request_id` (uuid) in every preflight response. `pagerank.py` computes PageRank authority scores (d=0.85) over memory dependency graph — opt-in via `use_pagerank: true`, adds `r_importance` as 13th component (weight 0.04, risk = authority × freshness) and `authority_scores` (0–10 per entry) to response. `drift_detector.py` computes 4-method drift ensemble: KL divergence, Wasserstein distance, Jensen-Shannon divergence, and α-Divergence (D_α for α∈{0.5, 1.5, 2.0}, log-space computation). drift_method=ensemble_5 with equal weights (0.2 each) when all 5 methods available: KL + Wasserstein + JSD + α-Divergence + MMD. `compute_mmd` uses RBF kernel k(x,y)=exp(-||x-y||²/(2σ²)) with median heuristic σ. MMD²(P,Q) = E[k(X,X')] + E[k(Y,Y')] - 2E[k(X,Y)]. Requires ≥ 2 samples. Falls back to ensemble_4 if MMD unavailable, ensemble_3 if α also fails. Every preflight response includes `drift_details` (kl_divergence, wasserstein, jsd, alpha_divergence, drift_method, ensemble_score). `trend_detection.py` provides CUSUM (S⁺ₜ/S⁻ₜ, h=5) and EWMA (λ=0.2, 3σ) detectors — `drift_sustained=true` when 4+ consecutive degradations and both agree. Preflight accepts optional `score_history`, returns `trend_detection` (cusum_alert, ewma_alert, drift_sustained, consecutive_degradations). `calibration.py` provides ML calibration layer: Brier score (assurance accuracy), log loss (penalizes confident errors), softmax temperature scaling (T=1.5, smooths overconfident scores), logistic meta-layer P(unsafe)=σ(β₀+Σβᵢ·Cᵢ). Every preflight response includes `calibration` (brier_score, log_loss, calibrated_scores, meta_score). `hawkes_process.py` models memory update bursts via Hawkes self-exciting process λ(t) = μ + Σ α·exp(-β·(t-tᵢ)). Detects excitement bursts when entries update in quick succession. Every preflight response includes `hawkes_intensity` (current_lambda, baseline_mu, excited, burst_detected). `copula.py` models joint dependence between s_freshness and s_drift via Gaussian copula C(u,v) = Φ₂(Φ⁻¹(u), Φ⁻¹(v), ρ). Detects tail dependence when both are elevated simultaneously — joint risk exceeds independent prediction. Every preflight response includes `copula_analysis` (rho, joint_risk, tail_dependence). `mewma.py` provides Multivariate EWMA joint monitoring — Hotelling T² = Zₜᵀ·Σ⁻¹·Zₜ across 5 key components (λ=0.2, h=12, α=0.01). Every preflight response includes `mewma` (T2_stat, control_limit, out_of_control, monitored_components). `sheaf_cohomology.py` automatically computes source_conflict via sheaf over memory entries — nodes=entries, edges=content overlap, H¹ rank=inconsistent cycles. When `source_conflict` not provided in request, auto_source_conflict feeds into s_interference. Manual override preserved for backward compat. Response includes `consistency_analysis` (consistency_score, h1_rank, inconsistent_pairs, auto_source_conflict). `rl_policy.py` implements Causal Q-learning: Q(s,a)=E[r|do(a),s] with α=0.1, γ=0.9. State=[omega,freshness,drift,provenance] discretized into 4 bins (256 states × 4 actions). Separate Q-tables per domain. Rewards: success=+1, failure=-1, failure+USE_MEMORY=-2. Cold start: 10 episodes before RL overrides. `/v1/outcome` updates Q-table. Preflight includes `rl_adjustment` (q_value, rl_adjusted_action, learning_episodes, confidence). `bocpd.py` implements Bayesian Online Change Point Detection — P(rₜ|x_{1:t}) with Gaussian likelihood and configurable hazard rate (H=0.01). Regime change when P(changepoint)>0.9 triggers merkle_reset. Integrated into `trend_detection.bocpd` (p_changepoint, regime_change, current_run_length, merkle_reset_triggered). `rmt.py` implements Random Matrix Theory signal/noise separation — Marchenko-Pastur boundary λ_signal=σ²·(1+√γ)² separates real interference from spurious correlations. Builds pairwise interference matrix (cosine/Jaccard). Preflight includes `rmt_analysis` (signal_eigenvalues, noise_threshold, true_interference_count, signal_ratio) when 2+ entries. `causal_graph.py` implements LiNGAM causal structure discovery — kurtosis-based causal ordering, OLS edge weights, metadata fallback. Identifies root_cause and causal_chain via BFS. Preflight includes `causal_graph` (edges with strength, root_cause, causal_chain, causal_explanation) when significant edges found. `spectral.py` computes Spectral Graph Laplacian L=D-A — Fiedler value (λ₂) measures algebraic connectivity, Cheeger bound λ₂/2≤h(G)≤√(2λ₂), mixing time τ=O(1/λ₂). graph_connectivity: fragmented/normal/dense. Preflight includes `spectral_analysis` (fiedler_value, spectral_gap, graph_connectivity, cheeger_bound, mixing_time_estimate) when 2+ entries. `consolidation.py` computes Memory Consolidation Score combining Hopfield network energy and Mutual Information: ConsolidationScore = MI(R_old, R_new) / H(R_old) · exp(-γ · Hopfield_energy). Per-entry scores with stable/fragile classification (stable_threshold=0.7, fragile_threshold=0.3). Hopfield energy E = -½ · Σᵢⱼ wᵢⱼ · sᵢ · sⱼ from cosine similarity weight matrix. Returns replay_priority sorted ascending (lowest score = needs replay most). Preflight includes `consolidation` (scores, mean_consolidation, fragile_entries, replay_priority) when 1+ entries. `jump_diffusion.py` implements Jump-Diffusion process dX = f(X,μ)dt + σdW + J·dN(t) for detecting sudden memory state changes (flash-crash events). Uses MAD-based robust σ estimation, Poisson jump rate λ = count(|change| > 3σ) / n, jump detection via 3σ threshold. flash_crash_risk when λ > 0.1. Top-level `cascade_risk` field = true when jump_detected AND hawkes burst_detected simultaneously. Requires 5+ observations in score_history. Preflight includes `jump_diffusion` (jump_detected, jump_size, jump_rate_lambda, diffusion_sigma, flash_crash_risk, expected_next_jump) and `cascade_risk` (bool, top-level). `hmm.py` implements 3-state Regime-Switching Hidden Markov Model (STABLE/DEGRADING/CRITICAL). Baum-Welch (EM) for parameter estimation in log-space, Viterbi decoding for state classification. Gaussian emissions, MAD-robust initialization from data terciles. Requires 20+ historical observations in score_history. Top-level `regime_collapse_risk` = true when HMM current_state=CRITICAL AND BOCPD regime_change=true simultaneously. Preflight includes `hmm_regime` (current_state, state_probability, transition_probs, regime_duration) and `regime_collapse_risk` (bool, top-level). `zk_sheaf.py` combines FV-06 Zero-Knowledge commitment with SH-01 Sheaf Cohomology: Proof_cons = FV-06_ZK ∧ ∀e∈E (restrict(sᵢ,e) = restrict(sⱼ,e)). commit = SHA256(consistency_score || h1_rank || entry_ids_sorted || nonce). proof_valid when consistency_score >= 0.95 AND h1_rank = 0. Wired into EU_AI_ACT compliance: adds `zk_consistency_proof: true` when proof valid. Preflight includes `zk_sheaf_proof` (commitment, proof_valid, n_edges_verified, nonce, verified_at) when sheaf_result available. `ornstein_uhlenbeck.py` implements Ornstein-Uhlenbeck mean-reversion process dX = θ(μ - X)dt + σdW for recovery prediction. OLS parameter estimation on discrete OU transitions, half-life = ln(2)/θ, conditional expectation E[X_{t+s}] = μ + (X_t - μ)·exp(-θ·s). Requires 10+ observations. Preflight includes `ornstein_uhlenbeck` (mean_reverting, half_life, expected_value_5, expected_value_10, equilibrium, current_deviation). Redis ring buffer `te_history:{api_key_hash}:{domain}` stores last 100 omega scores for OU estimation when score_history not provided. Wired into repair_plan: WAIT action when mean_reverting + half_life < 10, MANUAL_HEAL when not mean-reverting. `free_energy.py` implements variational Free Energy functional F = -ELBO where ELBO = E_q[log p(x|z)] - KL(q(z)||p(z)). Uses calibration meta-layer as approximate posterior q(z), Gaussian prior p(z)=N(0,1). KL = ½(μ² + σ² - log σ² - 1). Surprise = F/max_observed_F normalized 0-1. max_observed_F tracked in Redis (key: fe_max:{api_key_hash}:{domain}, TTL 7200s). Entries with surprise > 0.8 get elevated at_risk_warnings with free_energy_surprise tag. Preflight includes `free_energy` (F, elbo, kl_divergence, reconstruction, surprise). `levy_flight.py` estimates Lévy α-stable distribution stability index via McCulloch's quantile method (ν_α = (Q_95-Q_05)/(Q_75-Q_25), interpolated to α). Scale parameter c = IQR/2 (robust). Hill estimator fallback when IQR degenerate. α=2 Gaussian (light), α∈[1.5,2) moderate, α∈[1,1.5) heavy, α<1 extreme. heavy_tail_risk when α < 1.5. Wired into cascade_risk (heavy_tail + jump + burst = cascade) and repair_plan (MONITOR action for heavy-tail risk). Redis ring buffer reuse for history. Preflight includes `levy_flight` (alpha, scale, heavy_tail_risk, extreme_event_probability, tail_index) when 10+ observations. `sinkhorn.py` implements Sinkhorn optimal transport: W_ε(P,Q) = min_{γ∈Π} Σᵢⱼ γᵢⱼCᵢⱼ + ε·KL(γ‖P⊗Q). Iterative u ← a/(Kv), v ← b/(Kᵀu) with K = exp(-C/ε), ε=0.1, max 100 iterations, convergence 1e-6. Cost matrix normalized C/C.max()+1e-8. Replaces exact Wasserstein in drift_detector.py when n_entries > 5, falls back to exact on non-convergence. drift_details includes `sinkhorn_used` (bool) and `sinkhorn_iterations` (int). `rate_distortion.py` implements Rate-Distortion optimal retention: γ(t) = argmin[I(X;X̂) + λ·E[d(X,X̂)]]. Per-entry information_value (Shannon entropy), distortion_cost (MSE from mean), keep_score = info/distortion. recommend_delete when keep_score < 0.3 AND omega < 40. λ = 0.5*(1 - system_health/100) dynamically scaled. Wired into repair_plan: DELETE action for deletable entries. Preflight includes `rate_distortion` (entries, total_rate, total_distortion, compression_ratio, deletable_count, lambda_used). `stability_score.py` provides R_total normalized (DeepSeek: Δα/Δα₀ + β/β₀ + H/H₀ + ω₀/ω₀_crit + λ₂/λ₂_crit, capped at 5.0) and StabilityScore 9-component (Grok: (1/9)·Σ(1 - Cₖ/Cₖ_max), 0-1 range). Components: delta_alpha, p_transition, omega_drift, omega_0, lambda_2, hurst, h1_rank, tau_mix, d_geo_causal. Missing components fallback to 0.0. Preflight includes `r_total_normalized` (float, 0-5) and `stability_score` (score, components, interpretation: stable/degrading/critical). Dashboard shows StabilityScore gauge and R_total progress bar. `unified_loss.py` implements L_v4 Unified Loss = Σ λᵢ·signᵢ·Lᵢ over 11 components: L_IB (ELBO), L_RL (Q-value), L_EWC (Hopfield), L_SH (h1_rank), L_HG (OU deviation), L_FE (free energy F), L_OT (Wasserstein), -T_XY (transfer entropy, negative sign), L_LDT (extreme prob), Var_dN (jump rate), L_CA (1-stability). Geodesic weight update: Δλᵢ = -lr·(1/λᵢ²)·∂L/∂λᵢ with diagonal FIM, triggered on /v1/outcome. λ weights stored in Redis (key: lv4_weights:{hash}:{domain}, TTL 86400s), clipped [0.01, 10.0]. Preflight includes `unified_loss` (L_v4, components, lambda_weights, dominant_loss, geodesic_update_count). `policy_gradient.py` implements Policy Gradient with Advantage: ∇_θ J = E[∇_θ log π_θ(a|s) · A(s,a)], A(s,a) = Q(s,a) - V(s). Softmax policy π_θ(a|s) = exp(Q/τ)/Σexp(Q/τ) with temperature decay τ = max(0.1, τ·0.99) per /v1/outcome. pg_override when episodes ≥ 20, advantage > 0.1, not exploration_mode — sets recommended_action and rl_adjusted_action to softmax argmax (consistent). Temperature stored in Redis (key: pg_temperature:{hash}:{domain}, TTL 86400s). Preflight includes `policy_gradient` (action_probabilities, advantage, temperature, policy_entropy, exploration_mode) and optional `pg_override` (bool, top-level). `info_thermodynamics.py` implements transfer entropy T_{X→Y} = H(Y_t|Y_{t-1}) - H(Y_t|Y_{t-1},X_{t-1}) via binned estimation, Landauer's bound E_min = kT·ln(2)·bits_erased, information temperature τ = Var(scores)/Mean(scores), entropy production σ = mean|ΔX|/100 (2nd law: σ ≥ 0), reversibility = 1/(1+10σ). max_flow feeds T_XY in unified_loss (negative sign = maximize). Redis ring buffer reuse for history. Preflight includes `info_thermodynamics` (transfer_entropy, max_flow, landauer_bound, information_temperature, entropy_production, reversibility) when 5+ observations. `mahalanobis.py` computes Mahalanobis distance D_M(x,μ) = sqrt((x-μ)ᵀ·Σ⁻¹·(x-μ)) per entry over 5 components (s_freshness, s_drift, s_provenance, s_relevance, r_belief). Anomaly when D_M > χ²₀.₉₅(df) via Wilson-Hilferty approximation (dynamic df). Σ_reg = Σ + 0.01·I. Gauss-Jordan inversion with partial pivoting. Wired into s_interference: +(anomaly_count/n)*20, capped at 100. Requires 3+ entries. Preflight includes `mahalanobis_analysis` (distances, mean_distance, anomaly_count, covariance_condition, chi2_threshold). `page_hinkley.py` implements Page-Hinkley online change detection: mₜ = mₜ₋₁ + (xₜ - μ̂ₜ - δ), PHₜ = mₜ - min mᵢ, alert when PHₜ > λ. Detects exact step where drift became permanent. Accepts `page_hinkley_config` in request (delta, lambda). Top-level `permanent_shift_detected` = true when PH alert AND BOCPD regime_change. Redis ring buffer for history. In trend_detection: `page_hinkley` (ph_statistic, alert, change_magnitude, steps_since_change, running_mean, delta_used, lambda_used). `provenance_entropy.py` computes Shannon entropy H = -Σ pᵢ·log(pᵢ) on provenance graph using source_trust/conflict weights. High entropy = many equally weighted sources = conflict probable. Wired into s_provenance: +(mean_entropy/log(n))*10, capped at 100. entropy_trend from Redis history (prov_entropy:{hash}:{domain}, TTL 3600s). Preflight includes `provenance_entropy` (per_entry, mean_entropy, high_entropy_entries, entropy_trend). `subjective_logic.py` implements Subjective Logic opinions B = {b, d, u, a} where b=trust, d=conflict, u=1-b-d, a=0.5. Projected probability P(X) = b + a·u (more conservative than raw trust). Cumulative fusion: b_f = (b₁u₂ + b₂u₁)/(u₁+u₂-u₁u₂). Clips proportionally when trust+conflict > 1.0. Wired into s_provenance: replaces raw trust with (1 - fused projected_prob)*100. Preflight includes `subjective_logic` (opinions, fused_opinion, high_uncertainty_entries, consensus_possible). `frechet.py` implements Frechet distance FD = ||μ_P-μ_Q||² + Tr(Σ_P+Σ_Q-2·sqrt(Σ_P·Σ_Q)) via Denman-Beavers matrix square root iteration (pure Python, no scipy). Regularized covariance Σ+1e-6·I. encoding_degraded when FD > 10.0. Reference stored in Redis (frechet_ref:{hash}:{domain}, TTL 86400s), reset via `reset_frechet_reference: true`. Wired into r_encode: +15 when degraded. Preflight includes `frechet_distance` (fd_score, mean_shift, covariance_shift, encoding_degraded, reference_age_steps) when 3+ entries and reference available. `mutual_information.py` implements MI(X;Y) = -0.5·log(1-rho^2) with clipped rho ∈ [-0.999, 0.999] and NMI = MI/sqrt(H(X)·H(Y)) ∈ [0,1]. encoding_efficiency: high > 0.7, medium 0.4-0.7, low < 0.4. Wired into r_encode: +(1-nmi)*20. Preflight includes `mutual_information` (mi_score, nmi_score, encoding_efficiency, information_loss) when 2+ entries. `mdp.py` implements MDP V*(s) = max_a [R(s,a) + γ·ΣP(s'|s,a)·V*(s')] for optimal healing strategy. 4 states (SAFE/WARN/DEGRADED/CRITICAL), 4 actions (WAIT/SOFT_HEAL/FULL_HEAL/EMERGENCY_HEAL). Value iteration (γ=0.9, max 100 iter). Transitions from Redis or heuristic defaults. Wired into repair_plan: MDP action prepended when != WAIT. Preflight includes `mdp_recommendation` (optimal_action, expected_value, action_values, state, confidence). `mttr.py` implements MTTR = λ·Γ(1+1/k) via Weibull estimation with Lanczos gamma function (pure Python). p95 = λ·(-log(0.05))^(1/k). Recovery probability P(T<10) = 1-exp(-(10/λ)^k). Weibull k,λ from method of moments. Redis history (mttr_history:{hash}:{domain}, 50 entries, TTL 86400s). Wired into repair_plan: SLA_WARNING when p95 > 20. Preflight includes `mttr_analysis` (mttr_estimate, mttr_p95, recovery_probability, weibull_k, weibull_lambda, sla_compliant, data_points). `ctl_verification.py` implements Computation Tree Logic bounded model checking (k=10 steps). EF(omega<50): recovery reachable. AG(heal→AF(decrease)): healing convergence on all paths. EG(omega<80): stable operation possible. BFS/DFS reachability over 4-state transition graph. Wired into EU AI Act compliance: warning when ag_heal_works=false. Timeout < 100ms. Preflight includes `ctl_verification` (ef_recovery_possible, ag_heal_works, eg_stable_possible, verified_states, verification_time_ms, bounded_steps, ctl_formulas). `lyapunov_exponent.py` computes finite-time Lyapunov exponent λ = (1/N)·Σ log(|Δx_{i+1}|/|Δx_i| + ε). λ<0 converging, λ≈0 neutral, λ>0 diverging. chaos_risk when λ > 0.1. Wired into StabilityScore as 10th component (lyapunov_lambda/1.0, backward compatible 9-component when null). CHAOS_WARNING in repair_plan. Preflight includes `lyapunov_exponent` (lambda_estimate, chaos_risk, stability_class, divergence_rate) when 10+ observations. stability_score now includes `component_count` (9 or 10). `banach.py` verifies contraction mapping k = median(|Δx_{i+1}|/|Δx_i|), contraction_guaranteed when k < 1, convergence_steps = log(0.01)/log(k). Skips identical pairs, k=0 when all identical. BANACH_WARNING in repair_plan. Preflight includes `banach_contraction` (k_estimate, contraction_guaranteed, convergence_steps, fixed_point_estimate) when 5+ observations. `hotelling_t2.py` implements Hotelling T² = (x-μ)ᵀΣ⁻¹(x-μ) multivariate control chart. UCL = χ²₀.₉₉(df) dynamic. Phase 1 calibrating (< 10 obs), Phase 2 monitoring with Redis reference (hotelling_ref:{hash}:{domain}, TTL 86400s). Regularized Σ+0.01·I. out_of_control entries added to at_risk_warnings. Preflight includes `hotelling_t2` (t2_statistic, ucl, out_of_control, components_contributing, phase). `fisher_rao.py` computes diagonal Fisher-Rao metric g_ii = 1/(Var(component_i)+eps). geometry: flat/moderate/curved by condition number. `geodesic_flow.py` computes theta_{t+1} = theta_t - lr*g^-1*grad_L, manifold_distance = sqrt(sum g_ii*dtheta^2). Natural gradient flag in unified_loss when Fisher-Rao available. `koopman.py` implements Koopman operator via 1D DMD least-squares. Eigenvalue, stable when |K|<=1, prediction_5 = K^5*x_t. `ergodicity.py` measures Delta = |time_avg - ensemble_avg|, ergodic when Delta < 5.0. Preflight includes `fisher_rao`, `geodesic_flow`, `koopman` (10+ obs), `ergodicity` (5+ obs). `extended_freshness.py` implements W-03 Gompertz S=exp(-theta*exp(alpha*t)), W-04 Holt-Winters double exponential smoothing (alpha=0.3, beta=0.1, 5+ history), W-05 Power-law S=(1+t/tau)^(-alpha). Ensemble freshness: weibull 0.4 + gompertz 0.2 + holt_winters 0.2 + power_law 0.2, with weight redistribution when model unavailable. recommended_model by type: gompertz for preference, power_law for semantic/factual, weibull default. Wired into s_freshness. Preflight includes `extended_freshness` (gompertz, holt_winters, power_law, recommended_model, ensemble_freshness, models_used). `persistent_homology.py` computes Betti numbers β₀ (components) and β₁ (loops) via Vietoris-Rips filtration at 5 scales. BFS for components, Euler characteristic for β₁. structural_drift when β₁>0. topology_summary: simple/looped/complex. Requires 3+ entries. `ricci_curvature.py` computes Ollivier-Ricci κ(i,j) = 1 - W₁(μᵢ,μⱼ)/d(i,j). Positive κ = stable cluster, negative = fragile bottleneck. Entries with κ < -0.5 get ricci_fragile_connection at_risk_warnings. Requires 2+ entries. Preflight includes `persistent_homology` and `ricci_curvature`. `recursive_colimit.py` computes GlobalState via category theory colimit: GlobalState(t+1) = normalize(GlobalState(t)*mean(omega)*H1_factor). Min-max normalization with Redis persistence. First call = 0.5 uninformed prior. Wired into StabilityScore as optional 11th component. `cohomological_gradient.py` computes gradient_i = (dL_FE/dlambda_i + h1_rank)/(g_ii + eps) using Fisher-Rao FIM and sheaf H1. cohomological_update_used flag in unified_loss. Preflight includes `recursive_colimit` and `cohomological_gradient`. `cox_hazard.py` implements h(t)=h0*exp(beta*x) Cox proportional hazard for survival analysis. `arrhenius.py` models k=A*exp(-Ea/RT) thermal degradation. `owa_provenance.py` computes OWA weighted aggregation with linear weights and orness measure. `poisson_recall.py` models recall errors via Poisson lambda with Redis persistence. `roc_monitoring.py` computes online AUC via trapezoid rule. Preflight includes `cox_hazard`, `arrhenius`, `owa_provenance`, `poisson_recall`, `roc_monitoring`. `frontdoor.py` implements Pearl front-door criterion P(Y|do(X)) with domain/action/type confounders. `expected_utility.py` computes EU(a) = P(success)*V - P(failure)*C with Q-value or prior fallback. `cvar.py` computes VaR_5 and CVaR (mean below VaR) tail risk. `gumbel_softmax.py` implements y_i = exp((log(pi)+g)/tau) Gumbel relaxation. `fisher_rao.py` extended with off-diagonal FIM top-3 interactions. Preflight includes `frontdoor_effect`, `expected_utility`, `cvar_risk`, `gumbel_softmax`, `fim_extended`. `simulated_annealing.py` implements P(accept)=exp(-dE/T) with cooling schedule T=T0*0.95^t, active after 20 geodesic updates. `lqr_control.py` computes u*=-K*x optimal control (K=Q/(R+Q)=0.909, target omega=50). `persistence_landscape.py` extracts landscape values from betti_1. `topological_entropy.py` computes h=log(distinct_states)/log(n_steps). `homology_torsion.py` detects torsion when beta_1>0 AND h1_rank>0, hallucination_risk forces ASK_USER override. Preflight includes `simulated_annealing`, `lqr_control`, `persistence_landscape`, `topological_entropy`, `homology_torsion`. `dirichlet_process.py` implements Chinese Restaurant Process clustering (alpha=1.0, cosine>0.7). `particle_filter.py` implements SMC with 50 particles, Gaussian transition/likelihood, ESS-based resampling. `pctl_verification.py` runs 100 Monte Carlo simulations for probabilistic CTL. `dual_process_auq.py` combines System1 (fast omega) + System2 (ensemble of 5 signals) with 0.3/0.7 weighting. `security_transfer_entropy.py` detects information leakage between sensitive/non-sensitive entries. `sparse_merkle.py` computes SHA256 Merkle root for tamper detection. Preflight includes `dirichlet_process`, `particle_filter`, `pctl_verification`, `dual_process_auq`, `security_transfer_entropy`, `sparse_merkle`.
- **`api/`** — FastAPI REST API (255 route handlers). Key endpoints: `/v1/preflight` (scoring with 83 analytics modules), `/v1/explain`, `/v1/preflight/batch` (up to 100 entries), `/v1/heal`, `/v1/outcome`, `/v1/signup`, `/v1/verify`, `/v1/compliance/gdpr`, `/v1/compliance/sla`, `/v1/compliance/docs`, `/v1/compliance/eu-ai-act/report`, `/v1/audit-log` (with `timestamp` and `omega` alias fields mapped from Supabase `created_at`/`omega_mem_final`), `/v1/audit-log/export` (Splunk/Datadog/Elastic/CSV), `/v1/api-keys/generate` (returns full key once), `/v1/approvals` (enriched with agent_id from audit_log), `/health`. Preflight response includes `heal_decision` (alias for repair_plan[0].action), `stability_gauge` (alias for stability_score.score), `hysteresis_applied` (bool). Deterministic seeding: SHA256 of input passed to particle_filter and pctl_verification. Hysteresis suppresses omega jitter < 3.0 from stochastic modules. API key validation cached in Redis (TTL 300s, invalidated on revoke); all key generation endpoints (`/v1/api-keys/generate`, `/v1/signup`, `/v1/auth/register`) prime Redis cache immediately after Supabase insert. All endpoints use `Authorization: Bearer` header. Four post-reconciliation detection layers (cannot be overridden): `timestamp_integrity` (Round 6), `identity_drift` (Round 7), `consensus_collapse` (Round 8), `provenance_chain_integrity` (MemCube v3) — all MANIPULATED → BLOCK. `attack_surface_score` (0.0–1.45) computes compound risk from all 4 layers: `r1 + 0.3*r2 + 0.1*r3 + 0.05*r4`. `naturalness_score` detects synthetic/fabricated memory states via statistical signals (trust variance, conflict uniformity, downstream implausibility). Memory vaccination: on MANIPULATED BLOCK, extracts attack signature to Redis for fleet-wide immunity; endpoints `/v1/vaccines`. Compromised agent registry: agents from provenance chains auto-added on MANIPULATED BLOCK; endpoints `/v1/compromised-agents`. `detection_feedback_applied` boosts component_breakdown display values based on detection results (display-only, does not change omega_mem_final). Two policy systems: (1) `/v1/policy/validate` + `/v1/policy/apply` for inline .sgraal config validation, (2) `/v1/policies` CRUD + `/v1/policies/{name}/apply` for named policy registry in Redis — both intentional, different use cases. Calibration loop: `POST /v1/calibration/run` triggers automated corpus calibration, classifies mismatches (corpus_wrong/threshold_wrong/ambiguous), suggests threshold adjustments; `GET /v1/calibration/report`, `/v1/calibration/human-review`, `POST /v1/calibration/resolve/{case_id}`. All four detection layers fire independently. `POST /v1/adapt` converts any format (mem0/langchain/raw) to MemCube. `POST /v1/migrate` converts + runs preflight in one call. Policy registry: `POST /v1/policies` CRUD + `POST /v1/policies/{name}/apply`. `POST /v1/sla/configure` + `GET /v1/sla/status` for per-domain SLA monitoring. `GET /v1/failure-patterns` exports 8 attack pattern datasets. `POST /v1/policy/validate` + `POST /v1/policy/apply` for .sgraal config files. `GET /v1/vaccines` + `GET /v1/compromised-agents` for fleet immunity. Auto profile: irreversible/destructive → standard, informational/reversible → compact. HTTP headers: `X-Sgraal-Decision`, `X-Sgraal-Omega`, `X-Sgraal-Attack-Surface`, `X-Sgraal-Naturalness` set via middleware. `memory_location` optional field (MemCube v3). Valid domains: general, customer_support, coding, legal, fintech, medical. Valid action_types: informational, reversible, irreversible, destructive. Optionally logs to Supabase (`memory_ledger` + `audit_log` tables). Self-hosting: `Dockerfile` + `docker-compose.yml` + `SELF_HOSTING.md`.
- **`examples/`** — Usage examples for the scoring engine.
- **`web/`** — Next.js landing page (legacy). Superseded by `web-static/` for production.
- **`web-static/`** — Static HTML landing pages deployed to Vercel at [sgraal.com](https://www.sgraal.com). 30+ pages: index, decide, protect, comply, scale, pricing, blog, privacy, terms, docs, playground, benchmark, compatibility, roi, security, propagation, passport, changelog, standard, whitepaper, case-studies, failures, tutorial, latency, integrations/conway, integrations/agentkit, standard/provenance. Deploy: `cd web-static && vercel --prod`.
- **`dashboard/`** — Decision Readiness Dashboard (Next.js 16, deployed to Vercel at app.sgraal.com). 23 pages. Connected to live Sgraal API — enter API key via Settings panel. Discovers real agents from audit log, falls back to demo fleet. Key pages: `/` fleet overview with Executive Summary on BLOCK cards (reason + fix in plain English), OmegaMeter gauges, R_total color-coded; `/agent/[id]` detail with Executive Summary card, component breakdown, repair plan, forensics, Decision Twin, Time Machine, Advanced Analytics (collapsed by default); `/analytics` risk prevention framing, decision breakdown bars, domain BLOCK% bars; `/audit` with relative timestamps, color-coded omega badges, clickable agent rows; `/comply` EU AI Act report with force_refresh, SIEM export (Splunk/Datadog/Elastic); `/protect` circuit breaker explanation, red team, firewall history; `/scale` learning status, health history with outcome hints; `/team` API key creation modal (show full key once, then masked); `/code-generator` domain-specific entries, os.environ key pattern; `/templates` with Start Here badge and inline code preview. Deploy: `cd dashboard && vercel --prod`.
- **`mcp/`** — `@sgraal/mcp` npm package. MCP server (`sgraal_preflight` tool) for Claude Desktop, plus `createGuard()` and `withPreflight()` middleware for LangGraph/Node.js. Reads `SGRAAL_API_KEY` from env. Blocks on BLOCK, warns on WARN, passes through on USE_MEMORY.
- **`spec/`** — MemCube specification. `memcube.schema.json` defines the standardized memory entry format (JSON Schema draft 2020-12). 7 required fields (id, content, type, timestamp_age_days, source_trust, source_conflict, downstream_count) and 6 optional fields (goal_id, source, provenance, gsv, context_tags, geo_tag). MemCube v3 adds optional `provenance_chain` (list of agent_ids that touched the entry). Memory types: episodic, semantic, preference, tool_state, shared_workflow, policy, identity. See `MEMCUBE.md` for field documentation and examples.
- **`sdk/python/`** — `sgraal` PyPI package (`pip install sgraal`). `SgraalClient` with `preflight()` and `signup()`, circuit breaker (3 failures → OPEN, 30s recovery), local Weibull-only fallback scoring when API unavailable. `@guard()` decorator. `GeminiGuard` and `OpenAIGuard` wrap google-generativeai and openai SDKs.
- **`sdk/mem0_bridge/`** — `mem0-sgraal` PyPI package. SafeMemory wraps Mem0 Memory with automatic preflight guards.
- **Bridge SDKs** (26 integrations) — `sgraal-mnemos/`, `sgraal-memvid/`, `sgraal-llamaindex/`, `sgraal-haystack/`, `sgraal-semantic-kernel/`, `sgraal-langsmith/`, `sgraal-langfuse/`, `sgraal-vercel-ai/`, `sgraal-pydantic-ai/`, `sgraal-google-adk/`, `sgraal-llm-wrapper/`, `sgraal-normalizer/`, `sgraal-mngr/`, `sgraal-bedrock/`, `sgraal-azure-ai/`, `sgraal-zep/`, `sgraal-letta/`. Each wraps provider-specific memory/context into MemCube format and runs Sgraal preflight.
- **`scripts/`** — Stripe setup, Supabase migrations, pg_cron monthly reset, outcome_log table migration, and `shadow_calibration.py` (legacy stub — superseded by `api/calibration_engine.py` and `/v1/calibration/run` endpoint).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server locally
uvicorn api.main:app --reload

# Run tests (2,024+ tests across 25 test files)
pip install pytest httpx
python3 -m pytest tests/ -v

# Run single test file
python3 -m pytest tests/test_api_key_cache.py -v

# Run benchmark corpora against live API (614 cases total)
python3 tests/corpus/run_all.py
python3 tests/corpus/round6_memory_time_attack.py
python3 tests/corpus/round7_identity_drift.py
python3 tests/corpus/round5_consensus_poisoning.py
python3 tests/corpus/round8_consensus_collapse.py
python3 tests/corpus/run_adversarial.py

# Run example scoring
python examples/basic_usage.py

# Build dashboard
cd dashboard && npx next build

# Deploy dashboard
cd dashboard && vercel --prod

# Deploy landing page
cd web-static && vercel --prod
```

## Testing

### Run all unit tests:
```bash
python3 -m pytest tests/ --tb=short -q
```

### Run all corpus tests (against live API):
```bash
python3 tests/corpus/run_all.py
```

### Baseline — do not drop below:
- pytest: 2,228+ passing
- Corpus total: 614 baseline (Rounds 1-8) + 216 adversarial + 120 Round 9 = 950 total validated cases
  - Rounds 1-4: 329/329 (Joint: 60, Sponsored: 60, Subtle: 59, Hallucination: 60, Propagation: 90)
  - Round 5 — Consensus Poisoning: 45/45
  - Round 6 — Memory Time Attack: 60/60
  - Round 7 — Identity Drift: 90/90
  - Round 8 — Consensus Collapse: 90/90
  - Round 9 — Federated Memory Poisoning: 120/120

### Scoring weight note:
- `s_recovery` has **negative weight** (-0.10) — recovery capability *reduces* risk. This is intentional.
- Component weights sum to 0.95 (without PageRank) or 0.99 (with PageRank). The scoring engine normalizes by `sum(abs(applied_weights))` so `omega_mem_final` is always in [0.0, 100.0].

### When to run tests:
- **pytest**: only when `api/` or `tests/` files change
- **corpus**: only when scoring logic changes
- **NEVER run for**: frontend, docs, SDK, README changes

### Test files (33 files, 2,228+ tests):
- `test_scoring.py` — Core scoring engine (1840+ tests)
- `test_security_audit.py` — Cross-tenant isolation, SSRF, secrets, quota enforcement (27 tests)
- `test_batch3_audit.py` — Weight bounds, determinism, untested modules + endpoints (35 tests)
- `test_new_preflight_fields.py` — days_until_block, confidence_calibration, signal_vector_logged (12 tests)
- `test_heal_roi_knowledge_fleet.py` — heal_roi, knowledge_age_days, fleet_health_distance (11 tests)
- `test_complexity_cost_asymmetry.py` — memory_complexity_trend, decision_cost_asymmetry (10 tests)
- `test_spof_monoculture.py` — single_point_of_failure, monoculture_risk_score (9 tests)
- `test_insights_endpoint.py` — GET /v1/insights endpoint (8 tests)
- `test_api_key_cache.py` — Redis-cached API key validation
- `test_alias_fields.py` — heal_decision and stability_gauge alias fields
- `test_audit_log.py` — Audit log write correctness
- `test_audit_log_fields.py` — Audit log GET response timestamp/omega mapping
- `test_deterministic_seed.py` — Deterministic seeding and hysteresis
- `test_team_and_executive.py` — Key generation and executive summary fields
- `test_approvals_agent_id.py` — Approvals response includes agent_id
- `test_comply_fixes.py` — SIEM omega field and EU AI Act block counts
- `test_proof_and_protocol.py` — Proof-of-decision, court authority, passport TTL, anti-consensus
- `test_stability_and_endpoints.py` — Decision stability, grok comparison, propagation trace
- `test_timestamp_integrity.py` — Round 6: timestamp manipulation detection (17 tests)
- `test_identity_drift.py` — Round 7: authority expansion detection (19 tests)
- `test_consensus_collapse.py` — Round 8: consensus collapse detection (17 tests)
- `test_attack_surface_score.py` — Compound attack surface score (13 tests)
- `test_detection_feedback.py` — Detection-to-scoring feedback loop (8 tests)
- `test_naturalness.py` — Naturalness score: Benford's law for AI memory (12 tests)
- `test_vaccination.py` — Memory vaccination: fleet-wide attack immunity (7 tests)
- `test_provenance_chain.py` — Provenance chain detection, MemCube v3 (13 tests)
- `test_calibration.py` — Automated corpus calibration loop (11 tests)
- `test_failure_patterns.py` — Failure patterns dataset + memory_location field (5 tests)
- `test_new_features.py` — Preflight headers, auto profile, adapt, .sgraal policy, SLA (12 tests)
- `test_compatibility_suite.py` — SDK bridge import verification (10 tests, skips if not installed)
- `test_migrate_policies.py` — Migrate endpoint + policy registry CRUD (5 tests)
- `conftest.py` — Shared test config (sets `SGRAAL_SKIP_DNS_CHECK=1` for webhook URL tests)

### Benchmark corpora:

**Rounds 1-4** (329 cases, `tests/corpus/run_all.py`):
- `sgraal_grok_joint_corpus.jsonl` — 60 cases: freshness, drift, criticality, compliance, healing, security
- `sgraal_grok_sponsored_drift_corpus.jsonl` — 60 cases: sponsored drift, cross-agent propagation, clean baseline, mixed drift
- `sgraal_grok_subtle_drift_corpus.jsonl` — 59 cases: subtle sponsored, buried propagation, adversarial clean, boundary edge
- `sgraal_grok_hallucination_corpus.jsonl` — 60 cases: confident fabrication, multi-hop echo, cross-agent amplification
- `sgraal_grok_propagation_corpus.jsonl` — 90 cases: injection, drift amplification, RAG poisoning, API drift

**Rounds 6-8** (240 cases, individual runners in `tests/corpus/`):
- `round6_memory_time_attack.py` — 60 cases: timestamp zeroing, age collapse, anchor inconsistency
- `round7_identity_drift.py` — 90 cases: lexical softening, delegation chain, tenant binding, time-decay replay
- `round8_consensus_collapse.py` — 90 cases: redundant summarization, confidence recycling, modal uncertainty, cross-role reinforcement

**Round 5** (45 cases, `tests/corpus/`):
- `round5_consensus_poisoning.py` — 45 cases: fabricated historical, cross-stack identity, timestamp-invariant compound

**Round 9 — Federated Memory Poisoning** (120 cases, `tests/corpus/`):
- `round9_federated_poisoning.json` — 120 cases across 4 vectors:
  - Provenance erosion (30): trust eroded across 2-4 federation hops
  - Identity hijack (30): identity attributes morphed across federation sync
  - Consensus bleed (30): minority poisoned subset bleeds into consensus under partial sync
  - Tier-3 rewrites (30): retroactive fact modifications surviving federation without divergence flags
- `scripts/generate_round9_corpus.py` — corpus generator
- `scripts/run_round9_corpus.py` — runner + F1 scoring (F1=1.000, FP=0.0%)
- Detection hardening: PATTERN 5 (federation provenance asymmetry) + PATTERN 5b (federation topic injection) in `_check_consensus_collapse`

**Adversarial compound corpus** (216 cases, `tests/corpus/`):
- `generate_adversarial.py` — generates 3×6×4×3 = 216 compound attack cases combining R6+R7+R8 patterns
- `run_adversarial.py` — runs against live API, reports detection rate by severity (97.2% overall, 100% moderate/severe)
- `adversarial_compound_corpus.jsonl` — generated JSONL corpus

## Deployment

**API** (api.sgraal.com) — Deployed on Railway via `Procfile`, auto-deploys from main:
```
web: PYTHONPATH=/app python3 -m uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 4
```

**Dashboard** (app.sgraal.com) — Deployed on Vercel from `dashboard/`:
```bash
cd dashboard && vercel --prod
```

**Landing page** (sgraal.com) — Deployed on Vercel from `web-static/`:
```bash
cd web-static && vercel --prod
```

## Environment Variables

- `SUPABASE_URL` — Supabase project URL (optional, enables logging)
- `SUPABASE_KEY` — Supabase anon key (optional, enables logging)
- `SUPABASE_SERVICE_KEY` — Supabase service role key (required for signup, bypasses RLS for api_keys inserts)
- `STRIPE_SECRET_KEY` — Stripe secret key (optional, enables billing and signup)
- `UPSTASH_REDIS_URL` — Upstash Redis REST URL (optional, enables Global State Vector)
- `UPSTASH_REDIS_TOKEN` — Upstash Redis auth token (optional, enables GSV)
- `ATTESTATION_SECRET` — **Required in production.** Stable secret for HMAC proof hashes. Must not change across restarts (breaks attestation reproducibility). No fallback default.
- `PASSPORT_SIGNING_KEY_V1` — **Required in production.** Signing key for Memory Passports. No fallback default.
- `UNSUB_HMAC_SECRET` — **Required in production.** HMAC secret for email unsubscribe tokens. No fallback default.
- `SGRAAL_SKIP_DNS_CHECK` — Set to `1` in test environments to skip DNS resolution in webhook URL validation (avoids flaky tests).

## Security Architecture

### Tenant isolation
All per-tenant data is keyed by `_safe_key_hash(key_record)` — a helper that never returns `"default"` or empty string. Test keys get a deterministic SHA-256 derived from the API key. This prevents cross-tenant data leakage across policies, webhooks, SLA configs, alert rules, and all 110+ namespaced storage locations.

### Rate limiting
Quota enforcement uses atomic Redis `INCR` on `quota:{key_hash}:{year_month}` with 35-day TTL. If the incremented count exceeds the tier limit, the counter is decremented back and the request is rejected with 429. Falls back to Supabase `calls_this_month` if Redis is unavailable.

### SSRF protection
All webhook URLs are validated by `_validate_webhook_url()` before storage or dispatch. Blocks: `http://` scheme, private IP ranges (RFC 1918), loopback (127.x, ::1), link-local (169.254.x), cloud metadata (169.254.169.254), `.local`/`.internal`/`.localhost` hostnames. DNS resolution check skippable in tests via `SGRAAL_SKIP_DNS_CHECK=1`.

### Supabase error handling
Critical writes (audit_log, outcome_log, memory_ledger) log errors via `logger.error()` instead of silently swallowing exceptions. The audit_log writer retries up to 3 times with structured error logging on final failure.

### _outcomes thread safety
The in-memory `_outcomes` dict is protected by `_outcomes_lock` (threading.Lock). All reads and writes in `/v1/preflight` and `/v1/outcome` are wrapped. Eviction capped at 10,000 entries.

### Redis TTL policy
All `redis_set` calls must include an explicit TTL. Firewall rules: 7 days. Agent personas: 30 days. Webhook configs: 90 days. API key cache: 5 minutes. No indefinite keys allowed.

## Database Setup

The `api_keys` table migration is at `scripts/create_api_keys_table.sql`. Schema: `id` (uuid), `created_at`, `key_hash` (unique, indexed), `customer_id` (Stripe, indexed), `email`, `tier` (free/starter/growth), `calls_this_month`, `last_used_at`. RLS enabled: users see only their own keys; only service role can insert/delete.

The `outcome_log` table migration is at `scripts/create_outcome_log_table.sql`. Schema: `outcome_id` (uuid), `preflight_id`, `agent_id`, `task_id`, `status` (open/success/failure/partial), `component_attribution` (jsonb), `created_at`, `closed_at`. Service role full access via RLS.

## Authentication

The `/v1/preflight` endpoint requires a Bearer token in the `Authorization` header. API keys are validated in order: (1) in-memory `API_KEYS` dict, (2) Redis cache (`api_key_valid:{hash[:16]}`, TTL 300s), (3) Supabase `api_keys` table SHA-256 hash lookup. Valid keys cached in Redis on first Supabase hit. All key generation endpoints (`/v1/api-keys/generate`, `/v1/signup`, `/v1/auth/register`) prime Redis cache immediately after Supabase insert for instant usability. Cache invalidated on key revocation. Redis failures fall through silently to Supabase. Returns 401 for invalid keys, 403 if the header is missing. Registration emails sent via Resend HTTP API (not SDK).

## API Endpoints

`POST /v1/signup` — accepts `{ "email": "..." }`. Creates a Stripe customer, subscribes to the free tier, generates a secure API key (`sg_live_` prefix), stores the SHA-256 hash in Supabase `api_keys`, and returns the plaintext key once.

`POST /v1/preflight` — requires `Authorization: Bearer <api_key>`. Accepts `memory_state` (list of memory entries with trust/conflict/age metadata), `action_type` (informational/reversible/irreversible/destructive), `domain` (general/customer_support/coding/legal/fintech/medical), and optional `client_gsv` (integer). The Stripe customer ID is resolved automatically from the API key. Returns `omega_mem_final` score, `recommended_action`, `assurance_score`, `component_breakdown`, `repair_plan`, `healing_counter`, `gsv`, and `outcome_id` (uuid for closing via `/v1/outcome`). If `client_gsv` is provided and server GSV < client_gsv, returns `stale_state_warning: STALE_STATE_DETECTED`. GSV increments monotonically via Upstash Redis INCR (falls back to 0 if Redis unavailable).

`POST /v1/heal` — requires `Authorization: Bearer <api_key>`. Accepts `entry_id` (string), `action` (REFETCH/VERIFY_WITH_SOURCE/REBUILD_WORKING_SET), and optional `agent_id`. Increments the per-entry healing counter and returns `healed`, `healing_counter`, `projected_improvement`, `action_taken`, and `timestamp`. Logged to Supabase `memory_ledger`.

`POST /v1/outcome` — requires `Authorization: Bearer <api_key>`. Closes an outcome from a previous preflight call. Accepts `outcome_id`, `status` (success/failure/partial), and `failure_components` (list of β component names for attribution). Returns `outcome_id`, `status`, `closed_at`. Logged to Supabase `outcome_log`. Returns 404 for unknown outcome_id, 409 if already closed.

## Rate Limiting

Monthly call limits enforced per API key via atomic Redis `INCR` on `quota:{key_hash}:{YYYY-MM}` (TTL 35 days). Tier limits: free (10,000), starter (100,000), growth (1,000,000). Returns 429 when exceeded. Falls back to Supabase `calls_this_month` if Redis unavailable. Test/demo keys and `dry_run=True` skip quota enforcement. Supabase `calls_this_month` and `last_used_at` still updated as secondary record.

## Billing

Usage-based billing via Stripe Meters. Every `/v1/preflight` call emits an `omega_mem_preflight` meter event attributed to the request's `stripe_customer_id`. Free tier: first 10,000 calls per customer are free (configured in Stripe pricing).

One-time Stripe setup (creates meter, product, and graduated pricing):
```bash
STRIPE_SECRET_KEY=sk_test_... python scripts/setup_stripe.py
```

## MCP Package

`@sgraal/mcp` — install with `npm install @sgraal/mcp`, publish with `cd mcp && npm publish --access public`.

Build: `cd mcp && npm run build`. Claude Desktop config:
```json
{
  "mcpServers": {
    "sgraal": {
      "command": "npx",
      "args": ["@sgraal/mcp"],
      "env": { "SGRAAL_API_KEY": "sg_live_..." }
    }
  }
}
```
