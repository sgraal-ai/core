# KEYS.md — Cryptographic Secrets That Must Never Be Rotated Without Migration

This document describes three environment variables that **persist cryptographic state across deploys**. Changing any of them invalidates every credential, passport, or token signed with the old value. There is no automatic migration — if the key changes, every previously-issued artifact becomes permanently unverifiable.

---

## The three keys

| Variable | Purpose | What breaks if it changes |
|----------|---------|--------------------------|
| `ATTESTATION_SECRET` | HMAC-SHA256 proof hashes for proof-of-decision attestations and W3C Verifiable Credentials (`POST /v1/certify`) | Every previously-issued `SgraalProof2026` VC fails `POST /v1/certify/verify`. Customers who stored credentials as compliance evidence can no longer verify them. |
| `PASSPORT_SIGNING_KEY_V1` | Signing key for Memory Passports (proof that an agent's memory passed governance at a point in time) | Every previously-issued passport fails signature verification. Audit trails referencing passports become unverifiable. |
| `UNSUB_HMAC_SECRET` | HMAC for email unsubscribe tokens (one-click unsubscribe links in transactional emails) | Every unsubscribe link in every email already sent stops working. Users clicking "unsubscribe" get an error. Potential CAN-SPAM / GDPR violation. |

## Requirements

1. **Minimum length: 32 characters.** The startup check warns if any key is shorter. Use `openssl rand -hex 32` (produces 64 hex chars = 256 bits) for strong keys.

2. **Must persist across deploys.** These are NOT ephemeral session secrets. They sign long-lived artifacts that customers store, audit, and verify weeks or months later.

3. **Must be identical across all workers.** In a multi-replica deployment (Helm chart default: 2 replicas, HPA up to 10), every worker must use the same key. A credential issued by worker A must be verifiable by worker B.

4. **Must NOT be auto-generated at startup.** If your deployment platform generates a random value on each deploy (some PaaS platforms do this for unset env vars), every deploy rotates the key. Set them explicitly and permanently.

## How to set on Railway

```bash
# Generate strong keys (run once, save the output permanently)
ATTESTATION_SECRET=$(openssl rand -hex 32)
PASSPORT_SIGNING_KEY_V1=$(openssl rand -hex 32)
UNSUB_HMAC_SECRET=$(openssl rand -hex 32)

# Set on Railway (these persist across deploys by default)
railway variables set ATTESTATION_SECRET=$ATTESTATION_SECRET
railway variables set PASSPORT_SIGNING_KEY_V1=$PASSPORT_SIGNING_KEY_V1
railway variables set UNSUB_HMAC_SECRET=$UNSUB_HMAC_SECRET
```

Railway stores environment variables in its project settings, not in the Dockerfile or Procfile. They persist across deploys unless explicitly changed by the operator.

## How to set with Docker

```bash
docker run -e ATTESTATION_SECRET=<value> \
           -e PASSPORT_SIGNING_KEY_V1=<value> \
           -e UNSUB_HMAC_SECRET=<value> \
           sgraal-api:latest
```

Or via `docker-compose.yml`:
```yaml
services:
  api:
    environment:
      ATTESTATION_SECRET: ${ATTESTATION_SECRET}
      PASSPORT_SIGNING_KEY_V1: ${PASSPORT_SIGNING_KEY_V1}
      UNSUB_HMAC_SECRET: ${UNSUB_HMAC_SECRET}
```

Store the actual values in a `.env` file that is NOT committed to git.

## How to set with Helm

```bash
helm install sgraal ./charts/sgraal \
  --set secrets.attestationSecret=$(openssl rand -hex 32) \
  --set secrets.passportSigningKey=$(openssl rand -hex 32) \
  --set secrets.unsubHmacSecret=$(openssl rand -hex 32)
```

Or use a Kubernetes Secret pre-created by your secrets manager (Vault, AWS Secrets Manager, etc.).

## Key rotation procedure (if you MUST rotate)

If a key is compromised and must be rotated:

1. **Before rotating:** export all currently-valid credentials/passports/tokens that were signed with the old key. There is no API for this yet — it requires a Supabase query.

2. **Set the new key** on the deployment platform.

3. **Re-issue** all affected artifacts:
   - For `ATTESTATION_SECRET`: every W3C VC must be re-issued via `POST /v1/certify` with the original memory state. Customers must update their stored credentials.
   - For `PASSPORT_SIGNING_KEY_V1`: every passport must be re-issued. Audit references must be updated.
   - For `UNSUB_HMAC_SECRET`: every email with an unsubscribe link must be re-sent. In practice, old emails' unsubscribe links will just fail.

4. **There is no dual-key / grace-period mechanism.** The old key is dead immediately. A future enhancement could support key versioning (e.g., `PASSPORT_SIGNING_KEY_V2` + fallback to V1 during migration), but this is not implemented.

## Startup behavior

At startup, `api/main.py` calls `_validate_required_secrets()`:

- **Missing key** (empty or unset): `logger.warning("Missing required secrets: ...")`. The API starts with insecure defaults (empty string or `"dev_cert_secret"` fallback). Acceptable for local development; unacceptable for production.

- **Weak key** (set but shorter than 32 characters): `logger.warning("Weak secrets detected: ...")`. Suggests auto-generated placeholder, copy-paste error, or weak value like `"changeme"`.

- **Production + test mode**: `ENV=production` AND `SGRAAL_TEST_MODE=1` → `RuntimeError` at import time. The API refuses to start. (This is a separate guard unrelated to key strength, but it runs in the same startup sequence.)

## SGRAAL_SKIP_DNS_CHECK

This variable disables DNS resolution checks in webhook URL validation. When enabled, webhooks can target internal/private IP addresses (RFC 1918, loopback, link-local).

**Default:** not set (SSRF protection active).

**When to set:** only in test environments where webhook URLs point to localhost services, or in production deployments where webhook endpoints are intentionally behind a VPN and cannot resolve via public DNS.

**Risk if set in production:** an attacker who controls webhook configuration can aim webhooks at internal services (cloud metadata endpoint at 169.254.169.254, internal APIs, etc.). A startup warning fires if `ENV=production` and this is enabled.
