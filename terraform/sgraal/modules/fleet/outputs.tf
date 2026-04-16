output "fleet_name" {
  value = var.fleet_name
}

output "effective_thresholds" {
  description = "Final thresholds applied per domain (defaults merged with overrides)"
  value       = local.effective_thresholds
}

output "domains_configured" {
  value = keys(local.effective_thresholds)
}
