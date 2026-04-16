variable "api_key" {
  type      = string
  sensitive = true
}

variable "base_url" {
  type    = string
  default = "https://api.sgraal.com"
}

variable "fleet_name" {
  description = "Human-readable fleet identifier"
  type        = string
}

variable "per_domain_overrides" {
  description = "Map of domain -> {warn, ask_user, block} to override defaults. Domains not in the map use defaults."
  type = map(object({
    warn     = optional(number)
    ask_user = optional(number)
    block    = optional(number)
  }))
  default = {}
}
