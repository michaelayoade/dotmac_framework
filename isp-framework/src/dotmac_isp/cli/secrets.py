"""CLI tool for managing encrypted secrets."""

import click
import sys
from pathlib import Path
from typing import Optional

from dotmac_isp.shared.secrets import (
    SecretsManager,
    setup_production_secrets,
    generate_jwt_secret,
    generate_database_password,
    generate_api_key,
)


@click.group()
@click.option(
    "--secrets-dir", type=click.Path(path_type=Path), help="Custom secrets directory"
)
@click.pass_context
def secrets(ctx: click.Context, secrets_dir: Optional[Path]):
    """Manage encrypted secrets for the DotMac ISP Framework."""
    ctx.ensure_object(dict)
    ctx.obj["secrets_manager"] = SecretsManager(secrets_dir)


@secrets.command()
@click.argument("name")
@click.argument("value")
@click.pass_context
def set(ctx: click.Context, name: str, value: str):
    """Store an encrypted secret."""
    manager: SecretsManager = ctx.obj["secrets_manager"]
    manager.store_secret(name, value)
    click.echo(f"✅ Secret '{name}' stored successfully")


@secrets.command()
@click.argument("name")
@click.pass_context
def get(ctx: click.Context, name: str):
    """Retrieve and decrypt a secret."""
    manager: SecretsManager = ctx.obj["secrets_manager"]
    value = manager.get_secret(name)
    if value:
        click.echo(value)
    else:
        click.echo(f"❌ Secret '{name}' not found", err=True)
        sys.exit(1)


@secrets.command()
@click.argument("name")
@click.pass_context
def delete(ctx: click.Context, name: str):
    """Delete a secret."""
    manager: SecretsManager = ctx.obj["secrets_manager"]
    if click.confirm(f"Are you sure you want to delete secret '{name}'?"):
        if manager.delete_secret(name):
            click.echo(f"✅ Secret '{name}' deleted successfully")
        else:
            click.echo(f"❌ Secret '{name}' not found", err=True)
            sys.exit(1)


@secrets.command()
@click.pass_context
def list(ctx: click.Context):
    """List all stored secret names."""
    manager: SecretsManager = ctx.obj["secrets_manager"]
    secret_names = manager.list_secrets()
    if secret_names:
        click.echo("Stored secrets:")
        for name in sorted(secret_names):
            click.echo(f"  • {name}")
    else:
        click.echo("No secrets stored")


@secrets.command()
@click.option(
    "--show-values",
    is_flag=True,
    help="Show generated secret values (DANGER: only for development)",
)
@click.pass_context
def generate(ctx: click.Context, show_values: bool):
    """Generate common secret types."""
    click.echo("Generating secure secrets:")

    secrets_data = {
        "jwt_secret": generate_jwt_secret(),
        "db_password": generate_database_password(),
        "api_key": generate_api_key(),
    }

    for name, value in secrets_data.items():
        if show_values:
            click.echo(f"  {name}: {value}")
        else:
            click.echo(f"  {name}: [generated - use 'secrets get {name}' to view]")

    if not show_values:
        click.echo("\n⚠️  Use --show-values flag to display values (development only)")


@secrets.command()
@click.option("--force", is_flag=True, help="Overwrite existing secrets")
@click.pass_context
def setup_production(ctx: click.Context, force: bool):
    """Set up all required secrets for production deployment."""
    manager: SecretsManager = ctx.obj["secrets_manager"]

    # Check if any production secrets already exist
    existing_secrets = manager.list_secrets()
    production_secret_names = [
        "jwt_secret_key",
        "database_password",
        "redis_password",
        "admin_api_key",
        "webhook_secret",
        "encryption_key",
    ]

    conflicts = [name for name in production_secret_names if name in existing_secrets]

    if conflicts and not force:
        click.echo("❌ Some production secrets already exist:")
        for name in conflicts:
            click.echo(f"  • {name}")
        click.echo("\nUse --force to overwrite existing secrets")
        sys.exit(1)

    if conflicts and force:
        click.echo("⚠️  Overwriting existing production secrets")

    click.echo("Setting up production secrets...")
    production_secrets = setup_production_secrets()

    click.echo("✅ Production secrets generated and stored:")
    for name in production_secrets:
        click.echo(f"  • {name}")

    click.echo("\n📋 Environment variables to set:")
    click.echo(f"export JWT_SECRET_KEY=$(dotmac-secrets get jwt_secret_key)")
    click.echo(f"export DATABASE_PASSWORD=$(dotmac-secrets get database_password)")
    click.echo(f"export REDIS_PASSWORD=$(dotmac-secrets get redis_password)")


@secrets.command()
@click.pass_context
def export_env(ctx: click.Context):
    """Export secrets as environment variable commands."""
    manager: SecretsManager = ctx.obj["secrets_manager"]
    secret_names = manager.list_secrets()

    if not secret_names:
        click.echo("No secrets to export")
        return

    click.echo("# Export commands for secrets:")
    for name in sorted(secret_names):
        env_name = name.upper()
        click.echo(f'export {env_name}="$(dotmac-secrets get {name})"')


@secrets.command()
@click.argument("name")
@click.option(
    "--type",
    "secret_type",
    type=click.Choice(["jwt", "password", "api_key"]),
    default="password",
    help="Type of secret to generate",
)
@click.pass_context
def generate_and_store(ctx: click.Context, name: str, secret_type: str):
    """Generate and store a new secret of the specified type."""
    manager: SecretsManager = ctx.obj["secrets_manager"]

    if secret_type == "jwt":
        value = generate_jwt_secret()
    elif secret_type == "api_key":
        value = generate_api_key()
    else:  # password
        value = generate_database_password()

    manager.store_secret(name, value)
    click.echo(f"✅ Generated and stored {secret_type} secret '{name}'")


if __name__ == "__main__":
    secrets()
