"""DotMac Management CLI.

Provides administrative commands such as security bootstrap.
"""

import asyncio
import os
import sys

import click
from dotmac_management.core.bootstrap import (
    bootstrap_manager,
    run_bootstrap_if_needed,
)
from dotmac_shared.core.logging import get_logger
from sqlalchemy.exc import SQLAlchemyError

logger = get_logger(__name__)


def _validate_bootstrap_env() -> list[str]:
    """Validate required environment variables for bootstrap.

    Returns a list of issue strings. Empty list means validation passed.
    """
    issues: list[str] = []
    email = os.getenv("AUTH_ADMIN_EMAIL")
    password = os.getenv("AUTH_INITIAL_ADMIN_PASSWORD")

    if not email:
        issues.append("Missing AUTH_ADMIN_EMAIL")
    elif "@" not in email:
        issues.append("AUTH_ADMIN_EMAIL must be a valid email address")

    if not password:
        issues.append("Missing AUTH_INITIAL_ADMIN_PASSWORD")
    elif len(password) < 12:
        issues.append("AUTH_INITIAL_ADMIN_PASSWORD must be at least 12 characters")

    return issues


@click.group()
def main() -> None:
    """DotMac Management CLI."""


@main.command()
@click.option(
    "--check-only",
    is_flag=True,
    default=False,
    help="Only validate environment variables and imports; do not touch the database.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Run bootstrap even if it appears already completed.",
)
def bootstrap(check_only: bool, force: bool) -> None:
    """Run or validate the Management platform security bootstrap."""
    # Always validate env first so CI can enforce secret presence/strength
    issues = _validate_bootstrap_env()
    if issues:
        for issue in issues:
            logger.error(issue)
        if check_only:
            click.echo("❌ Bootstrap environment validation failed", err=True)
            sys.exit(1)
        # In run mode, still fail fast if env is invalid
        click.echo("❌ Bootstrap cannot run due to invalid/missing environment", err=True)
        sys.exit(1)

    if check_only:
        logger.info("Bootstrap environment variables are present and valid")
        click.echo("✅ Bootstrap environment validated")
        return

    # Run mode
    try:
        if not force and not bootstrap_manager.should_bootstrap():
            logger.info("Management platform already bootstrapped; skipping")
            click.echo("ℹ️ Bootstrap not needed")
            return

        # Execute async bootstrap
        completed = asyncio.run(run_bootstrap_if_needed())
        if completed:
            click.echo("✅ Security bootstrap completed successfully")
        else:
            click.echo("ℹ️ Security bootstrap skipped (already completed)")

    except (ValueError, RuntimeError, SQLAlchemyError):  # pragma: no cover - CLI top-level error
        logger.exception("Bootstrap failed")
        click.echo("💥 Bootstrap failed", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
