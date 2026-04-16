"""
Sgraal Kubernetes Operator

Manages SgraalDeployment custom resources by reconciling them into a standard
Kubernetes Deployment + Service pair. Built on top of kopf
(https://kopf.readthedocs.io/) which provides the controller loop, event
watching, finalizers, and owner reference plumbing.

Reconcile pattern
-----------------
The controller pattern is declarative: the user expresses the desired state
(a SgraalDeployment CR) and the operator continuously drives the cluster
toward it. On every CREATE/UPDATE event for a SgraalDeployment, the
`reconcile` handler below:

    1. Reads the spec (replicas, domain, blockThreshold, image, secret refs).
    2. Builds the desired Deployment manifest (with env + envFrom for secrets,
       liveness/readiness probes on /health, port 8000).
    3. Attaches an owner reference via kopf.adopt() so cascade deletion works.
    4. Creates the Deployment, or replaces it if it already exists (409).
    5. Builds and creates the matching ClusterIP Service (port 8000).
    6. Returns a dict that kopf merges into status.{ready, replicas,
       lastSyncTime} via the status subresource.

On DELETE, the ownerReferences placed in step 3/5 trigger Kubernetes
garbage collection of the Deployment and Service automatically, so the
`cleanup` handler only needs to log.

Error handling
--------------
Kubernetes API errors are caught and either handled (409 -> replace) or
re-raised so kopf can retry with exponential backoff. Unexpected errors
never crash the operator - kopf will re-queue the event.
"""

from datetime import datetime, timezone

import kopf
import kubernetes


# Valid domains accepted by the Sgraal scoring engine. Mirrors the CRD
# openAPIV3Schema enum and the API-level validation.
VALID_DOMAINS = {
    "general",
    "customer_support",
    "coding",
    "legal",
    "fintech",
    "medical",
}

DEFAULT_IMAGE = "sgraal-api:latest"
DEFAULT_REPLICAS = 2
DEFAULT_BLOCK_THRESHOLD = 70
CONTAINER_PORT = 8000


def _build_deployment(
    name: str,
    namespace: str,
    replicas: int,
    image: str,
    domain: str,
    block_threshold: int,
    api_key_secret: str,
    redis_url_secret: str,
    supabase_url_secret: str,
) -> dict:
    """Construct the desired Deployment manifest for a SgraalDeployment CR."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app": name, "managed-by": "sgraal-operator"},
        },
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {
                    "labels": {
                        "app": name,
                        "managed-by": "sgraal-operator",
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "sgraal-api",
                            "image": image,
                            "imagePullPolicy": "IfNotPresent",
                            "ports": [
                                {
                                    "name": "http",
                                    "containerPort": CONTAINER_PORT,
                                    "protocol": "TCP",
                                }
                            ],
                            "env": [
                                {"name": "SGRAAL_DOMAIN", "value": domain},
                                {
                                    "name": "SGRAAL_BLOCK_THRESHOLD",
                                    "value": str(block_threshold),
                                },
                            ],
                            "envFrom": [
                                {"secretRef": {"name": api_key_secret}},
                                {"secretRef": {"name": redis_url_secret}},
                                {"secretRef": {"name": supabase_url_secret}},
                            ],
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": CONTAINER_PORT,
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": 15,
                                "timeoutSeconds": 5,
                                "failureThreshold": 3,
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": CONTAINER_PORT,
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5,
                                "timeoutSeconds": 3,
                                "failureThreshold": 3,
                            },
                            "resources": {
                                "requests": {"cpu": "250m", "memory": "512Mi"},
                                "limits": {"cpu": "1000m", "memory": "1Gi"},
                            },
                        }
                    ]
                },
            },
        },
    }


def _build_service(name: str, namespace: str) -> dict:
    """Construct the ClusterIP Service fronting the Sgraal pods."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app": name, "managed-by": "sgraal-operator"},
        },
        "spec": {
            "type": "ClusterIP",
            "selector": {"app": name},
            "ports": [
                {
                    "name": "http",
                    "port": CONTAINER_PORT,
                    "targetPort": CONTAINER_PORT,
                    "protocol": "TCP",
                }
            ],
        },
    }


