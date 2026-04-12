package sgraal

// MemoryEntry represents a single memory entry in MemCube format.
type MemoryEntry struct {
	ID               string   `json:"id"`
	Content          string   `json:"content"`
	Type             string   `json:"type"`
	TimestampAgeDays float64  `json:"timestamp_age_days"`
	SourceTrust      float64  `json:"source_trust"`
	SourceConflict   float64  `json:"source_conflict"`
	DownstreamCount  int      `json:"downstream_count"`
	ProvenanceChain  []string `json:"provenance_chain,omitempty"`
}

// PreflightRequest is the input for a preflight call.
type PreflightRequest struct {
	MemoryState []MemoryEntry `json:"memory_state"`
	Domain      string        `json:"domain"`
	ActionType  string        `json:"action_type"`
}

// PreflightResponse is the output of a preflight call.
type PreflightResponse struct {
	RecommendedAction string             `json:"recommended_action"`
	OmegaMemFinal     float64            `json:"omega_mem_final"`
	AttackSurfaceLevel string            `json:"attack_surface_level"`
	TimestampIntegrity string            `json:"timestamp_integrity"`
	IdentityDrift      string            `json:"identity_drift"`
	ConsensusCollapse  string            `json:"consensus_collapse"`
	NaturalnessLevel   string            `json:"naturalness_level"`
	ProofSignature     string            `json:"proof_signature"`
	RequestID          string            `json:"request_id"`
	ScoringSkipped     bool              `json:"scoring_skipped"`
}

// GovernanceScoreResponse is the output of the governance score endpoint.
type GovernanceScoreResponse struct {
	GovernanceScore      *float64          `json:"governance_score"`
	TotalGovernedActions int               `json:"total_governed_actions"`
	Message              string            `json:"message,omitempty"`
}
