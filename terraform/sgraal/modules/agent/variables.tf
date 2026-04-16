variable "api_key" {
  type      = string
  sensitive = true
}

variable "base_url" {
  type    = string
  default = "https://api.sgraal.com"
}

variable "agent_name" {
  description = "Human-readable agent identifier (used in logs/dashboard)"
  type        = string
}

variable "domain" {
  description = "Sgraal domain — one of general, customer_support, coding, legal, fintech, medical"
  type        = string

  validation {
    condition     = contains(["general", "customer_support", "coding", "legal", "fintech", "medical"], var.domain)
    error_message = "domain must be one of: general, customer_support, coding, legal, fintech, medical"
  }
}

variable "warn_threshold" {
  description = "Omega threshold above which preflight returns WARN"
  type        = number
  default     = 25

  validation {
    condition     = var.warn_threshold >= 0 && var.warn_threshold <= 100
    error_message = "warn_threshold must be between 0 and 100"
  }
}

variable "ask_threshold" {
  description = "Omega threshold above which preflight returns ASK_USER"
  type        = number
  default     = 45

  validation {
    condition     = var.ask_threshold >= 0 && var.ask_threshold <= 100
    error_message = "ask_threshold must be between 0 and 100"
  }
}

variable "block_threshold" {
  description = "Omega threshold above which preflight returns BLOCK"
  type        = number
  default     = 70

  validation {
    condition     = var.block_threshold >= 0 && var.block_threshold <= 100
    error_message = "block_threshold must be between 0 and 100"
  }
}
