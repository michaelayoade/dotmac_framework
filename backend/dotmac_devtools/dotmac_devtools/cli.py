"""
DotMac Developer Tools CLI - Comprehensive command-line interface for service generation,
SDK creation, developer portal management, and zero-trust security.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from .core.config import DevToolsConfig, load_config, save_config, validate_environment
from .core.exceptions import DevToolsError
from .sdks.developer_portal import DeveloperPortalSDK
from .sdks.sdk_generator import SDKGeneratorSDK
from .sdks.service_generator import ServiceGeneratorSDK
from .sdks.zero_trust import ZeroTrustSecuritySDK

app = typer.Typer(
    name="dotmac",
    help="DotMac Developer Tools - Service scaffolding, SDK generation, and zero-trust security",
    rich_markup_mode="rich"
)

# Create sub-commands
generate_app = typer.Typer(name="generate", help="Generate services and SDKs")
portal_app = typer.Typer(name="portal", help="Developer portal management")
security_app = typer.Typer(name="security", help="Zero-trust security management")
scaffold_app = typer.Typer(name="scaffold", help="Scaffold complete projects")

app.add_typer(generate_app)
app.add_typer(portal_app)
app.add_typer(security_app)
app.add_typer(scaffold_app)

console = Console()


def load_global_config() -> DevToolsConfig:
    """Load global configuration."""
    try:
        return load_config()
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        return DevToolsConfig()


async def run_async(coro):
    """Run async function in sync context."""
    return await coro


@app.command("init")
def init_workspace(
    name: str = typer.Option("dotmac-workspace", help="Workspace name"),
    path: str | None = typer.Option(None, help="Workspace path"),
):
    """Initialize a new DotMac workspace."""

    workspace_path = Path(path) if path else Path.cwd() / name
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Create workspace structure
    directories = [
        "services",
        "sdks",
        "docs",
        "configs",
        "scripts",
        "deployments"
    ]

    for directory in directories:
        (workspace_path / directory).mkdir(exist_ok=True)

    # Create workspace configuration
    config = DevToolsConfig(workspace_path=workspace_path)
    config_file = workspace_path / "dotmac.yaml"
    save_config(config, config_file)

    # Create README
    readme_content = f"""# {name}

DotMac ISP Framework Workspace

## Structure

- `services/` - Generated services
- `sdks/` - Generated SDKs for external partners
- `docs/` - API documentation
- `configs/` - Configuration files
- `scripts/` - Utility scripts
- `deployments/` - Deployment manifests

## Getting Started

