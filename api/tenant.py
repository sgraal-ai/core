"""Tenant isolation context — structural enforcement of per-tenant data access.

Every endpoint that touches tenant-scoped data should declare:
    tenant: TenantContext = Depends(get_tenant_context)

TenantContext provides methods for scoping dict keys, filtering lists,
verifying ownership, and tagging new records with the tenant's key_hash.
This replaces ad-hoc _safe_key_hash + manual filtering patterns.

NOTE: get_tenant_context depends on verify_api_key from api.main.
Import order: api.main imports this module AFTER verify_api_key is defined.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException


@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context — constructed once per request."""

    key_hash: str       # SHA-256 hash from _safe_key_hash (never empty)
    customer_id: str    # For team/billing ownership checks
    is_demo: bool       # True for demo/playground keys

    def scoped_key(self, *parts: str) -> str:
        """Build a tenant-scoped dict key: {key_hash}:{part1}:{part2}:..."""
        return ":".join([self.key_hash] + list(parts))

    def redis_key(self, prefix: str, *parts: str) -> str:
        """Build a tenant-scoped Redis key: {prefix}:{key_hash}:{parts}"""
        return ":".join([prefix, self.key_hash] + list(parts))

    def filter_list(self, items: list, key_field: str = "key_hash") -> list:
        """Filter a list of dicts to only those belonging to this tenant."""
        return [item for item in items if isinstance(item, dict) and item.get(key_field) == self.key_hash]

    def owns(self, item: Optional[dict], key_field: str = "key_hash") -> bool:
        """Check if a dict item belongs to this tenant. Returns False for None or missing key."""
        if not isinstance(item, dict):
            return False
        stored = item.get(key_field)
        if not stored:
            return False
        return stored == self.key_hash

    def assert_owns(self, item: Optional[dict], key_field: str = "key_hash",
                    detail: str = "Not authorized for this resource") -> None:
        """Raise 403 if item doesn't belong to this tenant, 404 if item is None."""
        if item is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        if not self.owns(item, key_field):
            raise HTTPException(status_code=403, detail=detail)

    def tag(self, item: dict) -> dict:
        """Add key_hash to an item before storage. Returns the same dict (mutated)."""
        item["key_hash"] = self.key_hash
        return item

    def supabase_filter(self, url: str) -> str:
        """Append api_key_hash=eq.{key_hash} filter to a Supabase REST URL."""
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}api_key_hash=eq.{self.key_hash}"


def create_tenant_context(key_record: dict, safe_key_hash_fn) -> TenantContext:
    """Create a TenantContext from an authenticated key record.

    This is the non-FastAPI version — used when you already have key_record
    and _safe_key_hash available (e.g., inside _preflight_internal).

    For endpoint dependencies, use the Depends-based version registered
    in api/main.py:
        tenant: TenantContext = Depends(get_tenant_context)
    """
    return TenantContext(
        key_hash=safe_key_hash_fn(key_record),
        customer_id=key_record.get("customer_id", ""),
        is_demo=key_record.get("demo", False),
    )
