terraform {
  required_providers {
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }
}

locals {
  headers = {
    Authorization = "Bearer ${var.api_key}"
    Content-Type  = "application/json"
  }
}

# POST thresholds to the Sgraal API
data "http" "set_thresholds" {
  url    = "${var.base_url}/v1/config/thresholds"
  method = "POST"

  request_headers = local.headers

  request_body = jsonencode({
    domain   = var.domain
    warn     = var.warn_threshold
    ask_user = var.ask_threshold
    block    = var.block_threshold
  })

  lifecycle {
    postcondition {
      condition     = contains([200, 201], self.status_code)
      error_message = "Failed to set thresholds: HTTP ${self.status_code} - ${self.response_body}"
    }
  }
}

# Read back the current thresholds to verify
data "http" "current_thresholds" {
  url = "${var.base_url}/v1/config/thresholds?domain=${var.domain}"

  request_headers = {
    Authorization = "Bearer ${var.api_key}"
  }

  depends_on = [data.http.set_thresholds]
}
