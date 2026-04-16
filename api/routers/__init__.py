"""Router modules for Sgraal API.

Each file in this package contains a focused APIRouter for a specific
endpoint group. The main FastAPI app in api/main.py includes these routers.

Shared state (API_KEYS, _outcomes, verify_api_key, _check_rate_limit, etc.)
currently lives in api/main.py. Routers import what they need from there.
"""
