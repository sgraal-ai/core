terraform {
  required_providers {
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }
}

locals {
  default_thresholds = {
    general          = { warn = 25, ask_user = 45, block = 70 }
    customer_support = { warn = 25, ask_user = 45, block = 70 }
    coding           = { warn = 30, ask_user = 50, block = 75 }
    legal            = { warn = 20, ask_user = 40, block = 60 }
    fintech          = { warn = 20, ask_user = 40, block = 60 }
    medical          = { warn = 15, ask_user = 35, block = 55 }
  }

  # Merge user overrides with defaults
  effective_thresholds = {
    for d, t in local.default_thresholds : d => merge(t, lookup(var.per_domain_overrides, d, {}))
  }
}

# Apply thresholds to each domain
data "http" "set_thresholds" {
  for_each = local.effective_thresholds

  url    = "${var.base_url}/v1/config/thresholds"
  method = "POST"

  request_headers = {
    Authorization = "Bearer ${var.api_key}"
    Content-Type  = "application/json"
  }

  request_body = jsonencode({
    domain   = each.key
    warn     = each.value.warn
    ask_user = each.value.ask_user
    block    = each.value.block
  })

  lifecycle {
    postcondition {
      condition     = contains([200, 201], self.status_code)
      error_message = "Failed to set thresholds for ${each.key}: HTTP ${self.status_code}"
    }
  }
}
