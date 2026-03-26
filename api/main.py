from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Literal, Optional
import sys, os, math
import secrets
import hashlib
import hmac as _hmac
import json as _json
import threading
import uuid
from datetime import datetime, timezone
import stripe
import requests as http_requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring_engine import compute, MemoryEntry, PreflightResult, compute_importance, compute_importance_with_voi, ClientOptimizer, ComplianceEngine, ComplianceProfile, HealingPolicyMatrix, PolicyVerifier, KalmanForecaster, MemoryDependencyGraph, MemoryAccessTracker, ObfuscatedId, ReasonAbstractor, ZKAssurance, ThreadManager, compute_shapley_values, compute_lyapunov, LaplaceMechanism, compute_drift_metrics, detect_trend, compute_calibration, hawkes_from_entries, compute_copula, compute_mewma, compute_sheaf_consistency, get_rl_adjustment, update_from_outcome, compute_bocpd, compute_rmt, compute_causal_graph, compute_spectral, compute_consolidation, compute_jump_diffusion, compute_hmm_regime, compute_zk_sheaf_proof, compute_ou_process, compute_free_energy, compute_levy_flight, compute_rate_distortion, compute_r_total, compute_stability_score, compute_unified_loss, geodesic_update, compute_policy_gradient, decay_temperature, compute_info_thermodynamics, compute_mahalanobis, compute_page_hinkley, compute_provenance_entropy, compute_subjective_logic, compute_frechet, compute_mutual_information, compute_mdp, compute_mttr, compute_ctl_verification, compute_lyapunov_exponent, compute_banach, compute_hotelling_t2, compute_fisher_rao, compute_geodesic_flow, compute_koopman, compute_ergodicity, compute_extended_freshness, compute_persistent_homology, compute_ricci_curvature, compute_recursive_colimit, compute_cohomological_gradient, compute_cox_hazard, compute_arrhenius, compute_owa, compute_poisson_recall, compute_roc_auc

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        pass

supabase_service_client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        from supabase import create_client as _create_client
        supabase_service_client = _create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception:
        pass

def _increment_gsv() -> int:
    """Increment Global State Vector via Upstash Redis INCR. Returns 0 if unavailable."""
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return 0
    try:
        resp = http_requests.post(
            f"{UPSTASH_REDIS_URL}/INCR/sgraal:gsv",
            headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
            timeout=2,
        )
        if resp.ok:
            return resp.json().get("result", 0)
    except Exception:
        pass
    return 0


app = FastAPI(
    title="Sgraal API",
    version="0.1.0",
    servers=[{"url": "https://api.sgraal.com"}],
    description="Memory governance protocol for AI agents. Quickstart: /docs/quickstart | Compliance: /v1/compliance/docs | Batch scoring: up to 100 entries per call, <10ms p95.",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory API key store: api_key -> stripe_customer_id
API_KEYS: dict[str, str] = {
    "sg_test_key_001": "cus_test_001",
}

bearer_scheme = HTTPBearer()


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Validate Bearer token and return the key record with tier/usage info."""
    api_key = credentials.credentials

    # Check in-memory store first (test keys skip rate limiting)
    if api_key in API_KEYS:
        return {"customer_id": API_KEYS[api_key], "tier": "free", "calls_this_month": 0, "key_hash": None}

    # Fall back to Supabase hash lookup
    if supabase_service_client:
        key_hash = _hash_key(api_key)
        result = (
            supabase_service_client.table("api_keys")
            .select("key_hash, customer_id, tier, calls_this_month")
            .eq("key_hash", key_hash)
            .execute()
        )
        if result.data:
            return result.data[0]

    raise HTTPException(status_code=401, detail="Invalid API key")

class MemoryEntryRequest(BaseModel):
    id: str
    content: str
    type: str
    timestamp_age_days: float
    source_trust: float = 0.9
    source_conflict: Optional[float] = None  # None = auto-compute via sheaf cohomology
    downstream_count: int = 1
    r_belief: float = 0.5
    prompt_embedding: Optional[list[float]] = None
    healing_counter: int = 0
    reference_count: int = 1
    source: Optional[str] = None
    has_backup_source: bool = True
    action_context: str = "reversible"

class StepRequest(BaseModel):
    step_id: str
    entry_ids: list[str]

class PreflightRequest(BaseModel):
    agent_id: Optional[str] = "anonymous"
    task_id: Optional[str] = None
    memory_state: list[MemoryEntryRequest]
    action_type: Literal["informational","reversible","irreversible","destructive"] = "reversible"
    domain: Literal["general","customer_support","coding","legal","fintech","medical"] = "general"
    current_goal: Optional[str] = None
    current_goal_embedding: Optional[list[float]] = None
    client_gsv: Optional[int] = None
    client: Optional[str] = None
    compliance_profile: Optional[str] = "GENERAL"
    steps: Optional[list[StepRequest]] = None
    detail_level: Optional[str] = "obfuscated"  # "obfuscated" (default) or "full"
    thread_id: Optional[str] = None
    custom_weights: Optional[dict[str, float]] = None
    dp_epsilon: Optional[float] = None  # enable ε-DP with Laplace noise (default: off, set to e.g. 1.0)
    thresholds: Optional[dict[str, float]] = None  # custom WARN/ASK_USER/BLOCK thresholds
    use_pagerank: bool = False  # opt-in PageRank authority scoring
    score_history: Optional[list[float]] = None  # recent omega scores for CUSUM/EWMA trend detection
    page_hinkley_config: Optional[dict[str, float]] = None  # {"delta": float, "lambda": float}
    reset_frechet_reference: bool = False  # reset stored Fréchet reference distribution

class HealRequest(BaseModel):
    entry_id: str
    action: Literal["REFETCH", "VERIFY_WITH_SOURCE", "REBUILD_WORKING_SET"]
    agent_id: Optional[str] = "anonymous"

class OutcomeRequest(BaseModel):
    outcome_id: str
    preflight_id: Optional[str] = None
    status: Literal["success", "failure", "partial"]
    failure_components: list[str] = []

class BatchRequest(BaseModel):
    entries: list[MemoryEntryRequest]
    action_type: Literal["informational","reversible","irreversible","destructive"] = "reversible"
    domain: Literal["general","customer_support","coding","legal","fintech","medical"] = "general"
    custom_weights: Optional[dict[str, float]] = None

class WebhookRegisterRequest(BaseModel):
    url: str
    events: list[Literal["BLOCK", "WARN", "ASK_USER"]]
    secret: str
    target: Optional[Literal["generic", "slack", "pagerduty"]] = "generic"

class SignupRequest(BaseModel):
    email: str


TIER_LIMITS = {
    "free": 10_000,
    "starter": 100_000,
    "growth": 1_000_000,
}


def _generate_api_key() -> str:
    return "sg_live_" + secrets.token_urlsafe(32)


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


@app.get("/")
def root():
    return {"name": "Sgraal", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"status": "ok", "port": os.environ.get("PORT", "not set")}

@app.get("/metrics")
def metrics(accept: Optional[str] = None):
    """Prometheus-format metrics export. Also accepts ?format=json."""
    if accept == "json":
        return _metrics.to_json()
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=_metrics.to_prometheus(), media_type="text/plain")

@app.get("/v1/compliance/gdpr")
def gdpr_compliance():
    return {
        "policy": "Sgraal GDPR Data Processing Commitment",
        "data_retention": {
            "preflight_logs": "90 days, then auto-deleted",
            "audit_logs": "1 year, then archived",
            "api_keys": "retained until account deletion",
            "memory_state": "not stored — processed in real time and discarded",
        },
        "right_to_erasure": {
            "endpoint": "DELETE /v1/account",
            "scope": "All API keys, logs, and associated data permanently deleted within 30 days",
            "contact": "dpa@sgraal.com",
        },
        "data_portability": {
            "endpoint": "GET /v1/account/export",
            "format": "JSON",
            "scope": "All preflight logs, audit logs, and API key metadata",
        },
        "dpa_contact": {
            "email": "dpa@sgraal.com",
            "name": "Sgraal Data Protection Officer",
            "response_time": "72 hours",
        },
        "data_location": "EU (Frankfurt, DE)",
        "sub_processors": [
            {"name": "Supabase", "purpose": "Database", "location": "EU"},
            {"name": "Railway", "purpose": "API hosting", "location": "US/EU"},
            {"name": "Stripe", "purpose": "Billing", "location": "US"},
            {"name": "Upstash", "purpose": "Redis (GSV)", "location": "EU"},
        ],
        "legal_basis": "Legitimate interest (Article 6(1)(f)) and contract performance (Article 6(1)(b))",
    }

@app.get("/v1/compliance/sla")
def sla_tiers():
    return {
        "sla": "Sgraal Service Level Agreement",
        "tiers": {
            "free": {
                "uptime": "99.0%",
                "response_time_p95": "500ms",
                "support_response": "community (GitHub Issues)",
                "rate_limit": "10,000 calls/month",
            },
            "starter": {
                "uptime": "99.9%",
                "response_time_p95": "200ms",
                "support_response": "48 hours (email)",
                "rate_limit": "100,000 calls/month",
            },
            "growth": {
                "uptime": "99.9%",
                "response_time_p95": "100ms",
                "support_response": "4 hours (priority email)",
                "rate_limit": "1,000,000 calls/month",
            },
            "enterprise": {
                "uptime": "99.99%",
                "response_time_p95": "50ms",
                "support_response": "1 hour (dedicated Slack channel)",
                "rate_limit": "custom",
            },
        },
        "credit_policy": {
            "below_99.9%": "10% monthly credit",
            "below_99.0%": "25% monthly credit",
            "below_95.0%": "50% monthly credit",
        },
        "exclusions": ["scheduled maintenance (announced 48h in advance)", "force majeure", "client-side issues"],
        "contact": "sla@sgraal.com",
    }

@app.get("/v1/compliance/docs")
def compliance_docs():
    return {
        "title": "Sgraal Compliance Documentation",
        "profiles": {
            "EU_AI_ACT": {
                "description": "European Union AI Act compliance profile",
                "articles": {
                    "Article 9": "Risk management — medical domain with omega>40 requires human oversight",
                    "Article 12": "Logging — irreversible actions with omega>60 blocked, audit trail required",
                    "Article 13": "Transparency — explainability_note always included in every response",
                },
                "enforcement": "Critical violations override recommended_action to BLOCK",
            },
            "GDPR": {
                "description": "General Data Protection Regulation",
                "measures": {
                    "data_minimization": "Memory state processed in real time, not stored",
                    "privacy_by_design": "3-layer privacy: ID obfuscation, reason abstraction, ZK commitment",
                    "differential_privacy": "Optional ε-DP via Laplace mechanism (dp_epsilon field)",
                    "right_to_erasure": "DELETE /v1/account removes all data within 30 days",
                },
            },
            "FDA_510K": {
                "description": "FDA 510(k) medical device compliance",
                "rules": {
                    "predicate_comparison": "Medical domain with omega>30 requires predicate device comparison",
                    "risk_classification": "Irreversible/destructive actions with omega>50 require Class III review",
                },
                "healing_policy": "tool_state + medical → tier 3 (log-only), requires approval",
            },
            "HIPAA": {
                "description": "Health Insurance Portability and Accountability Act",
                "rules": {
                    "phi_integrity": "Medical domain with assurance<70 → PHI integrity cannot be guaranteed",
                },
                "healing_policy": "All medical memory types require approval for healing actions",
            },
        },
        "usage": "Add compliance_profile field to POST /v1/preflight (e.g. 'EU_AI_ACT')",
        "docs_url": "https://sgraal.com/docs/compliance",
    }

@app.get("/docs/quickstart")
def quickstart():
    return {
        "title": "Sgraal Quickstart Examples",
        "perplexity_note": "Batch scoring: up to 100 entries per call, <10ms p95 — ideal for long context query chains.",
        "examples": {
            "python_batch_scoring": {
                "title": "Fintech Batch Scoring (Python SDK)",
                "install": "pip install sgraal",
                "code": """from sgraal import SgraalClient

client = SgraalClient(api_key="sg_live_...")

result = client.preflight(
    memory_state=[
        {"id": "mem_001", "content": "User credit score updated to 720", "type": "tool_state", "timestamp_age_days": 2, "source_trust": 0.95, "source_conflict": 0.05, "downstream_count": 4},
        {"id": "mem_002", "content": "User income verified at $85k", "type": "tool_state", "timestamp_age_days": 45, "source_trust": 0.8, "source_conflict": 0.2, "downstream_count": 3},
        {"id": "mem_003", "content": "Previous loan default in 2019", "type": "episodic", "timestamp_age_days": 180, "source_trust": 0.99, "source_conflict": 0.0, "downstream_count": 6}
    ],
    action_type="irreversible",
    domain="fintech"
)
print(result.recommended_action)  # USE_MEMORY / WARN / ASK_USER / BLOCK
print(result.omega_mem_final)     # 0-100 risk score""",
                "batch_variant": """# Batch scoring (up to 100 entries)
import requests
resp = requests.post("https://api.sgraal.com/v1/preflight/batch",
    headers={"Authorization": "Bearer sg_live_..."},
    json={
        "entries": [
            {"id": "mem_001", "content": "Credit score 720", "type": "tool_state", "timestamp_age_days": 2, "source_trust": 0.95, "source_conflict": 0.05, "downstream_count": 4},
            {"id": "mem_002", "content": "Income $85k", "type": "tool_state", "timestamp_age_days": 45, "source_trust": 0.8, "source_conflict": 0.2, "downstream_count": 3},
        ],
        "action_type": "irreversible",
        "domain": "fintech"
    })
print(resp.json()["batch_summary"])""",
            },
            "langchain_guard": {
                "title": "LangChain / LangGraph Integration",
                "install": "pip install langchain-sgraal",
                "code": """from langchain_sgraal import SgraalMemoryGuard, sgraal_guard

# Option 1: As a LangChain tool
tool = SgraalMemoryGuard(api_key="sg_live_...")
result = tool.invoke({
    "memory_state": [{"id": "m1", "content": "User address", "type": "preference", "timestamp_age_days": 30}],
    "action_type": "irreversible",
    "domain": "fintech"
})

# Option 2: Guard decorator for LangGraph nodes
@sgraal_guard(
    memory_state=lambda state: state["memories"],
    action_type="irreversible",
    domain="fintech",
    block_on="BLOCK"
)
def process_trade(state):
    return execute_trade(state)""",
            },
            "claude_mcp": {
                "title": "Claude Desktop (MCP Server)",
                "install": "npm install @sgraal/mcp",
                "config": """{
  "mcpServers": {
    "sgraal": {
      "command": "npx",
      "args": ["@sgraal/mcp"],
      "env": { "SGRAAL_API_KEY": "sg_live_..." }
    }
  }
}""",
                "description": "Add to claude_desktop_config.json. Claude will have access to sgraal_preflight tool to check memory reliability before acting.",
            },
        },
        "links": {
            "docs": "https://sgraal.com/docs/compliance",
            "signup": "https://api.sgraal.com/v1/signup",
            "github": "https://github.com/sgraal-ai/core",
            "pypi_sgraal": "https://pypi.org/project/sgraal/",
            "pypi_langchain": "https://pypi.org/project/langchain-sgraal/",
            "npm_mcp": "https://www.npmjs.com/package/@sgraal/mcp",
        },
    }

