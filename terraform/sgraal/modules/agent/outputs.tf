output "agent_id" {
  description = "Agent identifier (currently: the agent_name)"
  value       = var.agent_name
}

output "thresholds" {
  description = "Configured decision thresholds"
  value = {
    warn     = var.warn_threshold
    ask_user = var.ask_threshold
    block    = var.block_threshold
  }
}

output "domain" {
  value = var.domain
}

output "current_config" {
  description = "Current thresholds read back from the API"
  value       = try(jsondecode(data.http.current_thresholds.response_body), {})
}