```bash
# Generate a new service
dotmac generate service --name customer-api --type rest-api

# Generate SDK for partners
dotmac generate sdk --language python --service customer-api

# Setup developer portal
dotmac portal init --domain developer.myisp.com

# Initialize zero-trust security
dotmac security init-zero-trust --cluster production
```
"""

    (workspace_path / "README.md").write_text(readme_content)

    console.print(Panel(
        f"[green]Workspace initialized successfully![/green]\n\n"
        f"Location: {workspace_path}\n"
        f"Configuration: {config_file}\n\n"
        f"Next steps:\n"
        f"1. cd {workspace_path}\n"
        f"2. dotmac generate service --name my-first-service\n"
        f"3. dotmac portal init --domain developer.example.com",
        title="🚀 DotMac Workspace Created"
    ))


@generate_app.command("service")
def generate_service(  # noqa: PLR0913
    name: str = typer.Option(..., help="Service name"),
    service_type: str = typer.Option("rest-api", help="Service type"),
    template: str | None = typer.Option(None, help="Service template name"),
    output_dir: str | None = typer.Option(None, help="Output directory"),
    database: str = typer.Option("postgresql", help="Database type"),
    cache: str = typer.Option("redis", help="Cache type"),
    queue: str = typer.Option("rabbitmq", help="Message queue type"),
    enable_auth: bool = typer.Option(True, help="Enable authentication"),
    enable_monitoring: bool = typer.Option(True, help="Enable monitoring"),
):
    """Generate a new DotMac service."""

    config = load_global_config()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        task = progress.add_task("Generating service...", total=None)

        try:
            service_generator = ServiceGeneratorSDK(config)

            result = asyncio.run(service_generator.generate_service(
                name=name,
                service_type=service_type,
                template=template,
                output_dir=output_dir,
                database=database,
                cache=cache,
                queue=queue,
                enable_auth=enable_auth,
                enable_monitoring=enable_monitoring,
            ))

            progress.stop()

            # Display results
            table = Table(title=f"Generated Service: {name}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Service Name", result['service_name'])
            table.add_row("Service Type", result['service_type'])
            table.add_row("Service Path", result['service_path'])
            table.add_row("Generated Files", str(len(result['generated_files'])))

            console.print(table)

            # Show next steps
            console.print("\n[bold cyan]Next Steps:[/bold cyan]")
            for i, step in enumerate(result['next_steps'], 1):
                console.print(f"{i}. {step}")

        except DevToolsError as e:
            progress.stop()
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@generate_app.command("sdk")
def generate_sdk(  # noqa: PLR0913
    language: str = typer.Option(..., help="Programming language"),
    api_spec_file: str | None = typer.Option(None, help="OpenAPI spec file"),
    api_spec_url: str | None = typer.Option(None, help="OpenAPI spec URL"),
    service_name: str | None = typer.Option(None, help="Service name for auto-discovery"),
    output_dir: str | None = typer.Option(None, help="Output directory"),
    package_name: str | None = typer.Option(None, help="Package name"),
    async_support: bool = typer.Option(True, help="Include async support"),
    include_examples: bool = typer.Option(True, help="Include examples"),
    include_tests: bool = typer.Option(True, help="Include tests"),
):
    """Generate SDK for external partners."""

    config = load_global_config()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        task = progress.add_task("Generating SDK...", total=None)

        try:
            sdk_generator = SDKGeneratorSDK(config)

            result = asyncio.run(sdk_generator.generate_sdk(
                language=language,
                api_spec_file=api_spec_file,
                api_spec_url=api_spec_url,
                service_name=service_name,
                output_dir=output_dir,
                package_name=package_name,
                async_support=async_support,
                include_examples=include_examples,
                include_tests=include_tests,
            ))

            progress.stop()

            # Display results
            table = Table(title=f"Generated {language.title()} SDK")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Language", result['language'])
            table.add_row("Package Name", result['package_name'])
            table.add_row("Output Directory", result['output_dir'])
            table.add_row("Generated Files", str(len(result['generated_files'])))

            console.print(table)

            # Show next steps
            console.print("\n[bold cyan]Next Steps:[/bold cyan]")
            for i, step in enumerate(result['next_steps'], 1):
                console.print(f"{i}. {step}")

        except DevToolsError as e:
            progress.stop()
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@portal_app.command("init")
def init_portal(
    domain: str = typer.Option(..., help="Portal domain"),
    title: str = typer.Option("Developer Portal", help="Portal title"),
    company_name: str = typer.Option("DotMac ISP", help="Company name"),
    support_email: str = typer.Option("api-support@dotmac.com", help="Support email"),
    auth_provider: str = typer.Option("auth0", help="Authentication provider"),
    approval_workflow: str = typer.Option("automatic", help="Approval workflow"),
):
    """Initialize developer portal."""

    config = load_global_config()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        task = progress.add_task("Initializing portal...", total=None)

        try:
            portal_sdk = DeveloperPortalSDK(config)

            result = asyncio.run(portal_sdk.initialize_portal(
                domain=domain,
                title=title,
                company_name=company_name,
                support_email=support_email,
                auth_provider=auth_provider,
                approval_workflow=approval_workflow,
            ))

            progress.stop()

            # Display results
            console.print(Panel(
                f"[green]Developer Portal initialized successfully![/green]\n\n"
                f"Domain: {result['domain']}\n"
                f"Title: {result['title']}\n"
                f"Auth Provider: {result['auth_provider']}\n"
                f"Approval Workflow: {result['approval_workflow']}\n\n"
                f"Portal ID: {result['portal_id']}",
                title="🌐 Developer Portal Ready"
            ))

        except DevToolsError as e:
            progress.stop()
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@portal_app.command("register")
def register_developer(
    email: str = typer.Option(..., help="Developer email"),
    name: str = typer.Option("", help="Developer name"),
    company: str = typer.Option("", help="Company name"),
    tier: str = typer.Option("starter", help="Developer tier"),
):
    """Register a new developer."""

    config = load_global_config()

    try:
        portal_sdk = DeveloperPortalSDK(config)

        result = asyncio.run(portal_sdk.register_developer(
            email=email,
            name=name,
            company=company,
            tier=tier,
        ))

        console.print(Panel(
            f"[green]Developer registered successfully![/green]\n\n"
            f"Email: {result['email']}\n"
            f"Name: {result['name']}\n"
            f"Status: {result['status']}\n"
            f"Tier: {result['tier']}\n\n"
            f"Developer ID: {result['developer_id']}",
            title="👨‍💻 Developer Registered"
        ))

    except DevToolsError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@security_app.command("init-zero-trust")
def init_zero_trust(
    cluster_name: str = typer.Option("default-cluster", help="Cluster name"),
    trust_domain: str = typer.Option("dotmac.local", help="Trust domain"),
    provider: str = typer.Option("istio", help="Service mesh provider"),
    enable_mtls: bool = typer.Option(True, help="Enable mutual TLS"),
):
    """Initialize zero-trust security model."""

    config = load_global_config()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        task = progress.add_task("Initializing zero-trust...", total=None)

        try:
            security_sdk = ZeroTrustSecuritySDK(config)

            result = asyncio.run(security_sdk.initialize_zero_trust(
                cluster_name=cluster_name,
                trust_domain=trust_domain,
                provider=provider,
                enable_mtls=enable_mtls,
            ))

            progress.stop()

            console.print(Panel(
                f"[green]Zero-trust security initialized![/green]\n\n"
                f"Cluster: {result['cluster_name']}\n"
                f"Trust Domain: {result['trust_domain']}\n"
                f"Provider: {result['provider']}\n"
                f"mTLS Enabled: {result['enable_mtls']}\n\n"
                f"Root CA created and service mesh configured.",
                title="🔒 Zero-Trust Security Active"
            ))

        except DevToolsError as e:
            progress.stop()
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@security_app.command("create-identity")
def create_service_identity(
    service_name: str = typer.Option(..., help="Service name"),
    namespace: str = typer.Option("default", help="Kubernetes namespace"),
    cluster_name: str = typer.Option("default-cluster", help="Cluster name"),
):
    """Create service identity with certificate."""

    config = load_global_config()

    try:
        security_sdk = ZeroTrustSecuritySDK(config)

        result = asyncio.run(security_sdk.create_service_identity(
            service_name=service_name,
            namespace=namespace,
            cluster_name=cluster_name,
        ))

        console.print(Panel(
            f"[green]Service identity created![/green]\n\n"
            f"Service: {result['service_name']}\n"
            f"Namespace: {result['namespace']}\n"
            f"SPIFFE ID: {result['spiffe_id']}\n"
            f"Expires: {result['expires_at']}\n\n"
            f"Certificate and private key generated.",
            title="🆔 Service Identity Created"
        ))

    except DevToolsError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@security_app.command("audit")
def audit_security(
    cluster_name: str = typer.Option("default-cluster", help="Cluster name"),
    detailed: bool = typer.Option(False, help="Show detailed report"),
):
    """Audit security policies and certificates."""

    config = load_global_config()

    try:
        security_sdk = ZeroTrustSecuritySDK(config)

        result = asyncio.run(security_sdk.audit_security_policies(cluster_name))

        # Display audit results
        table = Table(title=f"Security Audit: {cluster_name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Policies", str(result['total_policies']))
        table.add_row("Active Policies", str(result['active_policies']))
        table.add_row("Security Gaps", str(len(result['security_gaps'])))
        table.add_row("Warnings", str(len(result['warnings'])))
        table.add_row("Expiring Certificates", str(len(result['expiring_certificates'])))

        console.print(table)

        # Show warnings
        if result['warnings']:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in result['warnings']:
                console.print(f"⚠️  {warning}")

        # Show expiring certificates
        if result['expiring_certificates']:
            console.print("\n[bold red]Expiring Certificates:[/bold red]")
            for cert in result['expiring_certificates']:
                console.print(f"🔴 {cert['service']}.{cert.get('namespace', 'default')} expires in {cert['expires_in_days']} days")

    except DevToolsError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def show_status():
    """Show DotMac development environment status."""

    # Validate environment
    validation = validate_environment()

    # Create status table
    table = Table(title="DotMac Development Environment")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")

    # Environment validation
    if validation['valid']:
        table.add_row("Environment", "✅ Valid", "All requirements met")
    else:
        table.add_row("Environment", "❌ Invalid", f"{len(validation['errors'])} errors")

    # Tool versions
    for tool, version in validation['info'].items():
        table.add_row(tool.replace('_', ' ').title(), "✅ Available", version)

    console.print(table)

    # Show errors and warnings
    if validation['errors']:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in validation['errors']:
            console.print(f"❌ {error}")

    if validation['warnings']:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in validation['warnings']:
            console.print(f"⚠️  {warning}")


@app.command("config")
def show_config(
    edit: bool = typer.Option(False, help="Edit configuration"),
):
    """Show or edit configuration."""

    config = load_global_config()

    if edit:
        # TODO: Implement config editing
        console.print("[yellow]Config editing not implemented yet[/yellow]")
    else:
        # Display current configuration
        config_dict = config.dict(exclude_none=True)
        config_yaml = yaml.dump(config_dict, default_flow_style=False)

        syntax = Syntax(config_yaml, "yaml", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Current Configuration"))


def main():
    """Main CLI entry point."""
    app()


# Command shortcuts for common operations
@app.command("new")
def new_service_shortcut(
    name: str = typer.Argument(..., help="Service name"),
    service_type: str = typer.Option("rest-api", "--type", help="Service type"),
):
    """Shortcut to generate a new service."""
    return generate_service(name=name, service_type=service_type)


# Alias commands
generate_command = generate_app
scaffold_command = scaffold_app


if __name__ == "__main__":
    main()
