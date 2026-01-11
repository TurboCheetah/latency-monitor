import re
from typing import Dict, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def parse_mtr(output: str, target_ip: str) -> Dict[str, Union[float, int]]:
    """
    Extracts the latency values, loss percentage,
    and sent packets count for a specific target IP from the MTR output.

    Parameters:
    - output (str): The MTR command output.
    - target_ip (str): The target IP to search for.

    Returns:
    - dict: A dictionary containing the latency values, loss percentage,
            and sent packets count for the target IP,
            or None if the IP isn't found.
    """

    regex = re.compile(
        rf"{re.escape(target_ip)}\s+"
        r"(?P<Loss>\S+)%\s+"
        r"(?P<Snt>\d+)\s+"
        r"(?P<Last>[\d.]+)\s+"
        r"(?P<Avg>[\d.]+)\s+"
        r"(?P<Best>[\d.]+)\s+"
        r"(?P<Worst>[\d.]+)\s+"
        r"(?P<StDev>[\d.]+)"
    )

    match = regex.search(output)

    if not match:
        raise ValueError(f"Target IP {target_ip} not found in MTR output.")

    return {
        "loss": float(match.group("Loss")),
        "snt": int(match.group("Snt")),
        "last": float(match.group("Last")),
        "avg": float(match.group("Avg")),
        "best": float(match.group("Best")),
        "worst": float(match.group("Worst")),
        "stdev": float(match.group("StDev")),
    }


def parse_dig(output: str) -> int:
    """Extract the query time from the dig command output."""

    regex = re.compile(r"Query time:\s(?P<time>\d+)")

    match = regex.search(output)

    if not match:
        raise ValueError("Query time not found in dig output")

    return int(match.group("time"))


def print_mtr_result(target: str, parsed: dict) -> None:
    """Print a styled MTR result table."""
    table = Table(
        title=f"[bold cyan]MTR[/] → [bold magenta]{target}[/]",
        show_header=True,
        header_style="bold white on dark_blue",
        border_style="bright_blue",
        title_justify="left",
    )

    table.add_column("Metric", style="cyan", width=10)
    table.add_column("Value", style="green", justify="right")

    loss = parsed.get("loss", 0)
    loss_style = "green" if loss == 0 else "yellow" if loss < 5 else "red bold"

    table.add_row("Loss", Text(f"{loss}%", style=loss_style))
    table.add_row("Sent", str(parsed.get("snt", "-")))
    table.add_row("Last", f"{parsed.get('last', '-')} ms")
    table.add_row("Avg", f"[bold]{parsed.get('avg', '-')}[/] ms")
    table.add_row("Best", f"[green]{parsed.get('best', '-')}[/] ms")
    table.add_row("Worst", f"[red]{parsed.get('worst', '-')}[/] ms")
    table.add_row("StDev", f"{parsed.get('stdev', '-')} ms")

    console.print(table)


def print_dig_result(target: str, query_time: int) -> None:
    """Print a styled dig result panel."""
    if query_time < 50:
        time_style = "bold green"
        emoji = "⚡"
    elif query_time < 100:
        time_style = "bold yellow"
        emoji = "✓"
    else:
        time_style = "bold red"
        emoji = "⚠"

    panel = Panel(
        Text.assemble((f"{query_time}", time_style), (" ms", "dim")),
        title=f"[bold cyan]DIG[/] → [bold magenta]{target}[/]",
        subtitle=f"{emoji} DNS Query",
        border_style="bright_blue",
        width=40,
    )
    console.print(panel)


def print_task_start(task_name: str, target: str) -> None:
    """Print a styled task start message."""
    console.print(
        f"[dim]{'─' * 40}[/]\n"
        f"[bold blue]▶[/] Running [cyan]{task_name}[/] for [magenta]{target}[/]"
    )


def print_task_complete(task_name: str, count: int) -> None:
    """Print a styled task completion message."""
    console.print(
        f"\n[bold green]✔[/] Completed [cyan]{task_name}[/] for "
        f"[bold]{count}[/] target{'s' if count != 1 else ''}\n"
    )
