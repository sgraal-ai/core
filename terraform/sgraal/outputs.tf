output "base_url" {
  description = "The Sgraal API base URL being used"
  value       = var.base_url
}

output "health_status" {
  description = "Health check response from the Sgraal API"
  value       = jsondecode(data.http.health.response_body)
}

output "api_version" {
  description = "API version reported by /.well-known/sgraal.json"
  value       = try(jsondecode(data.http.capabilities.response_body).api_version, null)
}

output "capabilities" {
  description = "Sgraal capabilities reported by the API"
  value       = try(jsondecode(data.http.capabilities.response_body).capabilities, [])
}