@app.get("/v1/verify")
def verify(
    profile: str = "GENERAL",
    domain: str = "general",
    history: Optional[str] = None,
    key_record: dict = Depends(verify_api_key),
):
    verifier = PolicyVerifier()
    comp_profile = ComplianceProfile(profile) if profile in [p.value for p in ComplianceProfile] else ComplianceProfile.GENERAL

    healing_result = verifier.verify_healing_policy()
    compliance_result = verifier.verify_compliance_rules(comp_profile, domain)

    verified = healing_result.verified and compliance_result.verified
    proofs = [healing_result.proof, compliance_result.proof]
    counterexample = healing_result.counterexample or compliance_result.counterexample
    duration = round(healing_result.duration_ms + compliance_result.duration_ms, 2)

    response = {
        "verified": verified,
        "proof": " | ".join(proofs),
        "counterexample": counterexample,
        "duration_ms": duration,
        "profile": comp_profile.value,
        "domain": domain,
    }

    # Kalman forecast if history provided (comma-separated floats)
    if history:
        scores = [float(s.strip()) for s in history.split(",") if s.strip()]
        if len(scores) >= 2:
            forecaster = KalmanForecaster()
            forecaster.fit(scores)
            forecast = forecaster.predict(steps=5)
            response["forecast"] = {
                "trend": forecast.trend,
                "collapse_risk": forecast.collapse_risk,
                "forecast_scores": forecast.forecast_scores,
            }

    return response

@app.post("/v1/signup")
def signup(req: SignupRequest):
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    if not supabase_service_client:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    # 1. Create Stripe customer
    customer = stripe.Customer.create(email=req.email)

    # 2. Create free tier subscription
    stripe.Subscription.create(
        customer=customer.id,
        items=[{"price": "price_1TDnSaHIIn2LzB5quygTrclw"}],
    )

    # 3. Generate API key
    api_key = _generate_api_key()
    key_hash = _hash_key(api_key)

    # 4. Store hashed key in Supabase (service role bypasses RLS)
    supabase_service_client.table("api_keys").insert({
        "key_hash": key_hash,
        "customer_id": customer.id,
        "email": req.email,
        "tier": "free",
    }).execute()

    # 5. Return plaintext key (only time it's shown)
    return {
        "api_key": api_key,
        "customer_id": customer.id,
        "tier": "free",
    }


# --- Metrics collector ---
import time as _time

class _Metrics:
    def __init__(self):
        self.preflight_total = 0
        self.heal_total = 0
        self.decisions = {"USE_MEMORY": 0, "WARN": 0, "ASK_USER": 0, "BLOCK": 0}
        self.omega_sum = 0.0
        self.response_times: list[float] = []  # seconds

    def record_preflight(self, decision: str, omega: float, duration: float):
        self.preflight_total += 1
        self.decisions[decision] = self.decisions.get(decision, 0) + 1
        self.omega_sum += omega
        self.response_times.append(duration)
        # Keep last 1000 response times for p95
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

    def record_heal(self):
        self.heal_total += 1

    def avg_omega(self) -> float:
        return round(self.omega_sum / max(self.preflight_total, 1), 2)

    def p95_response_time_ms(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return round(sorted_times[min(idx, len(sorted_times) - 1)] * 1000, 2)

    def to_prometheus(self) -> str:
        lines = [
            "# HELP sgraal_preflight_total Total preflight API calls",
            "# TYPE sgraal_preflight_total counter",
            f"sgraal_preflight_total {self.preflight_total}",
            "",
            "# HELP sgraal_heal_total Total heal API calls",
            "# TYPE sgraal_heal_total counter",
            f"sgraal_heal_total {self.heal_total}",
            "",
            "# HELP sgraal_decision_total Decision distribution",
            "# TYPE sgraal_decision_total counter",
        ]
        for decision, count in self.decisions.items():
            lines.append(f'sgraal_decision_total{{decision="{decision}"}} {count}')
        lines += [
            "",
            "# HELP sgraal_omega_avg Average omega_mem_final score",
            "# TYPE sgraal_omega_avg gauge",
            f"sgraal_omega_avg {self.avg_omega()}",
            "",
            "# HELP sgraal_response_time_p95_ms p95 response time in milliseconds",
            "# TYPE sgraal_response_time_p95_ms gauge",
            f"sgraal_response_time_p95_ms {self.p95_response_time_ms()}",
        ]
        return "\n".join(lines) + "\n"

    def to_json(self) -> dict:
        return {
            "preflight_total": self.preflight_total,
            "heal_total": self.heal_total,
            "decisions": dict(self.decisions),
            "avg_omega": self.avg_omega(),
            "p95_response_time_ms": self.p95_response_time_ms(),
        }


_metrics = _Metrics()

# --- Webhook registry ---
_webhooks: list[dict] = []


def _sign_payload(payload: str, secret: str) -> str:
    return _hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _format_slack(payload: dict) -> dict:
    decision = payload["decision"]
    emoji = ":red_circle:" if decision == "BLOCK" else ":warning:"
    return {
        "text": f"{emoji} Sgraal {decision}: Ω={payload['omega_score']} | request={payload['request_id']}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": (
                f"*{decision}* — Ω_MEM = {payload['omega_score']}\n"
                f"Request: `{payload['request_id']}`\n"
                f"Time: {payload['timestamp']}"
            )}},
        ],
    }


def _format_pagerduty(payload: dict) -> dict:
    return {
        "routing_key": "",  # user provides in webhook URL
        "event_action": "trigger",
        "payload": {
            "summary": f"Sgraal {payload['decision']}: Ω={payload['omega_score']}",
            "severity": "critical" if payload["decision"] == "BLOCK" else "warning",
            "source": "sgraal",
            "custom_details": payload,
        },
    }


def _dispatch_webhooks(decision: str, request_id: str, omega: float, entry_ids: list[str]):
    """Fire webhooks matching the decision. Runs in background thread."""
    now = datetime.now(timezone.utc).isoformat()
    base_payload = {
        "request_id": request_id,
        "decision": decision,
        "omega_score": omega,
        "memory_ids": entry_ids,
        "timestamp": now,
    }

    for hook in _webhooks:
        if decision not in hook["events"]:
            continue

        target = hook.get("target", "generic")
        if target == "slack":
            body = _format_slack(base_payload)
        elif target == "pagerduty":
            body = _format_pagerduty(base_payload)
        else:
            body = base_payload

        payload_str = _json.dumps(body, sort_keys=True)
        signature = _sign_payload(payload_str, hook["secret"])

        def _send(url=hook["url"], data=payload_str, sig=signature):
            try:
                http_requests.post(
                    url,
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "X-Sgraal-Signature": sig,
                    },
                    timeout=5,
                )
            except Exception:
                pass

        threading.Thread(target=_send, daemon=True).start()


