"""Sgraal CLI — memory governance from the command line."""
import click
import json
import os
import sys

DEFAULT_URL = "https://api.sgraal.com"


def _get_config():
    cfg_path = os.path.expanduser("~/.sgraal/config.yml")
    if os.path.exists(cfg_path):
        import yaml
        with open(cfg_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _get_key():
    return os.environ.get("SGRAAL_API_KEY") or _get_config().get("api_key", "sg_demo_playground")


def _get_url():
    return os.environ.get("SGRAAL_API_URL") or _get_config().get("api_url", DEFAULT_URL)


@click.group()
def cli():
    """Sgraal Memory Governance CLI."""
    pass


@cli.command()
@click.option("--file", "-f", required=True, help="Path to JSONL memory state file")
@click.option("--domain", "-d", default="general", help="Domain")
@click.option("--action", "-a", default="reversible", help="Action type")
@click.option("--key", "-k", default=None, help="API key (or set SGRAAL_API_KEY)")
def preflight(file, domain, action, key):
    """Run preflight validation on a memory state file."""
    import requests
    api_key = key or _get_key()
    api_url = _get_url()
    with open(file) as f:
        entries = [json.loads(line) for line in f if line.strip()]
    resp = requests.post(f"{api_url}/v1/preflight",
                         json={"memory_state": entries, "domain": domain, "action_type": action},
                         headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                         timeout=30)
    if resp.status_code != 200:
        click.echo(f"Error: HTTP {resp.status_code}", err=True)
        sys.exit(1)
    data = resp.json()
    click.echo(f"Decision: {data.get('recommended_action')}")
    click.echo(f"Omega:    {data.get('omega_mem_final')}")
    click.echo(f"Attack:   {data.get('attack_surface_level')}")
    if data.get("recommended_action") == "BLOCK":
        sys.exit(1)


@cli.command()
@click.option("--key", "-k", default=None, help="API key")
def score(key):
    """Show governance score for configured API key."""
    import requests
    api_key = key or _get_key()
    resp = requests.get(f"{_get_url()}/v1/governance-score",
                        headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
    data = resp.json()
    if data.get("governance_score") is None:
        click.echo(f"Insufficient history ({data.get('total_governed_actions', 0)} actions)")
    else:
        click.echo(f"Governance Score: {data['governance_score']}/100")
        click.echo(f"Total governed:   {data['total_governed_actions']}")


@cli.command()
@click.option("--signature", required=True)
@click.option("--input-hash", required=True)
@click.option("--omega", required=True, type=float)
@click.option("--decision", required=True)
@click.option("--request-id", required=True)
def verify(signature, input_hash, omega, decision, request_id):
    """Verify a portable safety attestation."""
    import requests
    resp = requests.post(f"{_get_url()}/v1/verify-attestation",
                         json={"input_hash": input_hash, "omega": omega, "decision": decision,
                                "request_id": request_id, "proof_signature": signature}, timeout=10)
    data = resp.json()
    if data.get("valid"):
        click.echo("✅ Attestation verified")
    else:
        click.echo("❌ Invalid attestation")
        sys.exit(1)


@cli.group()
def config():
    """Manage .sgraal configuration."""
    pass


@config.command("init")
def config_init():
    """Create .sgraal config file in current directory."""
    cfg = {"version": "1.0", "domain": "general", "action_type": "reversible",
           "policy": {"block_omega": 70, "warn_omega": 40, "ask_user_omega": 55}}
    with open(".sgraal", "w") as f:
        import yaml
        yaml.dump(cfg, f, default_flow_style=False)
    click.echo("Created .sgraal config file")


@config.command("validate")
def config_validate():
    """Validate existing .sgraal config file."""
    if not os.path.exists(".sgraal"):
        click.echo("No .sgraal file found", err=True)
        sys.exit(1)
    import yaml
    with open(".sgraal") as f:
        cfg = yaml.safe_load(f)
    import requests
    resp = requests.post(f"{_get_url()}/v1/config/validate",
                         json={"config": cfg},
                         headers={"Authorization": f"Bearer {_get_key()}"}, timeout=10)
    data = resp.json()
    if data.get("valid"):
        click.echo("✅ Config valid")
    else:
        click.echo("❌ Config invalid:")
        for e in data.get("errors", []):
            click.echo(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
