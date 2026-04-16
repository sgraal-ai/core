# Sgraal Kubernetes Operator

Declarative management of [Sgraal](https://sgraal.com) API deployments via a
`SgraalDeployment` custom resource. Built on
[kopf](https://kopf.readthedocs.io/) (Kubernetes Operator Pythonic Framework).

## What it does

The operator watches `SgraalDeployment` objects and reconciles them into:

- A standard `apps/v1` **Deployment** running the Sgraal FastAPI image on
  port 8000 (with liveness + readiness probes on `/health`).
- A `ClusterIP` **Service** exposing port 8000 to the rest of the cluster.

Secrets for Supabase, Upstash Redis, and signing keys are projected into the
pod environment via `envFrom: secretRef`. Domain and block threshold from the
CR spec become `SGRAAL_DOMAIN` / `SGRAAL_BLOCK_THRESHOLD` env vars.

Owner references ensure cascade deletion: removing a `SgraalDeployment`
automatically garbage-collects its Deployment and Service.

## Quick start

1. Install the CRD:

   ```bash
   kubectl apply -f manifests/crd.yaml
   ```

2. Install RBAC (creates the `sgraal-system` namespace implicitly via the
   operator manifest; RBAC binds a ClusterRole to the operator
   ServiceAccount):

   ```bash
   kubectl apply -f manifests/operator.yaml  # creates namespace
   kubectl apply -f manifests/rbac.yaml
   ```

3. Build the operator image (load it into your local cluster, e.g.
   `kind load docker-image sgraal-operator:latest`):

   ```bash
   cd k8s/operator
   docker build -t sgraal-operator:latest .
   ```

4. Deploy the operator:

   ```bash
   kubectl apply -f manifests/operator.yaml
   ```

5. Create the secrets consumed by the managed Deployment (one per
   `*Secret` reference in your CR):

   ```bash
   kubectl create secret generic my-api-key-secret \
     --from-literal=ATTESTATION_SECRET=... \
     --from-literal=PASSPORT_SIGNING_KEY_V1=... \
     --from-literal=UNSUB_HMAC_SECRET=...

   kubectl create secret generic my-redis-secret \
     --from-literal=UPSTASH_REDIS_URL=https://...upstash.io \
     --from-literal=UPSTASH_REDIS_TOKEN=...

   kubectl create secret generic my-supabase-secret \
     --from-literal=SUPABASE_URL=https://....supabase.co \
     --from-literal=SUPABASE_SERVICE_KEY=...
   ```

6. Create a `SgraalDeployment`:

   ```yaml
   apiVersion: sgraal.com/v1
   kind: SgraalDeployment
   metadata:
     name: my-sgraal
   spec:
     replicas: 2
     apiKeySecret: my-api-key-secret
     redisUrlSecret: my-redis-secret
     supabaseUrlSecret: my-supabase-secret
     domain: fintech
     blockThreshold: 70
     image: sgraal-api:latest
   ```

   Apply it:

   ```bash
   kubectl apply -f my-sgraal.yaml
   kubectl get sgraaldeployments
   kubectl get deploy,svc -l managed-by=sgraal-operator
   ```

## CR field reference

| Field                     | Type    | Default            | Notes                                                                         |
| ------------------------- | ------- | ------------------ | ----------------------------------------------------------------------------- |
| `spec.replicas`           | int     | `2`                | Number of Sgraal API pods (1-100).                                            |
| `spec.apiKeySecret`       | string  | (required)         | Secret with `ATTESTATION_SECRET`, `PASSPORT_SIGNING_KEY_V1`, `UNSUB_HMAC_SECRET`. |
| `spec.redisUrlSecret`     | string  | (required)         | Secret with `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`.                       |
| `spec.supabaseUrlSecret`  | string  | (required)         | Secret with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`.                           |
| `spec.domain`             | enum    | `general`          | One of: `general`, `customer_support`, `coding`, `legal`, `fintech`, `medical`. |
| `spec.blockThreshold`     | int     | `70`               | Omega score threshold (0-100) above which preflight returns BLOCK.            |
| `spec.image`              | string  | `sgraal-api:latest`| Container image for the Sgraal API.                                           |
| `status.ready`            | bool    | (set by operator)  | True after a successful reconcile.                                            |
| `status.replicas`         | int     | (set by operator)  | Reconciled replica count.                                                     |
| `status.lastSyncTime`     | string  | (set by operator)  | ISO-8601 timestamp of the last successful reconcile.                          |

## Troubleshooting

Check operator logs:

```bash
kubectl logs -n sgraal-system deployment/sgraal-operator -f
```

Inspect a specific CR and its managed resources:

```bash
kubectl describe sgraaldeployment my-sgraal
kubectl get deploy my-sgraal -o yaml
kubectl get svc my-sgraal -o yaml
```

Common issues:

- **CR stuck with `ready: false`** - The operator likely cannot create the
  Deployment. `kubectl describe sgraaldeployment <name>` shows kopf events
  including the API error reason.
- **Pods CrashLoopBackOff** - The referenced secrets do not exist or are
  missing required keys. `kubectl describe pod <name>` shows the missing
  env var.
- **Image pull error** - The `image` field points to a registry the cluster
  cannot reach, or the image is not loaded in a local kind/minikube
  cluster.

## File layout

```
k8s/operator/
├── Dockerfile              # kopf + kubernetes client runtime
├── operator.py             # reconcile + cleanup handlers
├── manifests/
│   ├── crd.yaml            # SgraalDeployment CustomResourceDefinition
│   ├── rbac.yaml           # ServiceAccount + ClusterRole + ClusterRoleBinding
│   └── operator.yaml       # Namespace + Deployment running the operator
└── README.md               # this file
```
