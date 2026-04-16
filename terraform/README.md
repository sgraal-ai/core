# Sgraal Terraform Provider

Terraform skeleton for managing Sgraal fleets, agents, and per-domain decision thresholds declaratively.

## Architecture

This skeleton uses the native Terraform `http` provider to call the Sgraal REST API. For a full Go-based provider with CRUD lifecycle management, see the roadmap in `/docs/competitive/`.

## Quick start

```hcl
terraform {
  required_version = ">= 1.3.0"
  required_providers {
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }
}

variable "sgraal_api_key" {
  sensitive = true
}

module "fintech_agent" {
  source          = "./modules/agent"
  api_key         = var.sgraal_api_key
  agent_name      = "fintech-treasury"
  domain          = "fintech"
  warn_threshold  = 30
  ask_threshold   = 50
  block_threshold = 70
}

output "agent_id" {
  value = module.fintech_agent.agent_id
}
```

## Modules

### `modules/agent`
Manages a single agent's configuration — domain-specific thresholds, policy bindings.

### `modules/fleet`
Manages fleet-level configuration — global thresholds, webhooks, shared policies.

## Limitations

This is a skeleton — it uses HTTP provider for read/write operations. Not all CRUD semantics are perfectly declarative (e.g., re-running `terraform apply` will re-POST thresholds, which is idempotent on the Sgraal side).

For full custom-resource lifecycle with drift detection and state-aware updates, a native Go Terraform provider (to be released) is recommended.

## Security

- `api_key` is marked `sensitive = true` — do not commit variable files containing it.
- Use `TF_VAR_sgraal_api_key` environment variable or a secure backend (Vault, AWS SM, etc.).
