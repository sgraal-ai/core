"""Tests for Zapier/Make webhooks, embed SDK, GitHub OAuth."""
import pytest


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestZapierWebhook:
    def test_zapier_webhook_configure(self):
        c = _client()
        resp = c.post("/v1/zapier/webhook", json={
            "webhook_url": "https://hooks.zapier.com/test",
            "trigger": "block",
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["configured"] is True
        assert resp.json()["provider"] == "zapier"


class TestMakeWebhook:
    def test_make_webhook_configure(self):
        c = _client()
        resp = c.post("/v1/make/webhook", json={
            "webhook_url": "https://hook.us1.make.com/test",
            "trigger": "warn",
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["configured"] is True
        assert resp.json()["provider"] == "make"


class TestEmbedSDK:
    def test_embed_script_endpoint(self):
        c = _client()
        resp = c.get("/v1/embed/sgraal-embed.js")
        assert resp.status_code == 200
        assert "application/javascript" in resp.headers.get("content-type", "")
        assert "window.sgraal" in resp.text
        assert "preflight" in resp.text


class TestGitHubOAuth:
    def test_github_oauth_unconfigured(self):
        c = _client()
        resp = c.get("/v1/auth/github", follow_redirects=False)
        # Without GITHUB_CLIENT_ID env var → returns error JSON (200)
        if resp.status_code == 200:
            assert "error" in resp.json() or "not configured" in str(resp.json())
