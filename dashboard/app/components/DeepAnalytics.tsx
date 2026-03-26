"use client";
import { CollapsibleSection, KV } from "./CollapsibleSection";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function DeepAnalytics({ data }: { data: Record<string, any> }) {
  if (!data) return null;

  return (
    <div>
      {/* Stochastic Processes */}
      <CollapsibleSection title="Stochastic Processes" badge={data.ornstein_uhlenbeck ? "OU" : undefined}>
        {data.ornstein_uhlenbeck && <>
          <p className="text-xs text-muted mb-2 mt-2">Ornstein-Uhlenbeck</p>
          <KV label="mean_reverting" value={data.ornstein_uhlenbeck.mean_reverting} />
          <KV label="half_life" value={data.ornstein_uhlenbeck.half_life} />
          <KV label="expected_value_5" value={data.ornstein_uhlenbeck.expected_value_5} />
          <KV label="equilibrium" value={data.ornstein_uhlenbeck.equilibrium} />
        </>}
        {data.jump_diffusion && <>
          <p className="text-xs text-muted mb-2 mt-3">Jump-Diffusion</p>
          <KV label="jump_detected" value={data.jump_diffusion.jump_detected} />
          <KV label="flash_crash_risk" value={data.jump_diffusion.flash_crash_risk} />
          <KV label="jump_rate_lambda" value={data.jump_diffusion.jump_rate_lambda} />
        </>}
        {data.levy_flight && <>
          <p className="text-xs text-muted mb-2 mt-3">Levy Flight</p>
          <KV label="alpha" value={data.levy_flight.alpha} />
          <KV label="tail_index" value={data.levy_flight.tail_index} />
          <KV label="heavy_tail_risk" value={data.levy_flight.heavy_tail_risk} />
        </>}
        {data.hmm_regime && <>
          <p className="text-xs text-muted mb-2 mt-3">HMM Regime</p>
          <KV label="current_state" value={data.hmm_regime.current_state} />
          <KV label="state_probability" value={data.hmm_regime.state_probability} />
        </>}
        {data.particle_filter && <>
          <p className="text-xs text-muted mb-2 mt-3">Particle Filter</p>
          <KV label="state_estimate" value={data.particle_filter.state_estimate} />
          <KV label="uncertainty" value={data.particle_filter.uncertainty} />
        </>}
        {!data.ornstein_uhlenbeck && !data.jump_diffusion && !data.levy_flight && !data.hmm_regime && !data.particle_filter && <p className="text-xs text-muted mt-2">No stochastic data available (requires score_history)</p>}
      </CollapsibleSection>

      {/* Information Theory */}
      <CollapsibleSection title="Information Theory" badge={data.free_energy ? "FE" : undefined}>
        {data.free_energy && <>
          <p className="text-xs text-muted mb-2 mt-2">Free Energy</p>
          <KV label="F" value={data.free_energy.F} />
          <KV label="surprise" value={data.free_energy.surprise} />
        </>}
        {data.mutual_information && <>
          <p className="text-xs text-muted mb-2 mt-3">Mutual Information</p>
          <KV label="nmi_score" value={data.mutual_information.nmi_score} />
          <KV label="encoding_efficiency" value={data.mutual_information.encoding_efficiency} />
        </>}
        {data.info_thermodynamics && <>
          <p className="text-xs text-muted mb-2 mt-3">Info Thermodynamics</p>
          <KV label="transfer_entropy" value={data.info_thermodynamics.transfer_entropy} />
          <KV label="entropy_production" value={data.info_thermodynamics.entropy_production} />
          <KV label="reversibility" value={data.info_thermodynamics.reversibility} />
        </>}
        {data.ergodicity && <>
          <p className="text-xs text-muted mb-2 mt-3">Ergodicity</p>
          <KV label="delta" value={data.ergodicity.delta} />
          <KV label="ergodic" value={data.ergodicity.ergodic} />
        </>}
      </CollapsibleSection>

      {/* Topology */}
      <CollapsibleSection title="Topology" badge={data.persistent_homology?.structural_drift ? "drift" : undefined}>
        {data.persistent_homology && <>
          <p className="text-xs text-muted mb-2 mt-2">Persistent Homology</p>
          <KV label="structural_drift" value={data.persistent_homology.structural_drift} />
          <KV label="topology_summary" value={data.persistent_homology.topology_summary} />
        </>}
        {data.ricci_curvature && <>
          <p className="text-xs text-muted mb-2 mt-3">Ricci Curvature</p>
          <KV label="mean_curvature" value={data.ricci_curvature.mean_curvature} />
          <KV label="graph_health" value={data.ricci_curvature.graph_health} />
        </>}
        {data.homology_torsion && <>
          <p className="text-xs text-muted mb-2 mt-3">Homology Torsion</p>
          <KV label="torsion_detected" value={data.homology_torsion.torsion_detected} />
          <KV label="hallucination_risk" value={data.homology_torsion.hallucination_risk} />
        </>}
        {data.persistence_landscape && <>
          <p className="text-xs text-muted mb-2 mt-3">Persistence Landscape</p>
          <KV label="landscape_norm" value={data.persistence_landscape.landscape_norm} />
        </>}
        {data.topological_entropy && <>
          <p className="text-xs text-muted mb-2 mt-3">Topological Entropy</p>
          <KV label="entropy_estimate" value={data.topological_entropy.entropy_estimate} />
          <KV label="complexity_class" value={data.topological_entropy.complexity_class} />
        </>}
      </CollapsibleSection>

      {/* Optimization */}
      <CollapsibleSection title="Optimization" badge={data.unified_loss ? `L=${data.unified_loss.L_v4}` : undefined}>
        {data.unified_loss && <>
          <p className="text-xs text-muted mb-2 mt-2">Unified Loss L_v4</p>
          <KV label="L_v4" value={data.unified_loss.L_v4} />
          <KV label="dominant_loss" value={data.unified_loss.dominant_loss} />
        </>}
        {data.policy_gradient && <>
          <p className="text-xs text-muted mb-2 mt-3">Policy Gradient</p>
          <KV label="exploration_mode" value={data.policy_gradient.exploration_mode} />
          <KV label="temperature" value={data.policy_gradient.temperature} />
        </>}
        {data.simulated_annealing && <>
          <p className="text-xs text-muted mb-2 mt-3">Simulated Annealing</p>
          <KV label="sa_active" value={data.simulated_annealing.sa_active} />
          <KV label="current_temperature" value={data.simulated_annealing.current_temperature} />
        </>}
        {data.lqr_control && <>
          <p className="text-xs text-muted mb-2 mt-3">LQR Control</p>
          <KV label="optimal_control" value={data.lqr_control.optimal_control} />
          <KV label="control_effort" value={data.lqr_control.control_effort} />
        </>}
        {data.mdp_recommendation && <>
          <p className="text-xs text-muted mb-2 mt-3">MDP Recommendation</p>
          <KV label="optimal_action" value={data.mdp_recommendation.optimal_action} />
          <KV label="state" value={data.mdp_recommendation.state} />
        </>}
      </CollapsibleSection>

      {/* Drift & Trend */}
      <CollapsibleSection title="Drift & Trend" badge={data.drift_details ? `${data.drift_details.drift_method}` : undefined}>
        {data.drift_details && <>
          <p className="text-xs text-muted mb-2 mt-2">Drift Details</p>
          <KV label="ensemble_score" value={data.drift_details.ensemble_score} />
          <KV label="drift_method" value={data.drift_details.drift_method} />
          {data.drift_details.mmd && <KV label="mmd_score" value={data.drift_details.mmd.score} />}
        </>}
        {data.trend_detection && <>
          <p className="text-xs text-muted mb-2 mt-3">Trend Detection</p>
          <KV label="cusum_alert" value={data.trend_detection.cusum_alert} />
          <KV label="ewma_alert" value={data.trend_detection.ewma_alert} />
          <KV label="drift_sustained" value={data.trend_detection.drift_sustained} />
          {data.trend_detection.page_hinkley && <KV label="ph_alert" value={data.trend_detection.page_hinkley.alert} />}
          {data.trend_detection.bocpd && <KV label="regime_change" value={data.trend_detection.bocpd.regime_change} />}
        </>}
        {data.shapley_values && <>
          <p className="text-xs text-muted mb-2 mt-3">Shapley Values (top 3)</p>
          {Object.entries(data.shapley_values as Record<string, number>).sort(([,a],[,b]) => Math.abs(b) - Math.abs(a)).slice(0, 3).map(([k, v]) => (
            <KV key={k} label={k} value={v} />
          ))}
        </>}
      </CollapsibleSection>

      {/* Security & Integrity */}
      <CollapsibleSection title="Security & Integrity" badge={data.sparse_merkle?.integrity_verified ? "verified" : undefined}>
        {data.zk_sheaf_proof && <>
          <p className="text-xs text-muted mb-2 mt-2">ZK Sheaf Proof</p>
          <KV label="proof_valid" value={data.zk_sheaf_proof.proof_valid} />
          <KV label="n_edges_verified" value={data.zk_sheaf_proof.n_edges_verified} />
        </>}
        {data.sparse_merkle && <>
          <p className="text-xs text-muted mb-2 mt-3">Sparse Merkle Tree</p>
          <KV label="integrity_verified" value={data.sparse_merkle.integrity_verified} />
          <KV label="tamper_detected" value={data.sparse_merkle.tamper_detected} />
        </>}
        {data.security_transfer_entropy && <>
          <p className="text-xs text-muted mb-2 mt-3">Security Transfer Entropy</p>
          <KV label="leakage_detected" value={data.security_transfer_entropy.leakage_detected} />
          <KV label="risk_level" value={data.security_transfer_entropy.risk_level} />
        </>}
        {data.dirichlet_process && <>
          <p className="text-xs text-muted mb-2 mt-3">Dirichlet Process</p>
          <KV label="n_clusters" value={data.dirichlet_process.n_clusters} />
          <KV label="new_cluster_detected" value={data.dirichlet_process.new_cluster_detected} />
        </>}
      </CollapsibleSection>

      {/* Calibration & Learning */}
      <CollapsibleSection title="Calibration & Learning" badge={data.stability_score ? `SS=${data.stability_score.score}` : undefined}>
        {data.calibration && <>
          <p className="text-xs text-muted mb-2 mt-2">Calibration</p>
          <KV label="brier_score" value={data.calibration.brier_score} />
          <KV label="log_loss" value={data.calibration.log_loss} />
          <KV label="meta_score" value={data.calibration.meta_score} />
        </>}
        {data.recursive_colimit && <>
          <p className="text-xs text-muted mb-2 mt-3">Recursive Colimit</p>
          <KV label="global_state" value={data.recursive_colimit.global_state} />
          <KV label="colimit_stable" value={data.recursive_colimit.colimit_stable} />
        </>}
        {data.fisher_rao && <>
          <p className="text-xs text-muted mb-2 mt-3">Fisher-Rao</p>
          <KV label="geometry" value={data.fisher_rao.geometry} />
          <KV label="condition_number" value={data.fisher_rao.condition_number} />
        </>}
        {data.stability_score && <>
          <p className="text-xs text-muted mb-2 mt-3">Stability Score</p>
          <KV label="score" value={data.stability_score.score} />
          <KV label="interpretation" value={data.stability_score.interpretation} />
          <KV label="component_count" value={data.stability_score.component_count} />
        </>}
        <KV label="r_total_normalized" value={data.r_total_normalized} />
      </CollapsibleSection>
    </div>
  );
}