def _validate_spec(spec: dict) -> None:
    """Fail fast on invalid spec values via PermanentError (no retry)."""
    domain = spec.get("domain", "general")
    if domain not in VALID_DOMAINS:
        raise kopf.PermanentError(
            f"Invalid domain '{domain}'. Must be one of: {sorted(VALID_DOMAINS)}"
        )

    block_threshold = spec.get("blockThreshold", DEFAULT_BLOCK_THRESHOLD)
    if not isinstance(block_threshold, int) or not 0 <= block_threshold <= 100:
        raise kopf.PermanentError(
            f"blockThreshold must be an integer in [0, 100], got {block_threshold!r}"
        )

    replicas = spec.get("replicas", DEFAULT_REPLICAS)
    if not isinstance(replicas, int) or replicas < 1:
        raise kopf.PermanentError(
            f"replicas must be a positive integer, got {replicas!r}"
        )

    for field in ("apiKeySecret", "redisUrlSecret", "supabaseUrlSecret"):
        if not spec.get(field):
            raise kopf.PermanentError(f"spec.{field} is required")


@kopf.on.create("sgraal.com", "v1", "sgraaldeployments")
@kopf.on.update("sgraal.com", "v1", "sgraaldeployments")
def reconcile(spec, name, namespace, logger, **kwargs):
    """Reconcile a SgraalDeployment into a Deployment + Service pair.

    The returned dict is merged into status.* by kopf's default progression
    tracking, yielding observable fields (ready, replicas, lastSyncTime).
    """
    _validate_spec(spec)

    replicas = spec.get("replicas", DEFAULT_REPLICAS)
    domain = spec.get("domain", "general")
    block_threshold = spec.get("blockThreshold", DEFAULT_BLOCK_THRESHOLD)
    image = spec.get("image", DEFAULT_IMAGE)
    api_key_secret = spec["apiKeySecret"]
    redis_url_secret = spec["redisUrlSecret"]
    supabase_url_secret = spec["supabaseUrlSecret"]

    logger.info(
        f"Reconciling SgraalDeployment {namespace}/{name} "
        f"(replicas={replicas}, domain={domain}, image={image})"
    )

    # --- Deployment ----------------------------------------------------------
    dep_body = _build_deployment(
        name=name,
        namespace=namespace,
        replicas=replicas,
        image=image,
        domain=domain,
        block_threshold=block_threshold,
        api_key_secret=api_key_secret,
        redis_url_secret=redis_url_secret,
        supabase_url_secret=supabase_url_secret,
    )
    # kopf.adopt stamps ownerReferences so GC cascades on CR deletion.
    kopf.adopt(dep_body)

    apps = kubernetes.client.AppsV1Api()
    try:
        apps.create_namespaced_deployment(namespace=namespace, body=dep_body)
        logger.info(f"Created Deployment {namespace}/{name}")
    except kubernetes.client.ApiException as e:
        if e.status == 409:
            # Already exists: replace with the desired state.
            try:
                apps.replace_namespaced_deployment(
                    name=name, namespace=namespace, body=dep_body
                )
                logger.info(f"Updated Deployment {namespace}/{name}")
            except kubernetes.client.ApiException as replace_err:
                logger.error(
                    f"Failed to replace Deployment {namespace}/{name}: {replace_err}"
                )
                raise kopf.TemporaryError(
                    f"Deployment replace failed: {replace_err.reason}", delay=30
                )
        else:
            logger.error(
                f"Failed to create Deployment {namespace}/{name}: {e}"
            )
            raise kopf.TemporaryError(
                f"Deployment create failed: {e.reason}", delay=30
            )

    # --- Service -------------------------------------------------------------
    svc_body = _build_service(name=name, namespace=namespace)
    kopf.adopt(svc_body)

    core = kubernetes.client.CoreV1Api()
    try:
        core.create_namespaced_service(namespace=namespace, body=svc_body)
        logger.info(f"Created Service {namespace}/{name}")
    except kubernetes.client.ApiException as e:
        if e.status == 409:
            # Services require a resourceVersion for full replace and the
            # clusterIP is immutable; for an MVP we keep the existing Service
            # rather than risk an invalid patch.
            logger.info(
                f"Service {namespace}/{name} already exists; skipping update"
            )
        else:
            logger.error(
                f"Failed to create Service {namespace}/{name}: {e}"
            )
            raise kopf.TemporaryError(
                f"Service create failed: {e.reason}", delay=30
            )

    return {
        "ready": True,
        "replicas": replicas,
        "lastSyncTime": datetime.now(timezone.utc).isoformat(),
    }


@kopf.on.delete("sgraal.com", "v1", "sgraaldeployments")
def cleanup(name, namespace, logger, **kwargs):
    """Log the deletion. Owner references handle cascade cleanup of children."""
    logger.info(
        f"SgraalDeployment {namespace}/{name} deleted; "
        f"dependent Deployment + Service will be garbage-collected by owner refs."
    )
