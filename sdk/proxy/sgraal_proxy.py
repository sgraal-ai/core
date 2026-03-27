"""Sgraal Native Proxy."""
from __future__ import annotations

def create_proxy_app(sgraal_key: str):
    from fastapi import FastAPI
    app = FastAPI(title="Sgraal Proxy")
    return app
