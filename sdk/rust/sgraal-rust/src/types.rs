use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub id: String,
    pub content: String,
    #[serde(rename = "type")]
    pub entry_type: String,
    pub timestamp_age_days: f64,
    pub source_trust: f64,
    pub source_conflict: f64,
    pub downstream_count: i32,
}

#[derive(Debug, Serialize)]
pub struct PreflightRequest {
    pub memory_state: Vec<MemoryEntry>,
    pub domain: String,
    pub action_type: String,
}

#[derive(Debug, Deserialize)]
pub struct PreflightResponse {
    pub recommended_action: String,
    pub omega_mem_final: f64,
    pub attack_surface_level: Option<String>,
    pub request_id: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct GovernanceScoreResponse {
    pub governance_score: Option<f64>,
    pub total_governed_actions: i32,
}