def _audit_log(event_type: str, request_id: str, key_record: dict, decision: str, omega: float, extra: dict = None):
    """Log audit event to Supabase."""
    if not supabase_client:
        return
    try:
        record = {
            "event_type": event_type,
            "request_id": request_id,
            "api_key_id": key_record.get("key_hash", "in_memory"),
            "decision": decision,
            "omega_mem_final": omega,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            record.update(extra)
        supabase_client.table("audit_log").insert(record).execute()
    except Exception:
        pass


# In-memory healing counter store (per entry_id)
_healing_counters: dict[str, int] = {}

# Thread manager for adaptive sampling
_thread_manager = ThreadManager()

# In-memory outcome registry (outcome_id -> outcome record)
_outcomes: dict[str, dict] = {}

# Projected improvement estimates per action type
_HEAL_IMPROVEMENTS = {
    "REFETCH": 8.0,
    "VERIFY_WITH_SOURCE": 5.0,
    "REBUILD_WORKING_SET": 3.5,
}


@app.post("/v1/heal")
def heal(req: HealRequest, key_record: dict = Depends(verify_api_key)):
    # Increment healing counter for this entry
    prev = _healing_counters.get(req.entry_id, 0)
    _healing_counters[req.entry_id] = prev + 1

    now = datetime.now(timezone.utc)
    projected = _HEAL_IMPROVEMENTS.get(req.action, 0.0)

    # Log healing event to Supabase
    if supabase_client:
        try:
            supabase_client.table("memory_ledger").insert({
                "agent_id": req.agent_id,
                "action_type": f"heal:{req.action}",
                "healing_counter": prev + 1,
                "explainability_note": f"Heal action {req.action} applied to {req.entry_id}",
                "omega_mem_final": 0,
                "recommended_action": "HEAL",
                "assurance_score": 0,
                "domain": "general",
                "component_breakdown": {"entry_id": req.entry_id},
            }).execute()
        except Exception:
            pass

    lyap = compute_lyapunov(
        healing_counter=prev + 1,
        projected_improvement=projected,
        action=req.action,
    )

    heal_request_id = str(uuid.uuid4())
    _audit_log("heal", heal_request_id, key_record, req.action, 0, {"entry_id": req.entry_id})
    _metrics.record_heal()

    return {
        "healed": True,
        "healing_counter": prev + 1,
        "projected_improvement": projected,
        "action_taken": req.action,
        "entry_id": req.entry_id,
        "timestamp": now.isoformat(),
        "lyapunov_stability": {
            "V": lyap.V,
            "V_dot": lyap.V_dot,
            "converging": lyap.converging,
            "guaranteed": lyap.guaranteed,
        },
    }


@app.post("/v1/webhooks")
def register_webhook(req: WebhookRegisterRequest, key_record: dict = Depends(verify_api_key)):
    webhook = {
        "id": str(uuid.uuid4()),
        "url": req.url,
        "events": req.events,
        "secret": req.secret,
        "target": req.target,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _webhooks.append(webhook)
    return {
        "webhook_id": webhook["id"],
        "url": req.url,
        "events": req.events,
        "target": req.target,
        "registered": True,
    }

@app.get("/v1/webhooks")
def list_webhooks(key_record: dict = Depends(verify_api_key)):
    return {
        "webhooks": [
            {"id": w["id"], "url": w["url"], "events": w["events"], "target": w["target"]}
            for w in _webhooks
        ],
        "total": len(_webhooks),
    }

@app.delete("/v1/webhooks/{webhook_id}")
def delete_webhook(webhook_id: str, key_record: dict = Depends(verify_api_key)):
    global _webhooks
    before = len(_webhooks)
    _webhooks = [w for w in _webhooks if w["id"] != webhook_id]
    if len(_webhooks) == before:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    return {"deleted": True, "webhook_id": webhook_id}


@app.post("/v1/preflight/batch")
def preflight_batch(req: BatchRequest, key_record: dict = Depends(verify_api_key)):
    if len(req.entries) == 0:
        raise HTTPException(status_code=400, detail="entries cannot be empty")
    if len(req.entries) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 entries per batch request")

    # Validate custom weights if provided
    if req.custom_weights:
        weight_sum = sum(req.custom_weights.values())
        if abs(weight_sum) > 2.0 or abs(weight_sum) < 0.5:
            raise HTTPException(
                status_code=400,
                detail=f"custom_weights sum out of range (expected 0.5–2.0), got {weight_sum:.3f}",
            )

    results = []
    for e in req.entries:
        entry = MemoryEntry(
            id=e.id, content=e.content, type=e.type,
            timestamp_age_days=e.timestamp_age_days,
            source_trust=e.source_trust,
            source_conflict=e.source_conflict,
            downstream_count=e.downstream_count,
            r_belief=e.r_belief,
            healing_counter=e.healing_counter,
        )
        result = compute([entry], req.action_type, req.domain, custom_weights=req.custom_weights)
        results.append({
            "entry_id": e.id,
            "omega_mem_final": result.omega_mem_final,
            "recommended_action": result.recommended_action,
            "assurance_score": result.assurance_score,
            "explainability_note": result.explainability_note,
            "component_breakdown": result.component_breakdown,
            "shapley_values": compute_shapley_values(
                result.component_breakdown, req.action_type, req.domain, req.custom_weights,
            ),
        })

    blocked = sum(1 for r in results if r["recommended_action"] == "BLOCK")
    warned = sum(1 for r in results if r["recommended_action"] in ("WARN", "ASK_USER"))
    safe = sum(1 for r in results if r["recommended_action"] == "USE_MEMORY")
    highest = max(results, key=lambda r: r["omega_mem_final"])

    return {
        "results": results,
        "batch_summary": {
            "total": len(results),
            "blocked": blocked,
            "warned": warned,
            "safe": safe,
            "highest_risk_entry_id": highest["entry_id"],
        },
        "weights_used": "custom" if req.custom_weights else "default",
    }


@app.post("/v1/outcome")
def close_outcome(req: OutcomeRequest, key_record: dict = Depends(verify_api_key)):
    if req.outcome_id not in _outcomes:
        raise HTTPException(status_code=404, detail=f"Outcome {req.outcome_id} not found")

    outcome = _outcomes[req.outcome_id]
    if outcome["status"] != "open":
        raise HTTPException(status_code=409, detail=f"Outcome {req.outcome_id} already closed")

    now = datetime.now(timezone.utc)
    outcome["status"] = req.status
    outcome["closed_at"] = now.isoformat()
    outcome["component_attribution"] = req.failure_components

    # Log to Supabase outcome_log
    if supabase_client:
        try:
            supabase_client.table("outcome_log").insert({
                "outcome_id": req.outcome_id,
                "preflight_id": req.preflight_id or outcome.get("preflight_id"),
                "agent_id": outcome.get("agent_id"),
                "task_id": outcome.get("task_id"),
                "status": req.status,
                "component_attribution": req.failure_components,
                "closed_at": now.isoformat(),
            }).execute()
        except Exception:
            pass

    # RL Q-table update
    rl_reward = None
    try:
        rl_reward = update_from_outcome(
            omega_mem_final=outcome.get("omega_mem_final", 0),
            component_breakdown=outcome.get("component_breakdown", {}),
            action=outcome.get("recommended_action", "USE_MEMORY"),
            outcome_status=req.status,
            domain=outcome.get("domain", "general"),
        )
    except Exception:
        pass

    # Geodesic update of L_v4 weights
    lv4_updated = False
    try:
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            _domain = outcome.get("domain", "general")
            _lv4_key = f"lv4_weights:{key_record.get('key_hash', 'default')}:{_domain}"
            _lv4r = http_requests.get(
                f"{UPSTASH_REDIS_URL}/GET/{_lv4_key}",
                headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                timeout=2,
            )
            if _lv4r.ok and _lv4r.json().get("result"):
                _lv4_data = _json.loads(_lv4r.json()["result"])
                _weights = _lv4_data.get("weights", [1/11]*11)
                _losses = _lv4_data.get("last_losses", [0.0]*11)
                _count = _lv4_data.get("update_count", 0)
                _new_weights = geodesic_update(_weights, _losses)
                _new_data = _json.dumps({"weights": _new_weights, "last_losses": _losses, "update_count": _count + 1})
                http_requests.post(
                    f"{UPSTASH_REDIS_URL}/SET/{_lv4_key}/{_new_data}/EX/86400",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                lv4_updated = True
    except Exception:
        pass

    # Temperature decay for policy gradient
    pg_temp_decayed = False
    try:
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            _domain = outcome.get("domain", "general")
            _pg_temp_key = f"pg_temperature:{key_record.get('key_hash', 'default')}:{_domain}"
            _ptr = http_requests.get(
                f"{UPSTASH_REDIS_URL}/GET/{_pg_temp_key}",
                headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                timeout=2,
            )
            _cur_temp = 1.0
            if _ptr.ok and _ptr.json().get("result") is not None:
                _cur_temp = float(_ptr.json()["result"])
            _new_temp = decay_temperature(_cur_temp)
            http_requests.post(
                f"{UPSTASH_REDIS_URL}/SET/{_pg_temp_key}/{_new_temp}/EX/86400",
                headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                timeout=2,
            )
            pg_temp_decayed = True
    except Exception:
        pass

    resp = {
        "outcome_id": req.outcome_id,
        "status": req.status,
        "closed_at": now.isoformat(),
    }
    if rl_reward is not None:
        resp["rl_reward"] = rl_reward
    if lv4_updated:
        resp["lv4_geodesic_updated"] = True
    if pg_temp_decayed:
        resp["pg_temperature_decayed"] = True
    return resp


@app.post("/v1/preflight")
def preflight(req: PreflightRequest, key_record: dict = Depends(verify_api_key)):
    _t_start = _time.monotonic()

    if not req.memory_state:
        raise HTTPException(status_code=400, detail="memory_state cannot be empty")

    # Rate limit check
    tier = key_record.get("tier", "free")
    calls = key_record.get("calls_this_month", 0)
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    if calls >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit of {limit:,} calls exceeded for {tier} tier. "
                   f"Upgrade your plan or wait until the next billing cycle.",
        )

    # Thread-aware sampling
    thread_bucket_id = None
    thread_sample_rate = None
    if req.thread_id:
        thread_bucket_id = _thread_manager.assign_bucket(req.thread_id, req.domain)
        thread_sample_rate = _thread_manager.get_sample_rate(req.domain)
        if not _thread_manager.should_check(req.thread_id, req.domain):
            return {
                "sampled": False,
                "recommended_action": "USE_MEMORY",
                "reason": "sampled_out",
                "thread_id": req.thread_id,
                "bucket_id": thread_bucket_id,
                "sample_rate": thread_sample_rate,
            }

    # Sheaf cohomology: auto-compute source_conflict when not provided
    any_manual_conflict = any(e.source_conflict is not None for e in req.memory_state)
    sheaf_result = None
    if not any_manual_conflict and len(req.memory_state) >= 2:
        sheaf_entries = [{"id": e.id, "content": e.content, "prompt_embedding": e.prompt_embedding} for e in req.memory_state]
        sheaf_result = compute_sheaf_consistency(sheaf_entries)

    auto_conflict = sheaf_result.auto_source_conflict if sheaf_result else 0.1

    entries = [MemoryEntry(
        id=e.id, content=e.content, type=e.type,
        timestamp_age_days=e.timestamp_age_days,
        source_trust=e.source_trust,
        source_conflict=e.source_conflict if e.source_conflict is not None else auto_conflict,
        downstream_count=e.downstream_count,
        r_belief=e.r_belief,
        prompt_embedding=e.prompt_embedding,
        healing_counter=e.healing_counter,
        reference_count=e.reference_count,
        source=e.source,
        has_backup_source=e.has_backup_source,
        action_context=e.action_context)
        for e in req.memory_state]

    result = compute(entries, req.action_type, req.domain, req.current_goal_embedding, req.custom_weights, req.thresholds, req.use_pagerank)

    # Generate IDs for tracking
    request_id = str(uuid.uuid4())
    outcome_id = str(uuid.uuid4())
    _outcomes[outcome_id] = {
        "status": "open",
        "agent_id": req.agent_id,
        "task_id": req.task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "closed_at": None,
        "component_attribution": [],
        "omega_mem_final": result.omega_mem_final,
        "component_breakdown": dict(result.component_breakdown),
        "recommended_action": result.recommended_action,
        "domain": req.domain,
    }

    # Increment Global State Vector
    gsv = _increment_gsv()

    # Stale state detection: client's GSV is ahead of server's
    stale_state_warning = None
    if req.client_gsv is not None and gsv > 0 and gsv < req.client_gsv:
        stale_state_warning = (
            f"STALE_STATE_DETECTED: server GSV ({gsv}) < client GSV ({req.client_gsv}). "
            f"Memory state may be outdated."
        )

    # Increment calls_this_month and update last_used_at
    key_hash = key_record.get("key_hash")
    if supabase_service_client and key_hash:
        try:
            supabase_service_client.table("api_keys").update({
                "calls_this_month": calls + 1,
                "last_used_at": datetime.now(timezone.utc).isoformat(),
            }).eq("key_hash", key_hash).execute()
        except Exception:
            pass

    if stripe.api_key:
        try:
            stripe.billing.MeterEvent.create(
                event_name="omega_mem_preflight",
                payload={
                    "value": "1",
                    "stripe_customer_id": key_record["customer_id"],
                },
            )
        except Exception:
            pass

    if supabase_client:
        try:
            supabase_client.table("memory_ledger").insert({
                "agent_id": req.agent_id,
                "task_id": req.task_id,
                "omega_mem_final": result.omega_mem_final,
                "recommended_action": result.recommended_action,
                "assurance_score": result.assurance_score,
                "domain": req.domain,
                "action_type": req.action_type,
                "explainability_note": result.explainability_note,
                "component_breakdown": result.component_breakdown,
                "healing_counter": result.healing_counter,
                "gsv": gsv,
            }).execute()
        except Exception as e:
            pass

    # Importance detection with VoI — find at-risk entries sorted by ROI
    importance_results = compute_importance_with_voi(entries, req.action_type, req.domain)
    at_risk_warnings = [
        {
            "entry_id": ir.entry_id,
            "importance_score": ir.importance_score,
            "voi_score": ir.voi_score,
            "warning": ir.warning,
            "signal_breakdown": ir.signal_breakdown,
        }
        for ir in importance_results if ir.at_risk
    ]

    # Compliance evaluation
    profile = ComplianceProfile(req.compliance_profile) if req.compliance_profile in [p.value for p in ComplianceProfile] else ComplianceProfile.GENERAL
    compliance = ComplianceEngine().evaluate(
        omega_mem_final=result.omega_mem_final,
        assurance_score=result.assurance_score,
        domain=req.domain,
        action_type=req.action_type,
        profile=profile,
    )

    # Override recommended_action if compliance requires it
    if not compliance.compliant:
        critical = any(v.severity == "critical" for v in compliance.violations)
        if critical and result.recommended_action in ("USE_MEMORY", "WARN"):
            result = PreflightResult(
                omega_mem_final=result.omega_mem_final,
                recommended_action="BLOCK",
                assurance_score=result.assurance_score,
                explainability_note=result.explainability_note,
                component_breakdown=result.component_breakdown,
                repair_plan=result.repair_plan,
                healing_counter=result.healing_counter,
            )

    # Apply healing policy matrix to repair plan tiers
    policy_matrix = HealingPolicyMatrix()
    for action in result.repair_plan:
        entry = next((e for e in entries if e.id == action.entry_id), None)
        if entry:
            policy = policy_matrix.lookup(entry.type, req.domain, profile)
            action.priority = max(action.priority, policy.tier)

    # Client optimization
    client_optimized = False
    optimizer_version = None
    if req.client:
        co = ClientOptimizer().optimize(result, entries, client_profile=req.client)
        result = co.preflight
        client_optimized = co.client_optimized
        optimizer_version = co.optimizer_version

    # Surgical block via dependency graph
    surgical_result = None
    auto_tracked = False
    if req.steps:
        graph = MemoryDependencyGraph()
        for step in req.steps:
            graph.add_step(step.step_id, step.entry_ids)
        blocked_entries = [h.entry_id for h in result.repair_plan]
        sr = graph.surgical_block(blocked_entries)
        surgical_result = {
            "blocked_steps": sr.blocked_steps,
            "safe_steps": sr.safe_steps,
            "partial_execution_possible": sr.partial_execution_possible,
        }
    elif len(entries) > 1:
        # Auto-track: each entry is treated as its own step
        tracker = MemoryAccessTracker()
        for e in entries:
            tracker.track(f"auto:{e.id}", e.id)
        blocked_entries = [h.entry_id for h in result.repair_plan]
        if blocked_entries:
            graph = tracker.to_dependency_graph()
            sr = graph.surgical_block(blocked_entries)
            surgical_result = {
                "blocked_steps": sr.blocked_steps,
                "safe_steps": sr.safe_steps,
                "partial_execution_possible": sr.partial_execution_possible,
            }
            auto_tracked = True

    # Privacy layers
    session_key = str(uuid.uuid4())
    full_detail = req.detail_level == "full"
    all_entry_ids = [e.id for e in entries]

    # Layer 1: obfuscate entry IDs in repair plan
    repair_plan_out = []
    for h in result.repair_plan:
        eid = h.entry_id if full_detail else ObfuscatedId.obfuscate(h.entry_id, session_key)
        reason = h.reason if full_detail else ReasonAbstractor.abstract(h.reason)
        repair_plan_out.append({
            "action": h.action,
            "entry_id": eid,
            "reason": reason,
            "projected_improvement": h.projected_improvement,
            "priority": h.priority,
        })

    # Layer 3: ZK commitment
    zk_commitment = ZKAssurance.commit(result.omega_mem_final, all_entry_ids)

    # ε-Differential Privacy: add calibrated Laplace noise
    omega_out = result.omega_mem_final
    privacy_guarantee = None
    if req.dp_epsilon is not None and req.dp_epsilon > 0:
        dp = LaplaceMechanism(epsilon=req.dp_epsilon)
        dp_check = dp.check_guarantee(len(entries), session_key)
        noised, _ = dp.add_noise(result.omega_mem_final, dp_check.sensitivity, session_key)
        omega_out = round(max(0, min(100, noised)), 1)
        privacy_guarantee = {
            "epsilon": dp_check.epsilon,
            "mechanism": dp_check.mechanism,
            "dp_satisfied": dp_check.dp_satisfied,
        }

    response = {
        "omega_mem_final": omega_out,
        "recommended_action": result.recommended_action,
        "assurance_score": result.assurance_score,
        "explainability_note": result.explainability_note,
        "component_breakdown": result.component_breakdown,
        "repair_plan": repair_plan_out,
        "healing_counter": result.healing_counter,
        "gsv": gsv,
        "outcome_id": outcome_id,
        "client_optimized": client_optimized,
        "compliance_result": {
            "compliant": compliance.compliant,
            "violations": [
                {"article": v.article, "description": v.description, "severity": v.severity}
                for v in compliance.violations
            ],
            "audit_required": compliance.audit_required,
            "profile_applied": compliance.profile_applied,
        },
        "session_key": session_key,
        "zk_commitment": zk_commitment,
        "sampled": True,
        "weights_used": "custom" if req.custom_weights else "default",
        "request_id": request_id,
        "use_pagerank": req.use_pagerank,
        "shapley_values": compute_shapley_values(
            result.component_breakdown, req.action_type, req.domain, req.custom_weights,
        ),
    }

    # Drift details — ensemble of KL, Wasserstein, JSD
    component_scores = list(result.component_breakdown.values())
    drift = compute_drift_metrics(component_scores)
    dd = {
        "kl_divergence": drift.kl_divergence,
        "wasserstein": drift.wasserstein,
        "jsd": drift.jsd,
        "drift_method": drift.drift_method,
        "ensemble_score": drift.ensemble_score,
        "sinkhorn_used": drift.sinkhorn_used,
        "sinkhorn_iterations": drift.sinkhorn_iterations,
    }
    if drift.alpha_divergence:
        dd["alpha_divergence"] = {
            "alpha_0_5": drift.alpha_divergence.alpha_0_5,
            "alpha_1_5": drift.alpha_divergence.alpha_1_5,
            "alpha_2_0": drift.alpha_divergence.alpha_2_0,
        }
    if drift.mmd:
        dd["mmd"] = {
            "score": drift.mmd.score,
            "sigma": drift.mmd.sigma,
            "kernel": drift.mmd.kernel,
        }
    response["drift_details"] = dd

    # CUSUM + EWMA trend detection + BOCPD
    if req.score_history and len(req.score_history) >= 2:
        trend = detect_trend(req.score_history)
        td = {
            "cusum_alert": trend.cusum_alert,
            "ewma_alert": trend.ewma_alert,
            "drift_sustained": trend.drift_sustained,
            "consecutive_degradations": trend.consecutive_degradations,
        }

        # BOCPD
        try:
            if len(req.score_history) >= 3:
                bocpd = compute_bocpd(req.score_history)
                td["bocpd"] = {
                    "p_changepoint": bocpd.p_changepoint,
                    "regime_change": bocpd.regime_change,
                    "current_run_length": bocpd.current_run_length,
                    "merkle_reset_triggered": bocpd.merkle_reset_triggered,
                }
        except Exception:
            pass  # graceful degradation

        # Page-Hinkley change detection
        _ph_alert = False
        try:
            _ph_history = list(req.score_history) if req.score_history else []
            if len(_ph_history) < 5 and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
                try:
                    _phk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                    _phr = http_requests.get(
                        f"{UPSTASH_REDIS_URL}/LRANGE/{_phk}/0/99",
                        headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                        timeout=2,
                    )
                    if _phr.ok:
                        _phh = _phr.json().get("result", [])
                        if _phh:
                            _ph_history = [float(x) for x in _phh]
                except Exception:
                    pass

            if len(_ph_history) >= 5:
                _ph_cfg = req.page_hinkley_config or {}
                _ph_delta = _ph_cfg.get("delta", 0.005)
                _ph_lambda = _ph_cfg.get("lambda", 50.0)
                ph = compute_page_hinkley(_ph_history, omega_out, delta=_ph_delta, lam=_ph_lambda)
                if ph:
                    td["page_hinkley"] = {
                        "ph_statistic": ph.ph_statistic,
                        "alert": ph.alert,
                        "change_magnitude": ph.change_magnitude,
                        "steps_since_change": ph.steps_since_change,
                        "running_mean": ph.running_mean,
                        "delta_used": ph.delta_used,
                        "lambda_used": ph.lambda_used,
                    }
                    _ph_alert = ph.alert
        except Exception:
            pass  # graceful degradation

        response["trend_detection"] = td

        # Permanent shift: Page-Hinkley alert AND BOCPD regime_change
        _bocpd_regime = td.get("bocpd", {}).get("regime_change", False)
        if _ph_alert and _bocpd_regime:
            response["permanent_shift_detected"] = True

    if "permanent_shift_detected" not in response:
        response["permanent_shift_detected"] = False

    # Calibration metrics
    cal = compute_calibration(omega_out, result.assurance_score, result.component_breakdown)
    response["calibration"] = {
        "brier_score": cal.brier_score,
        "log_loss": cal.log_loss,
        "calibrated_scores": cal.calibrated_scores,
        "meta_score": cal.meta_score,
    }

    # Free Energy functional (FE-01)
    fe_surprise = 0.0
    try:
        # Fetch max_observed_F from Redis
        fe_max_key = f"fe_max:{key_record.get('key_hash', 'default')}:{req.domain}"
        fe_max = None
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _r = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/GET/{fe_max_key}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _r.ok and _r.json().get("result") is not None:
                    fe_max = float(_r.json()["result"])
            except Exception:
                pass

        fe = compute_free_energy(omega_out, cal.meta_score, result.component_breakdown, fe_max)
        if fe:
            response["free_energy"] = {
                "F": fe.F,
                "elbo": fe.elbo,
                "kl_divergence": fe.kl_divergence,
                "reconstruction": fe.reconstruction,
                "surprise": fe.surprise,
            }
            fe_surprise = fe.surprise

            # Update max_observed_F in Redis if current F is larger
            if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
                try:
                    new_max = max(fe.F, fe_max or 1.0)
                    if fe_max is None or fe.F > fe_max:
                        http_requests.post(
                            f"{UPSTASH_REDIS_URL}/SET/{fe_max_key}/{new_max}/EX/7200",
                            headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                            timeout=2,
                        )
                except Exception:
                    pass
    except Exception:
        pass  # graceful degradation

    # Wire surprise into at_risk_warnings: entries with surprise > 0.8 get elevated
    if fe_surprise > 0.8 and at_risk_warnings:
        for w in at_risk_warnings:
            w["free_energy_surprise"] = fe_surprise
            w["warning"] = w.get("warning", "") + " [HIGH FREE ENERGY SURPRISE]"

    # Information Thermodynamics (IT-01)
    _it_max_flow = 0.0
    try:
        _it_history = list(req.score_history) if req.score_history else []
        if len(_it_history) < 5 and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _itk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                _itr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_itk}/0/99",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _itr.ok:
                    _ith = _itr.json().get("result", [])
                    if _ith:
                        _it_history = [float(x) for x in _ith]
            except Exception:
                pass

        if len(_it_history) >= 5:
            _comp_vals = list(result.component_breakdown.values())
            it = compute_info_thermodynamics(
                _it_history, omega_out, _comp_vals,
                healing_counter=result.healing_counter,
            )
            if it:
                response["info_thermodynamics"] = {
                    "transfer_entropy": it.transfer_entropy,
                    "max_flow": it.max_flow,
                    "landauer_bound": it.landauer_bound,
                    "information_temperature": it.information_temperature,
                    "entropy_production": it.entropy_production,
                    "reversibility": it.reversibility,
                }
                _it_max_flow = it.max_flow
    except Exception:
        pass  # graceful degradation

    # Mahalanobis multivariate anomaly detection (I-06)
    try:
        mah_entries = [{"id": e.id, "source_trust": e.source_trust,
                        "timestamp_age_days": e.timestamp_age_days,
                        "source_conflict": e.source_conflict,
                        "downstream_count": e.downstream_count,
                        "r_belief": e.r_belief} for e in entries]
        mah = compute_mahalanobis(mah_entries)
        if mah:
            response["mahalanobis_analysis"] = {
                "distances": [{"entry_id": d.entry_id, "distance": d.distance, "is_anomaly": d.is_anomaly} for d in mah.distances],
                "mean_distance": mah.mean_distance,
                "anomaly_count": mah.anomaly_count,
                "covariance_condition": mah.covariance_condition,
                "chi2_threshold": mah.chi2_threshold,
            }
            # Wire into s_interference: add (anomaly_count / n) * 20, cap at 100
            if mah.anomaly_count > 0:
                n_e = len(entries)
                boost = (mah.anomaly_count / max(n_e, 1)) * 20
                old_interf = response.get("component_breakdown", {}).get("s_interference", 0)
                new_interf = min(100, old_interf + boost)
                if "component_breakdown" in response:
                    response["component_breakdown"]["s_interference"] = round(new_interf, 2)
    except Exception:
        pass  # graceful degradation

    # Provenance entropy (P-03)
    try:
        _pe_entries = [{"id": e.id, "source_trust": e.source_trust, "source_conflict": e.source_conflict} for e in entries]
        # Fetch entropy history from Redis for trend
        _pe_history = None
        _pe_key = f"prov_entropy:{key_record.get('key_hash', 'default')}:{req.domain}"
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _per = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_pe_key}/0/9",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _per.ok:
                    _peh = _per.json().get("result", [])
                    if _peh:
                        _pe_history = [float(x) for x in _peh]
            except Exception:
                pass

        pe = compute_provenance_entropy(_pe_entries, history=_pe_history)
        if pe:
            response["provenance_entropy"] = {
                "per_entry": [{"entry_id": p.entry_id, "entropy": p.entropy, "source_count": p.source_count, "conflict_probable": p.conflict_probable} for p in pe.per_entry],
                "mean_entropy": pe.mean_entropy,
                "high_entropy_entries": pe.high_entropy_entries,
                "entropy_trend": pe.entropy_trend,
            }
            # Wire into s_provenance
            n_e = len(entries)
            max_h = math.log(n_e) if n_e > 1 else 1.0
            if max_h > 0 and "component_breakdown" in response:
                boost = (pe.mean_entropy / max_h) * 10
                old_prov = response["component_breakdown"].get("s_provenance", 0)
                response["component_breakdown"]["s_provenance"] = round(min(100, old_prov + boost), 2)

            # Push to Redis for trend
            if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
                try:
                    http_requests.post(
                        f"{UPSTASH_REDIS_URL}/RPUSH/{_pe_key}/{pe.mean_entropy}",
                        headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                        timeout=2,
                    )
                    http_requests.post(
                        f"{UPSTASH_REDIS_URL}/LTRIM/{_pe_key}/-10/-1",
                        headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                        timeout=2,
                    )
                    http_requests.post(
                        f"{UPSTASH_REDIS_URL}/EXPIRE/{_pe_key}/3600",
                        headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                        timeout=2,
                    )
                except Exception:
                    pass
    except Exception:
        pass  # graceful degradation

    # Subjective Logic (P-04)
    try:
        _sl_entries = [{"id": e.id, "source_trust": e.source_trust, "source_conflict": e.source_conflict} for e in entries]
        sl = compute_subjective_logic(_sl_entries)
        if sl:
            _sl_opinions = [{"entry_id": eid, "belief": op.belief, "disbelief": op.disbelief,
                             "uncertainty": op.uncertainty, "projected_prob": op.projected_prob}
                            for eid, op in sl.opinions]
            _sl_fused = None
            if sl.fused_opinion:
                _sl_fused = {"belief": sl.fused_opinion.belief, "disbelief": sl.fused_opinion.disbelief,
                             "uncertainty": sl.fused_opinion.uncertainty, "projected_prob": sl.fused_opinion.projected_prob}
            response["subjective_logic"] = {
                "opinions": _sl_opinions,
                "fused_opinion": _sl_fused,
                "high_uncertainty_entries": sl.high_uncertainty_entries,
                "consensus_possible": sl.consensus_possible,
            }
            # Wire into s_provenance: use fused projected_prob instead of raw trust
            if sl.fused_opinion and "component_breakdown" in response:
                fused_risk = (1.0 - sl.fused_opinion.projected_prob) * 100
                response["component_breakdown"]["s_provenance"] = round(min(100, fused_risk), 2)
    except Exception:
        pass  # graceful degradation

    # Fréchet distance for encoding degradation (R-05)
    try:
        if len(entries) >= 3:
            _fd_vectors = [[e.source_trust * 100, max(0, 100 - e.timestamp_age_days),
                            (1.0 - (e.source_conflict or 0.1)) * 100, max(0, 100 - e.downstream_count * 10),
                            (e.r_belief or 0) * 100] for e in entries]
            _fd_key = f"frechet_ref:{key_record.get('key_hash', 'default')}:{req.domain}"
            _fd_ref = None
            _fd_age = 0

            if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN and not req.reset_frechet_reference:
                try:
                    _fdr = http_requests.get(
                        f"{UPSTASH_REDIS_URL}/GET/{_fd_key}",
                        headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                        timeout=2,
                    )
                    if _fdr.ok and _fdr.json().get("result"):
                        _fd_data = _json.loads(_fdr.json()["result"])
                        _fd_ref = _fd_data.get("vectors")
                        _fd_age = _fd_data.get("age", 0) + 1
                except Exception:
                    pass

            if _fd_ref is None:
                # First call or reset: store current as reference
                if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
                    try:
                        _fd_store = _json.dumps({"vectors": _fd_vectors, "age": 0})
                        http_requests.post(
                            f"{UPSTASH_REDIS_URL}/SET/{_fd_key}/{_fd_store}/EX/86400",
                            headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                            timeout=2,
                        )
                    except Exception:
                        pass
            else:
                fd = compute_frechet(_fd_vectors, _fd_ref, reference_age_steps=_fd_age)
                if fd:
                    response["frechet_distance"] = {
                        "fd_score": fd.fd_score,
                        "mean_shift": fd.mean_shift,
                        "covariance_shift": fd.covariance_shift,
                        "encoding_degraded": fd.encoding_degraded,
                        "reference_age_steps": fd.reference_age_steps,
                    }
                    # Wire into r_encode
                    if fd.encoding_degraded and "component_breakdown" in response:
                        old_enc = response["component_breakdown"].get("r_encode", 0)
                        response["component_breakdown"]["r_encode"] = round(min(100, old_enc + 15), 2)

                    # Update age in Redis
                    if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
                        try:
                            _fd_store = _json.dumps({"vectors": _fd_ref, "age": _fd_age})
                            http_requests.post(
                                f"{UPSTASH_REDIS_URL}/SET/{_fd_key}/{_fd_store}/EX/86400",
                                headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                                timeout=2,
                            )
                        except Exception:
                            pass
    except Exception:
        pass  # graceful degradation

    # Mutual Information encoding efficiency (R-06/R-07)
    try:
        _mi_entries = [{"id": e.id, "source_trust": e.source_trust,
                        "source_conflict": e.source_conflict,
                        "timestamp_age_days": e.timestamp_age_days} for e in entries]
        mi = compute_mutual_information(_mi_entries)
        if mi:
            response["mutual_information"] = {
                "mi_score": mi.mi_score,
                "nmi_score": mi.nmi_score,
                "encoding_efficiency": mi.encoding_efficiency,
                "information_loss": mi.information_loss,
            }
            # Wire into r_encode: (1 - nmi) * 20
            if "component_breakdown" in response:
                boost = (1.0 - mi.nmi_score) * 20
                old_enc = response["component_breakdown"].get("r_encode", 0)
                response["component_breakdown"]["r_encode"] = round(min(100, old_enc + boost), 2)
    except Exception:
        pass  # graceful degradation

    # MDP optimal healing strategy (REC-02)
    try:
        # Fetch learned transitions from Redis
        _mdp_key = f"mdp_transitions:{key_record.get('key_hash', 'default')}:{req.domain}"
        _mdp_data = None
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _mdpr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/GET/{_mdp_key}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _mdpr.ok and _mdpr.json().get("result"):
                    _mdp_data = _json.loads(_mdpr.json()["result"])
            except Exception:
                pass

        mdp = compute_mdp(omega_out, transition_data=_mdp_data)
        if mdp:
            response["mdp_recommendation"] = {
                "optimal_action": mdp.optimal_action,
                "expected_value": mdp.expected_value,
                "action_values": mdp.action_values,
                "state": mdp.state,
                "confidence": mdp.confidence,
            }
            # Wire into repair_plan if action != WAIT
            if mdp.optimal_action != "WAIT":
                repair_plan_out.insert(0, {
                    "action": mdp.optimal_action,
                    "entry_id": "*",
                    "reason": f"MDP recommends {mdp.optimal_action} (V*={mdp.expected_value:.2f}, state={mdp.state})",
                    "projected_improvement": round(mdp.expected_value * 10, 1),
                    "priority": "high" if mdp.state in ("DEGRADED", "CRITICAL") else "medium",
                })
    except Exception:
        pass  # graceful degradation

    # MTTR Weibull estimation (REC-03)
    try:
        _mttr_key = f"mttr_history:{key_record.get('key_hash', 'default')}:{req.domain}"
        _mttr_durations = None
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _mttrr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_mttr_key}/0/49",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _mttrr.ok:
                    _mttrh = _mttrr.json().get("result", [])
                    if _mttrh:
                        _mttr_durations = [float(x) for x in _mttrh]
            except Exception:
                pass

        mttr = compute_mttr(_mttr_durations)
        if mttr:
            response["mttr_analysis"] = {
                "mttr_estimate": mttr.mttr_estimate,
                "mttr_p95": mttr.mttr_p95,
                "recovery_probability": mttr.recovery_probability,
                "weibull_k": mttr.weibull_k,
                "weibull_lambda": mttr.weibull_lambda,
                "sla_compliant": mttr.sla_compliant,
                "data_points": mttr.data_points,
            }
            if not mttr.sla_compliant:
                repair_plan_out.append({
                    "action": "SLA_WARNING",
                    "entry_id": "*",
                    "reason": f"SLA WARNING: p95 recovery time {mttr.mttr_p95:.1f} steps exceeds 20-step threshold",
                    "projected_improvement": 0,
                    "priority": "high",
                })
    except Exception:
        pass  # graceful degradation

    # CTL branching-time verification (FV-07)
    try:
        # Extract HMM transitions if available
        _ctl_trans = None
        _hmm_data = response.get("hmm_regime", {})
        if _hmm_data.get("transition_probs"):
            # HMM gives transition from current state only; use defaults for full matrix
            pass  # use default transitions, HMM single-row insufficient for full CTL

        ctl = compute_ctl_verification(omega_out, hmm_transitions=_ctl_trans)
        if ctl:
            response["ctl_verification"] = {
                "ef_recovery_possible": ctl.ef_recovery_possible,
                "ag_heal_works": ctl.ag_heal_works,
                "eg_stable_possible": ctl.eg_stable_possible,
                "verified_states": ctl.verified_states,
                "verification_time_ms": ctl.verification_time_ms,
                "bounded_steps": ctl.bounded_steps,
                "ctl_formulas": ctl.ctl_formulas,
            }
            # Wire into compliance: EU AI Act warning if healing not guaranteed
            if ctl.ag_heal_works is False and "compliance_result" in response:
                response["compliance_result"].setdefault("warnings", [])
                if isinstance(response["compliance_result"].get("warnings"), list):
                    response["compliance_result"]["warnings"].append(
                        "CTL_WARNING: healing convergence not guaranteed on all paths"
                    )
    except Exception:
        pass  # graceful degradation

    # Lyapunov Exponent chaos detection (S-03)
    _lyap_lambda = None
    try:
        _lyap_history = list(req.score_history) if req.score_history else []
        if len(_lyap_history) < 10 and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _lyk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                _lyr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_lyk}/0/99",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _lyr.ok:
                    _lyh = _lyr.json().get("result", [])
                    if _lyh:
                        _lyap_history = [float(x) for x in _lyh]
            except Exception:
                pass

        if len(_lyap_history) >= 10:
            lyap = compute_lyapunov_exponent(_lyap_history, omega_out)
            if lyap:
                response["lyapunov_exponent"] = {
                    "lambda_estimate": lyap.lambda_estimate,
                    "chaos_risk": lyap.chaos_risk,
                    "stability_class": lyap.stability_class,
                    "divergence_rate": lyap.divergence_rate,
                }
                _lyap_lambda = lyap.lambda_estimate

                # Wire into repair_plan
                if lyap.chaos_risk:
                    repair_plan_out.append({
                        "action": "CHAOS_WARNING",
                        "entry_id": "*",
                        "reason": "CHAOS WARNING: positive Lyapunov exponent — drift spiral risk",
                        "projected_improvement": 0,
                        "priority": "high",
                    })
    except Exception:
        pass  # graceful degradation

    # Banach Fixed-Point contraction (S-04)
    try:
        _ban_history = list(req.score_history) if req.score_history else []
        if len(_ban_history) < 5 and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _bk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                _br = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_bk}/0/99",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _br.ok:
                    _bh = _br.json().get("result", [])
                    if _bh:
                        _ban_history = [float(x) for x in _bh]
            except Exception:
                pass

        if len(_ban_history) >= 5:
            ban = compute_banach(_ban_history, omega_out)
            if ban:
                response["banach_contraction"] = {
                    "k_estimate": ban.k_estimate,
                    "contraction_guaranteed": ban.contraction_guaranteed,
                    "convergence_steps": ban.convergence_steps,
                    "fixed_point_estimate": ban.fixed_point_estimate,
                }
                if not ban.contraction_guaranteed:
                    repair_plan_out.append({
                        "action": "BANACH_WARNING",
                        "entry_id": "*",
                        "reason": "BANACH WARNING: heal loop not contracting — convergence not guaranteed",
                        "projected_improvement": 0,
                        "priority": "high",
                    })
    except Exception:
        pass  # graceful degradation

    # Hotelling T-squared control chart (S-05)
    try:
        _hot_key = f"hotelling_ref:{key_record.get('key_hash', 'default')}:{req.domain}"
        _hot_ref = None
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _hr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/GET/{_hot_key}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _hr.ok and _hr.json().get("result"):
                    _hot_ref = _json.loads(_hr.json()["result"])
            except Exception:
                pass

        hot = compute_hotelling_t2(result.component_breakdown, reference_data=_hot_ref)
        if hot:
            response["hotelling_t2"] = {
                "t2_statistic": hot.t2_statistic,
                "ucl": hot.ucl,
                "out_of_control": hot.out_of_control,
                "components_contributing": hot.components_contributing,
                "phase": hot.phase,
            }
            if hot.out_of_control:
                for e in entries:
                    at_risk_warnings.append({
                        "entry_id": e.id,
                        "importance_score": 0,
                        "voi_score": 0,
                        "warning": "hotelling_out_of_control",
                        "signal_breakdown": {},
                    })
    except Exception:
        pass  # graceful degradation

    # Fisher-Rao metric (IG-02)
    _fr_diag = None
    try:
        fr = compute_fisher_rao(result.component_breakdown)
        if fr:
            response["fisher_rao"] = {
                "metric_diagonal": fr.metric_diagonal,
                "condition_number": fr.condition_number,
                "geometry": fr.geometry,
            }
            _fr_diag = fr.metric_diagonal
    except Exception:
        pass

    # Geodesic Flow (IG-04) + Natural Gradient flag (IG-03)
    try:
        _ul = response.get("unified_loss", {})
        _ul_weights = _ul.get("lambda_weights", [])
        _ul_comps = _ul.get("components", {})
        if _ul_weights and _ul_comps:
            from scoring_engine.unified_loss import COMPONENT_NAMES
            _ul_losses = [_ul_comps.get(k, 0.0) for k in COMPONENT_NAMES]
            gf = compute_geodesic_flow(_ul_weights, _ul_losses, metric_diagonal=_fr_diag)
            if gf:
                response["geodesic_flow"] = {
                    "flow_magnitude": gf.flow_magnitude,
                    "parameter_velocity": gf.parameter_velocity,
                    "manifold_distance": gf.manifold_distance,
                }
            # IG-03: flag natural gradient usage in unified_loss
            if _fr_diag and "unified_loss" in response:
                response["unified_loss"]["natural_gradient_used"] = True
    except Exception:
        pass

    # Koopman Operator (OP-01)
    try:
        _koop_history = list(req.score_history) if req.score_history else []
        if len(_koop_history) < 10 and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _kk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                _kr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_kk}/0/99",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _kr.ok:
                    _kh = _kr.json().get("result", [])
                    if _kh:
                        _koop_history = [float(x) for x in _kh]
            except Exception:
                pass

        if len(_koop_history) >= 10:
            koop = compute_koopman(_koop_history, omega_out)
            if koop:
                response["koopman"] = {
                    "eigenvalues": koop.eigenvalues,
                    "dominant_mode": koop.dominant_mode,
                    "prediction_5": koop.prediction_5,
                    "stable": koop.stable,
                }
    except Exception:
        pass

    # Ergodicity (ET-01)
    try:
        _erg_history = list(req.score_history) if req.score_history else []
        if len(_erg_history) < 5 and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _ek = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                _er = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_ek}/0/99",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _er.ok:
                    _eh = _er.json().get("result", [])
                    if _eh:
                        _erg_history = [float(x) for x in _eh]
            except Exception:
                pass

        if len(_erg_history) >= 5:
            _comp_vals = list(result.component_breakdown.values())
            erg = compute_ergodicity(_erg_history, omega_out, _comp_vals)
            if erg:
                response["ergodicity"] = {
                    "time_average": erg.time_average,
                    "ensemble_average": erg.ensemble_average,
                    "delta": erg.delta,
                    "ergodic": erg.ergodic,
                    "interpretation": erg.interpretation,
                }
    except Exception:
        pass

    # Extended Freshness models (W-03/04/05)
    try:
        _ef_entries = [{"id": e.id, "type": e.type, "timestamp_age_days": e.timestamp_age_days} for e in entries]
        _ef_history = list(req.score_history) if req.score_history else None
        if (_ef_history is None or len(_ef_history) < 5) and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _efk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                _efr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_efk}/0/99",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _efr.ok:
                    _efh = _efr.json().get("result", [])
                    if _efh and len(_efh) >= 5:
                        _ef_history = [float(x) for x in _efh]
            except Exception:
                pass

        ef = compute_extended_freshness(_ef_entries, history=_ef_history)
        if ef:
            _ef_resp = {
                "gompertz": [{"entry_id": g.entry_id, "score": g.score} for g in ef.gompertz],
                "power_law": [{"entry_id": p.entry_id, "score": p.score, "half_life": p.half_life} for p in ef.power_law],
                "recommended_model": ef.recommended_model,
                "ensemble_freshness": ef.ensemble_freshness,
                "models_used": ef.models_used,
            }
            if ef.holt_winters:
                _ef_resp["holt_winters"] = [{"entry_id": h.entry_id, "score": h.score, "trend": h.trend} for h in ef.holt_winters]
            else:
                _ef_resp["holt_winters"] = None
            response["extended_freshness"] = _ef_resp

            # Wire into s_freshness: use ensemble_freshness
            if "component_breakdown" in response:
                fresh_score = (1.0 - ef.ensemble_freshness) * 100  # lower freshness = higher risk
                response["component_breakdown"]["s_freshness"] = round(min(100, fresh_score), 2)
    except Exception:
        pass  # graceful degradation

    # Persistent Homology (TDA-01)
    try:
        if len(entries) >= 3:
            _ph_entries = [{"id": e.id, "source_trust": e.source_trust,
                            "timestamp_age_days": e.timestamp_age_days,
                            "source_conflict": e.source_conflict,
                            "downstream_count": e.downstream_count} for e in entries]
            ph = compute_persistent_homology(_ph_entries)
            if ph:
                response["persistent_homology"] = {
                    "betti_0": [{"scale": b.scale, "count": b.count} for b in ph.betti_0],
                    "betti_1": [{"scale": b.scale, "count": b.count} for b in ph.betti_1],
                    "significant_features": ph.significant_features,
                    "structural_drift": ph.structural_drift,
                    "topology_summary": ph.topology_summary,
                }
    except Exception:
        pass

    # Ollivier-Ricci Curvature (TDA-04)
    try:
        if len(entries) >= 2:
            _rc_entries = [{"id": e.id, "source_trust": e.source_trust,
                            "timestamp_age_days": e.timestamp_age_days,
                            "source_conflict": e.source_conflict,
                            "downstream_count": e.downstream_count} for e in entries]
            rc = compute_ricci_curvature(_rc_entries)
            if rc:
                response["ricci_curvature"] = {
                    "edge_curvatures": [{"from": c.from_id, "to": c.to_id, "kappa": c.kappa} for c in rc.edge_curvatures],
                    "mean_curvature": rc.mean_curvature,
                    "negative_curvature_edges": [list(e) for e in rc.negative_curvature_edges],
                    "graph_health": rc.graph_health,
                }
                # Wire fragile edges into at_risk_warnings
                for from_id, to_id in rc.negative_curvature_edges:
                    kappa = next((c.kappa for c in rc.edge_curvatures if c.from_id == from_id and c.to_id == to_id), 0)
                    if kappa < -0.5:
                        at_risk_warnings.append({
                            "entry_id": from_id,
                            "importance_score": 0,
                            "voi_score": 0,
                            "warning": "ricci_fragile_connection",
                            "signal_breakdown": {"kappa": kappa, "connected_to": to_id},
                        })
    except Exception:
        pass

    # Recursive Colimit (Category Theory)
    _colimit_state = None
    try:
        _cl_key = f"colimit_state:{key_record.get('key_hash', 'default')}:{req.domain}"
        _cl_prev = None
        _cl_iter = 0
        _cl_min = None
        _cl_max = None
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _clr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/GET/{_cl_key}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _clr.ok and _clr.json().get("result"):
                    _cl_data = _json.loads(_clr.json()["result"])
                    _cl_prev = _cl_data.get("state")
                    _cl_iter = _cl_data.get("iteration", 0)
                    _cl_min = _cl_data.get("min")
                    _cl_max = _cl_data.get("max")
            except Exception:
                pass

        _omega_scores = list(result.component_breakdown.values())
        _h1 = response.get("consistency_analysis", {}).get("h1_rank", 0)
        cl = compute_recursive_colimit(_omega_scores, h1_rank=_h1, previous_state=_cl_prev,
                                        iteration=_cl_iter, min_observed=_cl_min, max_observed=_cl_max)
        if cl:
            response["recursive_colimit"] = {
                "global_state": cl.global_state,
                "state_velocity": cl.state_velocity,
                "colimit_stable": cl.colimit_stable,
                "h1_factor": cl.h1_factor,
                "iteration": cl.iteration,
            }
            _colimit_state = cl.global_state

            # Store in Redis
            if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
                try:
                    _raw = sum(_omega_scores) / max(len(_omega_scores), 1) * cl.h1_factor
                    _new_min = min(_cl_min or _raw, _raw)
                    _new_max = max(_cl_max or _raw, _raw)
                    _cl_store = _json.dumps({"state": cl.global_state, "iteration": cl.iteration,
                                             "min": _new_min, "max": _new_max})
                    http_requests.post(
                        f"{UPSTASH_REDIS_URL}/SET/{_cl_key}/{_cl_store}/EX/86400",
                        headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                        timeout=2,
                    )
                except Exception:
                    pass
    except Exception:
        pass

    # Cohomological Learning Gradient
    try:
        _fe_F = response.get("free_energy", {}).get("F", 0.0)
        _fr_diag_cg = response.get("fisher_rao", {}).get("metric_diagonal")
        _ul_weights_cg = response.get("unified_loss", {}).get("lambda_weights")
        _h1_cg = response.get("consistency_analysis", {}).get("h1_rank", 0)

        cg = compute_cohomological_gradient(
            free_energy_F=_fe_F, h1_rank=_h1_cg,
            fisher_rao_diagonal=_fr_diag_cg, lambda_weights=_ul_weights_cg,
        )
        if cg:
            response["cohomological_gradient"] = {
                "gradient_norm": cg.gradient_norm,
                "h1_contribution": cg.h1_contribution,
                "fim_contribution": cg.fim_contribution,
                "cohomological_update_used": cg.cohomological_update_used,
            }
            if cg.cohomological_update_used and "unified_loss" in response:
                response["unified_loss"]["cohomological_update_used"] = True
    except Exception:
        pass

    # Cox Proportional Hazard (W-06)
    try:
        _cox_entries = [{"source_trust": e.source_trust, "downstream_count": e.downstream_count,
                         "timestamp_age_days": e.timestamp_age_days} for e in entries]
        cox = compute_cox_hazard(_cox_entries)
        if cox:
            response["cox_hazard"] = {"hazard_rate": cox.hazard_rate, "survival_probability": cox.survival_probability, "high_risk": cox.high_risk}
            if cox.high_risk and "component_breakdown" in response:
                response["component_breakdown"]["s_freshness"] = round(min(100, response["component_breakdown"].get("s_freshness", 0) + 10), 2)
    except Exception:
        pass

    # Arrhenius Degradation (W-07)
    try:
        _arr_entries = [{"source_conflict": e.source_conflict, "timestamp_age_days": e.timestamp_age_days} for e in entries]
        arr = compute_arrhenius(_arr_entries)
        if arr:
            response["arrhenius"] = {"degradation_rate": arr.degradation_rate, "effective_lifetime": arr.effective_lifetime, "heat_index": arr.heat_index}
    except Exception:
        pass

    # OWA Provenance (P-05)
    try:
        _trusts = [e.source_trust for e in entries]
        owa = compute_owa(_trusts)
        if owa:
            response["owa_provenance"] = {"owa_score": owa.owa_score, "weights_used": owa.weights_used, "orness": owa.orness}
            if "component_breakdown" in response:
                response["component_breakdown"]["s_provenance"] = round(min(100, (1.0 - owa.owa_score) * 100), 2)
    except Exception:
        pass

    # Poisson Recall (R-03)
    try:
        _pr_key = f"poisson_lambda:{key_record.get('key_hash', 'default')}:{req.domain}"
        _pr_lam = 0.1
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _prr = http_requests.get(f"{UPSTASH_REDIS_URL}/GET/{_pr_key}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"}, timeout=2)
                if _prr.ok and _prr.json().get("result") is not None:
                    _pr_lam = float(_prr.json()["result"])
            except Exception:
                pass
        pr = compute_poisson_recall(_pr_lam)
        if pr:
            response["poisson_recall"] = {"lambda_rate": pr.lambda_rate, "expected_errors_10": pr.expected_errors_10, "error_probability": pr.error_probability}
            if "component_breakdown" in response:
                old_recall = response["component_breakdown"].get("r_recall", 0)
                response["component_breakdown"]["r_recall"] = round(min(100, old_recall + pr.error_probability * 20), 2)
    except Exception:
        pass

    # ROC AUC Monitoring (R-04)
    try:
        _roc_key = f"roc_history:{key_record.get('key_hash', 'default')}:{req.domain}"
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _rocr = http_requests.get(f"{UPSTASH_REDIS_URL}/GET/{_roc_key}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"}, timeout=2)
                if _rocr.ok and _rocr.json().get("result"):
                    _roc_data = _json.loads(_rocr.json()["result"])
                    _preds = _roc_data.get("predictions", [])
                    _acts = _roc_data.get("actuals", [])
                    roc = compute_roc_auc(_preds, _acts)
                    if roc:
                        response["roc_monitoring"] = {"auc_estimate": roc.auc_estimate, "model_degraded": roc.model_degraded, "retrain_recommended": roc.retrain_recommended}
            except Exception:
                pass
    except Exception:
        pass

    # Hawkes self-exciting process
    entry_ages = [e.timestamp_age_days for e in entries]
    hawkes = hawkes_from_entries(entry_ages)
    response["hawkes_intensity"] = {
        "current_lambda": hawkes.current_lambda,
        "baseline_mu": hawkes.baseline_mu,
        "excited": hawkes.excited,
        "burst_detected": hawkes.burst_detected,
    }

    # Copula dependence analysis
    s_fresh = result.component_breakdown.get("s_freshness", 0)
    s_drft = result.component_breakdown.get("s_drift", 0)
    copula = compute_copula(s_fresh, s_drft)
    response["copula_analysis"] = {
        "rho": copula.rho,
        "joint_risk": copula.joint_risk,
        "tail_dependence": copula.tail_dependence,
    }

    # Multivariate EWMA
    mewma = compute_mewma(result.component_breakdown)
    response["mewma"] = {
        "T2_stat": mewma.T2_stat,
        "control_limit": mewma.control_limit,
        "out_of_control": mewma.out_of_control,
        "monitored_components": mewma.monitored_components,
    }

    # RMT signal/noise separation
    try:
        rmt_entries = [{"id": e.id, "content": e.content, "prompt_embedding": e.prompt_embedding} for e in entries]
        rmt_result = compute_rmt(rmt_entries)
        if rmt_result:
            response["rmt_analysis"] = {
                "signal_eigenvalues": rmt_result.signal_eigenvalues,
                "noise_threshold": rmt_result.noise_threshold,
                "true_interference_count": rmt_result.true_interference_count,
                "noise_interference_count": rmt_result.noise_interference_count,
                "signal_ratio": rmt_result.signal_ratio,
            }
    except Exception:
        pass  # graceful degradation

    # Causal graph discovery (LiNGAM)
    try:
        cg_entries = [{"id": e.id, "content": e.content, "timestamp_age_days": e.timestamp_age_days,
                       "source_trust": e.source_trust, "source_conflict": e.source_conflict,
                       "downstream_count": e.downstream_count} for e in entries]
        cg = compute_causal_graph(cg_entries)
        if cg and cg.edges:
            response["causal_graph"] = {
                "edges": [{"from": e.from_id, "to": e.to_id, "strength": e.strength, "confirmed": e.confirmed} for e in cg.edges],
                "root_cause": cg.root_cause,
                "causal_chain": cg.causal_chain,
                "causal_explanation": cg.causal_explanation,
            }
    except Exception:
        pass  # graceful degradation

    # Spectral graph Laplacian analysis
    try:
        sp_entries = [{"id": e.id, "content": e.content, "prompt_embedding": e.prompt_embedding} for e in entries]
        sp = compute_spectral(sp_entries)
        if sp:
            response["spectral_analysis"] = {
                "fiedler_value": sp.fiedler_value,
                "spectral_gap": sp.spectral_gap,
                "graph_connectivity": sp.graph_connectivity,
                "cheeger_bound": sp.cheeger_bound,
                "mixing_time_estimate": sp.mixing_time_estimate,
            }
    except Exception:
        pass  # graceful degradation

    # Memory consolidation (Hopfield + MI)
    try:
        cons_entries = [{"id": e.id, "content": e.content, "prompt_embedding": e.prompt_embedding,
                         "source_trust": e.source_trust, "timestamp_age_days": e.timestamp_age_days}
                        for e in entries]
        cons = compute_consolidation(cons_entries)
        if cons:
            response["consolidation"] = {
                "scores": [{"entry_id": s.entry_id, "consolidation_score": s.consolidation_score, "stable": s.stable} for s in cons.scores],
                "mean_consolidation": cons.mean_consolidation,
                "fragile_entries": cons.fragile_entries,
                "replay_priority": cons.replay_priority,
            }
    except Exception:
        pass

    # Rate-Distortion optimal retention (RD-01)
    try:
        rd_entries = [{"id": e.id, "source_trust": e.source_trust,
                       "timestamp_age_days": e.timestamp_age_days,
                       "source_conflict": e.source_conflict,
                       "downstream_count": e.downstream_count} for e in entries]
        rd = compute_rate_distortion(rd_entries, omega_out, result.component_breakdown,
                                     system_health=100.0 - omega_out)
        if rd:
            response["rate_distortion"] = {
                "entries": [{"entry_id": r.entry_id, "information_value": r.information_value,
                             "distortion_cost": r.distortion_cost, "keep_score": r.keep_score,
                             "recommend_delete": r.recommend_delete} for r in rd.entries],
                "total_rate": rd.total_rate,
                "total_distortion": rd.total_distortion,
                "compression_ratio": rd.compression_ratio,
                "deletable_count": rd.deletable_count,
                "lambda_used": rd.lambda_used,
            }
            # Wire into repair_plan
            for r in rd.entries:
                if r.recommend_delete:
                    eid = r.entry_id if full_detail else ObfuscatedId.obfuscate(r.entry_id, session_key)
                    repair_plan_out.append({
                        "action": "DELETE",
                        "entry_id": eid,
                        "reason": f"Consider removing entry {eid} — low information value relative to distortion cost.",
                        "projected_improvement": round(r.distortion_cost * 0.5, 1),
                        "priority": "medium",
                    })
    except Exception:
        pass  # graceful degradation

    # Jump-Diffusion process (DS-04)
    jump_diffusion_result = None
    try:
        if req.score_history and len(req.score_history) >= 5:
            jump_diffusion_result = compute_jump_diffusion(req.score_history, omega_out)
            if jump_diffusion_result:
                response["jump_diffusion"] = {
                    "jump_detected": jump_diffusion_result.jump_detected,
                    "jump_size": jump_diffusion_result.jump_size,
                    "jump_rate_lambda": jump_diffusion_result.jump_rate_lambda,
                    "diffusion_sigma": jump_diffusion_result.diffusion_sigma,
                    "flash_crash_risk": jump_diffusion_result.flash_crash_risk,
                    "expected_next_jump": jump_diffusion_result.expected_next_jump,
                }
    except Exception:
        pass  # graceful degradation

    # Lévy Flight tail analysis (DS-07)
    levy_result = None
    try:
        levy_history = list(req.score_history) if req.score_history else []
        if len(levy_history) < 10 and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _lk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                _lr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_lk}/0/99",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _lr.ok:
                    _lhist = _lr.json().get("result", [])
                    if _lhist:
                        levy_history = [float(x) for x in _lhist]
            except Exception:
                pass

        if len(levy_history) >= 10:
            levy_result = compute_levy_flight(levy_history, omega_out)
            if levy_result:
                response["levy_flight"] = {
                    "alpha": levy_result.alpha,
                    "scale": levy_result.scale,
                    "heavy_tail_risk": levy_result.heavy_tail_risk,
                    "extreme_event_probability": levy_result.extreme_event_probability,
                    "tail_index": levy_result.tail_index,
                }
    except Exception:
        pass  # graceful degradation

    # Cascade risk: jump_detected AND burst_detected, OR all three (jump + burst + heavy tail)
    cascade_risk = False
    try:
        if jump_diffusion_result and jump_diffusion_result.jump_detected and hawkes.burst_detected:
            cascade_risk = True
        if levy_result and levy_result.heavy_tail_risk and jump_diffusion_result and jump_diffusion_result.jump_detected and hawkes.burst_detected:
            cascade_risk = True
    except Exception:
        pass
    response["cascade_risk"] = cascade_risk

    # Wire Lévy into repair_plan
    if levy_result and levy_result.heavy_tail_risk:
        repair_plan_out.append({
            "action": "MONITOR",
            "entry_id": "*",
            "reason": "Heavy-tail risk detected — extreme memory state changes possible. Increase monitoring frequency.",
            "projected_improvement": 0,
            "priority": "high",
        })

    # HMM Regime-Switching (DS-05)
    hmm_result = None
    try:
        if req.score_history and len(req.score_history) >= 20:
            hmm_result = compute_hmm_regime(req.score_history, omega_out)
            if hmm_result:
                response["hmm_regime"] = {
                    "current_state": hmm_result.current_state,
                    "state_probability": hmm_result.state_probability,
                    "transition_probs": hmm_result.transition_probs,
                    "regime_duration": hmm_result.regime_duration,
                }
    except Exception:
        pass  # graceful degradation

    # Regime collapse risk: HMM CRITICAL AND BOCPD regime_change simultaneously
    regime_collapse_risk = False
    try:
        if hmm_result and hmm_result.current_state == "CRITICAL":
            td = response.get("trend_detection", {})
            bocpd_data = td.get("bocpd", {})
            if bocpd_data.get("regime_change", False):
                regime_collapse_risk = True
    except Exception:
        pass
    response["regime_collapse_risk"] = regime_collapse_risk

    # Ornstein-Uhlenbeck mean-reversion (DS-06)
    ou_result = None
    try:
        # Build history: prefer score_history, fall back to Redis ring buffer
        ou_history = list(req.score_history) if req.score_history else []
        if len(ou_history) < 10 and UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _rk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                _rr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/LRANGE/{_rk}/0/99",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _rr.ok:
                    redis_hist = _rr.json().get("result", [])
                    if redis_hist:
                        ou_history = [float(x) for x in redis_hist]
            except Exception:
                pass

        if len(ou_history) >= 10:
            ou_result = compute_ou_process(ou_history, omega_out)
            if ou_result:
                response["ornstein_uhlenbeck"] = {
                    "mean_reverting": ou_result.mean_reverting,
                    "half_life": ou_result.half_life,
                    "expected_value_5": ou_result.expected_value_5,
                    "expected_value_10": ou_result.expected_value_10,
                    "equilibrium": ou_result.mu,
                    "current_deviation": ou_result.current_deviation,
                }

        # Push current score to Redis ring buffer (keep last 100)
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _rk = f"te_history:{key_record.get('key_hash', 'default')}:{req.domain}"
                http_requests.post(
                    f"{UPSTASH_REDIS_URL}/RPUSH/{_rk}/{omega_out}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                http_requests.post(
                    f"{UPSTASH_REDIS_URL}/LTRIM/{_rk}/-100/-1",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
            except Exception:
                pass
    except Exception:
        pass  # graceful degradation

    # Wire OU into repair_plan
    if ou_result:
        if ou_result.mean_reverting and ou_result.half_life < 10:
            repair_plan_out.append({
                "action": "WAIT",
                "entry_id": "*",
                "reason": f"Self-recovery expected in {ou_result.half_life:.1f} steps. Consider waiting before manual intervention.",
                "projected_improvement": round(abs(ou_result.current_deviation) * 0.5, 1),
                "priority": "low",
            })
        elif not ou_result.mean_reverting:
            repair_plan_out.append({
                "action": "MANUAL_HEAL",
                "entry_id": "*",
                "reason": "Memory state is not mean-reverting — manual healing recommended.",
                "projected_improvement": 0,
                "priority": "high",
            })

    # Sheaf consistency analysis
    if sheaf_result:
        response["consistency_analysis"] = {
            "consistency_score": sheaf_result.consistency_score,
            "h1_rank": sheaf_result.h1_rank,
            "inconsistent_pairs": [list(p) for p in sheaf_result.inconsistent_pairs],
            "auto_source_conflict": sheaf_result.auto_source_conflict,
        }

    # ZK Sheaf proof (SH-02): combine FV-06 ZK commitment + SH-01 sheaf cohomology
    try:
        zk_sheaf = compute_zk_sheaf_proof(sheaf_result, [e.id for e in entries])
        if zk_sheaf:
            response["zk_sheaf_proof"] = {
                "commitment": zk_sheaf.commitment,
                "proof_valid": zk_sheaf.proof_valid,
                "n_edges_verified": zk_sheaf.n_edges_verified,
                "nonce": zk_sheaf.nonce,
                "verified_at": zk_sheaf.verified_at,
            }
            # Wire into compliance: EU AI Act gets zk_consistency_proof when valid
            if zk_sheaf.proof_valid and "compliance_result" in response:
                response["compliance_result"]["zk_consistency_proof"] = True
    except Exception:
        pass  # graceful degradation

    # RL Q-learning adjustment
    rl = None
    try:
        rl = get_rl_adjustment(omega_out, result.component_breakdown, result.recommended_action, req.domain)
        response["rl_adjustment"] = {
            "q_value": rl.q_value,
            "rl_adjusted_action": rl.rl_adjusted_action,
            "learning_episodes": rl.learning_episodes,
            "confidence": rl.confidence,
        }
    except Exception:
        pass  # graceful degradation

    # Policy Gradient with Advantage (RL-02)
    try:
        from scoring_engine.rl_policy import _q_table, _state_key, _discretize, ACTIONS as RL_ACTIONS, ACTION_MAP
        _fresh = result.component_breakdown.get("s_freshness", 0)
        _drft = result.component_breakdown.get("s_drift", 0)
        _prov = result.component_breakdown.get("s_provenance", 0)
        _st = _state_key(omega_out, _fresh, _drft, _prov)
        _qv = _q_table.get_q_values(req.domain, _st)

        # Fetch temperature from Redis
        _pg_temp_key = f"pg_temperature:{key_record.get('key_hash', 'default')}:{req.domain}"
        _pg_temp = 1.0
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _ptr = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/GET/{_pg_temp_key}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _ptr.ok and _ptr.json().get("result") is not None:
                    _pg_temp = float(_ptr.json()["result"])
            except Exception:
                pass

        _current_idx = ACTION_MAP.get(result.recommended_action, 0)
        pg = compute_policy_gradient(_qv, _current_idx, _pg_temp)

        response["policy_gradient"] = {
            "action_probabilities": pg.action_probabilities,
            "advantage": pg.advantage,
            "temperature": pg.temperature,
            "policy_entropy": pg.policy_entropy,
            "exploration_mode": pg.exploration_mode,
        }

        # PG Override: consistent action across recommended_action and rl_adjusted_action
        _episodes = rl.learning_episodes if rl else 0
        if (_episodes >= 20
            and pg.advantage > 0.1
            and not pg.exploration_mode):
            response["recommended_action"] = pg.best_action
            if "rl_adjustment" in response:
                response["rl_adjustment"]["rl_adjusted_action"] = pg.best_action
            response["pg_override"] = True
    except Exception:
        pass  # graceful degradation

    if req.thread_id:
        response["thread_id"] = req.thread_id
        response["bucket_id"] = thread_bucket_id
        response["sample_rate"] = thread_sample_rate
    if req.use_pagerank:
        from scoring_engine import compute_authority_scores
        auth_scores = compute_authority_scores([e.id for e in entries])
        response["authority_scores"] = auth_scores
    if privacy_guarantee:
        response["privacy_guarantee"] = privacy_guarantee
    if optimizer_version:
        response["optimizer_version"] = optimizer_version
    if at_risk_warnings:
        if not full_detail:
            at_risk_warnings = [
                {**w, "entry_id": ObfuscatedId.obfuscate(w["entry_id"], session_key)}
                for w in at_risk_warnings
            ]
        response["at_risk_warnings"] = at_risk_warnings
    if stale_state_warning:
        response["stale_state_warning"] = stale_state_warning
    if surgical_result:
        response["surgical_result"] = surgical_result
        response["auto_tracked"] = auto_tracked

    # R_total normalized + StabilityScore (RD-01+)
    try:
        # Gather components from response (fallback 0.0 for missing)
        _dd = response.get("drift_details", {})
        _ad = _dd.get("alpha_divergence", {})
        _alpha_score = (_ad.get("alpha_0_5", 0) + _ad.get("alpha_1_5", 0) + _ad.get("alpha_2_0", 0)) / 3.0 / 100.0 if _ad else 0.0
        _s_drift = result.component_breakdown.get("s_drift", 0) / 100.0
        _s_interf = result.component_breakdown.get("s_interference", 0) / 100.0
        _sp = response.get("spectral_analysis", {})
        _fiedler = _sp.get("fiedler_value", 0)
        _mix_time = _sp.get("mixing_time_estimate", 0)

        response["r_total_normalized"] = compute_r_total(
            alpha_divergence_score=_alpha_score,
            s_drift=_s_drift,
            s_interference=_s_interf,
            omega_mem_final=omega_out,
            fiedler_value=_fiedler,
        )

        # StabilityScore 9 components
        _hmm = response.get("hmm_regime", {})
        _tp = _hmm.get("transition_probs", {})
        _p_trans = 1.0 - _tp.get("to_stable", 1.0) if _tp else 0.0
        _td = response.get("trend_detection", {})
        _bocpd = _td.get("bocpd", {})
        _run_len = _bocpd.get("current_run_length", 0)
        _hurst = min(1.0, _run_len / 50.0) if _run_len > 0 else 0.0
        _ca = response.get("consistency_analysis", {})
        _h1 = _ca.get("h1_rank", 0)
        _cg = response.get("causal_graph", {})
        _cg_edges = len(_cg.get("edges", [])) if _cg else 0
        _d_geo = min(2.0, _cg_edges / 5.0)

        # Get lyapunov lambda and colimit state if computed earlier
        _lyap_for_ss = response.get("lyapunov_exponent", {}).get("lambda_estimate")
        _colimit_for_ss = response.get("recursive_colimit", {}).get("global_state")

        ss = compute_stability_score(
            delta_alpha=_alpha_score,
            p_transition=_p_trans,
            omega_drift=_s_drift,
            omega_0=omega_out / 100.0,
            lambda_2=_fiedler,
            hurst=_hurst,
            h1_rank=float(_h1),
            tau_mix=_mix_time,
            d_geo_causal=_d_geo,
            lyapunov_lambda=_lyap_for_ss,
            colimit_state=_colimit_for_ss,
        )
        response["stability_score"] = {
            "score": ss.score,
            "components": ss.components,
            "interpretation": ss.interpretation,
            "component_count": ss.component_count,
        }
    except Exception:
        pass  # graceful degradation

    # Unified Loss L_v4
    try:
        # Fetch λ weights from Redis
        _lv4_key = f"lv4_weights:{key_record.get('key_hash', 'default')}:{req.domain}"
        _lv4_weights = None
        _lv4_update_count = 0
        if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
            try:
                _lv4r = http_requests.get(
                    f"{UPSTASH_REDIS_URL}/GET/{_lv4_key}",
                    headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                    timeout=2,
                )
                if _lv4r.ok and _lv4r.json().get("result"):
                    import json as _lv4_json
                    _lv4_data = _lv4_json.loads(_lv4r.json()["result"])
                    _lv4_weights = _lv4_data.get("weights")
                    _lv4_update_count = _lv4_data.get("update_count", 0)
            except Exception:
                pass

        # Gather loss components from response
        _fe = response.get("free_energy", {})
        _rl = response.get("rl_adjustment", {})
        _cons = response.get("consolidation", {})
        _zks = response.get("zk_sheaf_proof", {})
        _ou = response.get("ornstein_uhlenbeck", {})
        _lf = response.get("levy_flight", {})
        _jd = response.get("jump_diffusion", {})
        _ss = response.get("stability_score", {})

        ul = compute_unified_loss(
            L_IB=_fe.get("elbo", 0.0),
            L_RL=abs(_rl.get("q_value", 0.0)),
            L_EWC=_cons.get("mean_consolidation", 0.0),
            L_SH=float(_zks.get("n_edges_verified", 0)) * (0 if _zks.get("proof_valid", True) else 1),
            L_HG=abs(_ou.get("current_deviation", 0.0)),
            L_FE=_fe.get("F", 0.0),
            L_OT=response.get("drift_details", {}).get("wasserstein", 0.0),
            T_XY=response.get("info_thermodynamics", {}).get("max_flow", 0.0),
            L_LDT=_lf.get("extreme_event_probability", 0.0),
            Var_dN=_jd.get("jump_rate_lambda", 0.0),
            L_CA=1.0 - _ss.get("score", 1.0),
            lambda_weights=_lv4_weights,
            geodesic_update_count=_lv4_update_count,
        )
        response["unified_loss"] = {
            "L_v4": ul.L_v4,
            "components": ul.components,
            "lambda_weights": ul.lambda_weights,
            "dominant_loss": ul.dominant_loss,
            "geodesic_update_count": ul.geodesic_update_count,
        }
    except Exception:
        pass  # graceful degradation

    # Audit log
    _audit_log("preflight", request_id, key_record, result.recommended_action, omega_out)

    # Webhook dispatch
    entry_ids = [e.id for e in entries]
    _dispatch_webhooks(result.recommended_action, request_id, omega_out, entry_ids)

    # Metrics + tracing
    _duration = _time.monotonic() - _t_start
    _metrics.record_preflight(result.recommended_action, omega_out, _duration)
    response["_trace"] = {
        "span": "preflight",
        "api_key_id": key_record.get("key_hash", "in_memory"),
        "decision": result.recommended_action,
        "omega_score": omega_out,
        "request_id": request_id,
        "duration_ms": round(_duration * 1000, 2),
    }

    return response
