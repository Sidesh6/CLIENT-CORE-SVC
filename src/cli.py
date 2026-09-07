"""
CLI Interface for Client Core Service.
"""

import sys
import click
import uvicorn
from src.config.settings import settings
from src.database.session import SessionLocal, check_db_connection, init_db
from src.repositories.client_repo import ClientProfileRepository
from src.repositories.lead_repo import LeadRepository


@click.group()
def cli() -> None:
    """Client Core Service CRM CLI."""
    pass


@cli.command("init-db")
def cmd_init_db() -> None:
    """Initialize SQLite / PostgreSQL tables."""
    click.secho("[+] Initializing Client Core database...", fg="cyan")
    init_db()
    if check_db_connection():
        click.secho("[OK] Database initialized successfully!", fg="green")
    else:
        click.secho("[ERROR] Failed to connect to database.", fg="red", err=True)
        sys.exit(1)


@cli.command("run-server")
@click.option("--host", default=None, help="Host to bind.")
@click.option("--port", default=None, type=int, help="Port to bind.")
@click.option("--reload", is_flag=True, default=False, help="Auto-reload.")
def cmd_run_server(host: str | None, port: int | None, reload: bool) -> None:
    """Start Client Core Service REST API."""
    bind_host = host or settings.app_host
    bind_port = port or settings.app_port
    click.secho(f"[*] Starting Client Core Service on http://{bind_host}:{bind_port}", fg="green")
    click.secho(f"[*] Swagger Docs: http://{bind_host}:{bind_port}/docs", fg="cyan")
    uvicorn.run("src.api.main:app", host=bind_host, port=bind_port, reload=reload)


@cli.command("list-leads")
@click.option("--status", default=None, help="Filter by status.")
@click.option("--min-score", default=None, type=float, help="Filter by score.")
@click.option("--limit", default=20, type=int, help="Max leads to show.")
def cmd_list_leads(status: str | None, min_score: float | None, limit: int) -> None:
    """List CRM leads."""
    with SessionLocal() as session:
        repo = LeadRepository(session)
        leads = repo.list_leads(status=status, min_score=min_score, page_size=limit)
        total = repo.count_leads(status=status, min_score=min_score)

    click.secho(f"\n--- Total Leads: {total} (showing {len(leads)}) ---\n", fg="cyan", bold=True)
    for lead in leads:
        score_str = f"Score: {lead.finder_score:.1f}" if lead.finder_score else "Score: N/A"
        click.secho(f"* [{lead.status.upper()}] {lead.title}", fg="white", bold=True)
        click.secho(f"  ID: {lead.id} | Source: {lead.source} | {score_str}", fg="bright_black")
        if lead.skills:
            click.secho(f"  Skills: {', '.join(lead.skills[:5])}", fg="yellow")
        click.echo()


@cli.command("list-clients")
@click.option("--limit", default=20, type=int, help="Max clients to show.")
def cmd_list_clients(limit: int) -> None:
    """List CRM client accounts."""
    with SessionLocal() as session:
        repo = ClientProfileRepository(session)
        clients = repo.list_clients(page_size=limit)
        total = repo.count_clients()

    click.secho(f"\n--- Total CRM Clients: {total} ---\n", fg="cyan", bold=True)
    for c in clients:
        click.secho(f"* {c.company or c.name or 'Unknown Client'}", fg="white", bold=True)
        click.secho(f"  Email: {c.email or 'N/A'} | Domain: {c.domain or 'N/A'} | Confidence: {c.confidence_score * 100:.0f}%", fg="bright_black")
        click.echo()


if __name__ == "__main__":
    cli()
