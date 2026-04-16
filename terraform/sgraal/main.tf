terraform {
  required_version = ">= 1.3.0"
  required_providers {
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }
}

# Default base URL — override via variable for self-hosted deployments
locals {
  base_url = var.base_url
  headers  = {
    Authorization = "Bearer ${var.api_key}"
    Content-Type  = "application/json"
  }
}

# Health check data source — verifies the Sgraal API is reachable
data "http" "health" {
  url = "${local.base_url}/health"
}

# Capabilities discovery — fetches /.well-known/sgraal.json
data "http" "capabilities" {
  url = "${local.base_url}/.well-known/sgraal.json"
}
