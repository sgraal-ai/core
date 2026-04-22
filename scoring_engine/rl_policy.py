from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("sgraal.rl_policy")

ACTIONS = ["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]
ACTION_MAP = {a: i for i, a in enumerate(ACTIONS)}
DOMAINS = ["general", "customer_support", "coding", "legal", "fintech", "medical"]

# Hyperparameters
ALPHA = 0.1   # learning rate
GAMMA = 0.9   # discount factor
COLD_START_THRESHOLD = 10  # minimum episodes before RL can override


@dataclass
class RLAdjustment:
    q_value: float
    rl_adjusted_action: str
    learning_episodes: int
    confidence: float


def _discretize(value: float) -> int:
    """Discretize a 0–100 score into 4 bins: 0=[0-25], 1=[26-50], 2=[51-75], 3=[76-100]."""
    if value <= 25:
        return 0
    if value <= 50:
        return 1
    if value <= 75:
        return 2
    return 3


def _state_key(omega: float, freshness: float, drift: float, provenance: float) -> str:
    """Encode state as string key from 4 discretized components."""
    bins = [
        _discretize(omega),
        _discretize(freshness),
        _discretize(drift),
        _discretize(provenance),
    ]
    return f"{bins[0]}:{bins[1]}:{bins[2]}:{bins[3]}"


def compute_reward(outcome_status: str, action: str) -> float:
    """Compute reward signal from outcome.

    +1.0  success
    -1.0  failure
    -2.0  failure AND action was USE_MEMORY (should have blocked)
    +0.5  partial (mixed result)
    """
    if outcome_status == "success":
        return 1.0
    if outcome_status == "failure":
        return -2.0 if action == "USE_MEMORY" else -1.0
    if outcome_status == "partial":
        return 0.5
    return 0.0


class QTable:
    """Q-table with Redis persistence across deploys.

    Maintains separate Q-tables per domain. On every update, the affected
    domain's table + episode count + timestamp are written to Redis. On
    first access per domain, the table is loaded from Redis if available.

    Redis keys:
      sgraal:rl_qtable:{domain}      — JSON dict of state→[Q values]
      sgraal:rl_episodes:{domain}    — int episode count
      sgraal:rl_last_update:{domain} — ISO timestamp

    Fail-safe: Redis failures never crash. If Redis is down, learning
    continues in memory (just won't survive the next deploy).
    """

    def __init__(self):
        self._tables: dict[str, dict[str, list[float]]] = {}
        self._episodes: dict[str, int] = {}
        self._last_update: dict[str, str] = {}
        self._loaded_from_redis: dict[str, bool] = {}
        # Lazy Redis import — scoring_engine should not hard-depend on api.redis_state
        self._redis_get = None
        self._redis_set = None
        self._redis_initialized = False

    def _init_redis(self) -> None:
        """Lazy-init Redis helpers. Called once on first use."""
        if self._redis_initialized:
            return
        self._redis_initialized = True
        try:
            from api.redis_state import redis_get, redis_set
            self._redis_get = redis_get
            self._redis_set = redis_set
        except Exception:
            logger.debug("RL Redis persistence unavailable — learning is memory-only")

    def _load_from_redis(self, domain: str) -> None:
        """Load Q-table for a domain from Redis (if not already loaded)."""
        if domain in self._loaded_from_redis:
            return  # already attempted
        self._loaded_from_redis[domain] = False
        self._init_redis()
        if not self._redis_get:
            return
        try:
            table_data = self._redis_get(f"sgraal:rl_qtable:{domain}")
            episodes = self._redis_get(f"sgraal:rl_episodes:{domain}")
            last_update = self._redis_get(f"sgraal:rl_last_update:{domain}")
            if isinstance(table_data, dict) and table_data:
                self._tables[domain] = table_data
                self._loaded_from_redis[domain] = True
                logger.info("RL Q-table loaded from Redis for domain=%s (%d states)",
                            domain, len(table_data))
            if isinstance(episodes, int):
                self._episodes[domain] = episodes
            elif isinstance(episodes, str) and episodes.isdigit():
                self._episodes[domain] = int(episodes)
            if isinstance(last_update, str):
                self._last_update[domain] = last_update
        except Exception as e:
            logger.debug("RL Redis load failed for domain=%s: %s", domain, e)

    def _persist_to_redis(self, domain: str) -> None:
        """Write Q-table for a domain to Redis (best-effort)."""
        self._init_redis()
        if not self._redis_set:
            return
        try:
            self._redis_set(f"sgraal:rl_qtable:{domain}", self._tables.get(domain, {}), ttl=7776000)
            self._redis_set(f"sgraal:rl_episodes:{domain}", self._episodes.get(domain, 0), ttl=7776000)
            ts = datetime.now(timezone.utc).isoformat()
            self._redis_set(f"sgraal:rl_last_update:{domain}", ts, ttl=7776000)
            self._last_update[domain] = ts
        except Exception as e:
            logger.debug("RL Redis persist failed for domain=%s: %s", domain, e)

    def _get_domain_table(self, domain: str) -> dict[str, list[float]]:
        self._load_from_redis(domain)  # lazy load on first access
        if domain not in self._tables:
            self._tables[domain] = {}
        return self._tables[domain]

    def get_q_values(self, domain: str, state: str) -> list[float]:
        table = self._get_domain_table(domain)
        if state not in table:
            table[state] = [0.0, 0.0, 0.0, 0.0]
        return table[state]

    def update(
        self,
        domain: str,
        state: str,
        action_idx: int,
        reward: float,
        next_state: Optional[str] = None,
    ) -> None:
        """Q(s,a) ← Q(s,a) + α·(r + γ·max Q(s',a') - Q(s,a))"""
        q_values = self.get_q_values(domain, state)
        old_q = q_values[action_idx]

        if next_state is not None:
            next_q = self.get_q_values(domain, next_state)
            max_next = max(next_q)
        else:
            max_next = 0.0  # terminal state

        q_values[action_idx] = old_q + ALPHA * (reward + GAMMA * max_next - old_q)

        # Increment episode count
        self._episodes[domain] = self._episodes.get(domain, 0) + 1

        # Persist to Redis after every update (best-effort, non-blocking)
        self._persist_to_redis(domain)

    def get_episodes(self, domain: str) -> int:
        self._load_from_redis(domain)
        return self._episodes.get(domain, 0)

    def get_best_action(self, domain: str, state: str) -> tuple[int, float]:
        """Return (action_idx, q_value) for the best action."""
        q_values = self.get_q_values(domain, state)
        best_idx = 0
        best_val = q_values[0]
        for i in range(1, len(q_values)):
            if q_values[i] > best_val:
                best_val = q_values[i]
                best_idx = i
        return best_idx, best_val

    def to_dict(self) -> dict:
        return {"tables": self._tables, "episodes": self._episodes}

    def from_dict(self, data: dict) -> None:
        self._tables = data.get("tables", {})
        self._episodes = data.get("episodes", {})

    def persistence_status(self) -> dict:
        """Return per-domain persistence metadata for /v1/scheduler/status."""
        result = {}
        for domain in DOMAINS:
            self._load_from_redis(domain)
            result[domain] = {
                "episodes": self._episodes.get(domain, 0),
                "last_update": self._last_update.get(domain),
                "loaded_from_redis": self._loaded_from_redis.get(domain, False),
                "states_populated": len(self._tables.get(domain, {})),
            }
        return result


# Global Q-table instance
_q_table = QTable()


def get_rl_adjustment(
    omega_mem_final: float,
    component_breakdown: dict[str, float],
    recommended_action: str,
    domain: str = "general",
) -> RLAdjustment:
    """Get RL-adjusted action recommendation.

    Cold start: minimum COLD_START_THRESHOLD episodes before RL can override.
    """
    freshness = component_breakdown.get("s_freshness", 0)
    drift = component_breakdown.get("s_drift", 0)
    provenance = component_breakdown.get("s_provenance", 0)

    state = _state_key(omega_mem_final, freshness, drift, provenance)
    episodes = _q_table.get_episodes(domain)
    best_action_idx, q_value = _q_table.get_best_action(domain, state)
    best_action = ACTIONS[best_action_idx]

    # Cold start: don't override until enough episodes
    if episodes < COLD_START_THRESHOLD:
        return RLAdjustment(
            q_value=round(q_value, 4),
            rl_adjusted_action=recommended_action,
            learning_episodes=episodes,
            confidence=0.0,
        )

    # Confidence: based on episode count (saturates at 100 episodes)
    confidence = round(min(1.0, episodes / 100.0), 2)

    return RLAdjustment(
        q_value=round(q_value, 4),
        rl_adjusted_action=best_action,
        learning_episodes=episodes,
        confidence=confidence,
    )


def update_from_outcome(
    omega_mem_final: float,
    component_breakdown: dict[str, float],
    action: str,
    outcome_status: str,
    domain: str = "general",
) -> float:
    """Update Q-table from an outcome. Returns the reward."""
    freshness = component_breakdown.get("s_freshness", 0)
    drift = component_breakdown.get("s_drift", 0)
    provenance = component_breakdown.get("s_provenance", 0)

    state = _state_key(omega_mem_final, freshness, drift, provenance)
    action_idx = ACTION_MAP.get(action, 0)
    reward = compute_reward(outcome_status, action)

    _q_table.update(domain, state, action_idx, reward)
    return reward


def get_q_table() -> QTable:
    """Get the global Q-table (for testing)."""
    return _q_table


def reset_q_table() -> None:
    """Reset global Q-table (for testing)."""
    global _q_table
    _q_table = QTable()
