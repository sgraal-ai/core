variable "api_key" {
  description = "Sgraal API key (sg_live_... or sg_test_...)"
  type        = string
  sensitive   = true
}

variable "base_url" {
  description = "Sgraal API base URL. Use https://api.sgraal.com for SaaS, or a custom URL for self-hosted deployments."
  type        = string
  default     = "https://api.sgraal.com"
}
