"""Dashboard CLI command group."""

from __future__ import annotations

import typer

from pm_agent.cli.commands.common import console
from pm_agent.dashboard.server import serve

dashboard_app = typer.Typer(help="本地 dashboard API / UI", no_args_is_help=True)


@dashboard_app.command("serve")
def dashboard_serve(
    host: str = typer.Option("127.0.0.1", "--host", help="监听地址"),
    port: int = typer.Option(5001, "--port", help="监听端口"),
    debug: bool = typer.Option(False, "--debug", help="是否开启 Flask debug"),
):
    """启动本地 PM dashboard。"""
    console.print(f"[cyan]Starting dashboard on http://{host}:{port}[/cyan]")
    serve(host=host, port=port, debug=debug)
