pub mod types;

use types::*;

pub struct SgraalClient {
    api_key: String,
    base_url: String,
    client: reqwest::Client,
}

impl SgraalClient {
    pub fn new(api_key: &str) -> Self {
        Self {
            api_key: api_key.to_string(),
            base_url: "https://api.sgraal.com".to_string(),
            client: reqwest::Client::new(),
        }
    }

    pub async fn preflight(&self, req: PreflightRequest) -> Result<PreflightResponse, reqwest::Error> {
        let resp = self.client
            .post(format!("{}/v1/preflight", self.base_url))
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&req)
            .send()
            .await?
            .json::<PreflightResponse>()
            .await?;
        Ok(resp)
    }

    pub async fn governance_score(&self) -> Result<GovernanceScoreResponse, reqwest::Error> {
        let resp = self.client
            .get(format!("{}/v1/governance-score", self.base_url))
            .header("Authorization", format!("Bearer {}", self.api_key))
            .send()
            .await?
            .json::<GovernanceScoreResponse>()
            .await?;
        Ok(resp)
    }
}
