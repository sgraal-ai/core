from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Literal, Optional
import sys, os
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
from scoring_engine import compute, MemoryEntry, PreflightResult, compute_importance, compute_importance_with_voi, ClientOptimizer, ComplianceEngine, ComplianceProfile, HealingPolicyMatrix, PolicyVerifier, KalmanForecaster, MemoryDependencyGraph, MemoryAccessTracker, ObfuscatedId, ReasonAbstractor, ZKAssurance, ThreadManager, compute_shapley_values, compute_lyapunov, LaplaceMechanism, compute_drift_metrics, detect_trend, compute_calibration, hawkes_from_entries, compute_copula, compute_mewma, compute_sheaf_consistency, get_rl_adjustment, update_from_outcome, compute_bocpd, compute_rmt, compute_causal_graph, compute_spectral, compute_consolidation, compute_jump_diffusion, compute_hmm_regime, compute_zk_sheaf_proof, compute_ou_process, compute_free_energy

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

    resp = {
        "outcome_id": req.outcome_id,
        "status": req.status,
        "closed_at": now.isoformat(),
    }
    if rl_reward is not None:
        resp["rl_reward"] = rl_reward
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
    }
    if drift.alpha_divergence:
        dd["alpha_divergence"] = {
            "alpha_0_5": drift.alpha_divergence.alpha_0_5,
            "alpha_1_5": drift.alpha_divergence.alpha_1_5,
            "alpha_2_0": drift.alpha_divergence.alpha_2_0,
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

        response["trend_detection"] = td

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

    # Cascade risk: jump_detected AND hawkes burst_detected simultaneously
    cascade_risk = False
    try:
        if jump_diffusion_result and jump_diffusion_result.jump_detected and hawkes.burst_detected:
            cascade_risk = True
    except Exception:
        pass
    response["cascade_risk"] = cascade_risk

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
