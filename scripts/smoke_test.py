"""Smoke test: verify Anthropic API + Qdrant are reachable before Day 1 PM work."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from rich.console import Console

console = Console()


def check_anthropic() -> bool:
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key.startswith("sk-ant-xxxx"):
        console.print("[red]ANTHROPIC_API_KEY not set (fill in .env)[/red]")
        return False
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        model = os.getenv("INTENT_MODEL", "claude-haiku-4-5-20251001")
        resp = client.messages.create(
            model=model,
            max_tokens=20,
            messages=[{"role": "user", "content": "Reply with only: pong"}],
        )
        text = resp.content[0].text.strip().lower()
        if "pong" in text:
            console.print(f"[green]Anthropic API OK[/green] (model={model}, reply={text!r})")
            return True
        console.print(f"[yellow]Anthropic API responded but unexpected: {text!r}[/yellow]")
        return True
    except Exception as e:  # noqa: BLE001 — want all errors surfaced in smoke test
        console.print(f"[red]Anthropic API FAILED: {e}[/red]")
        return False


def check_qdrant() -> bool:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=url, timeout=5)
        collections = client.get_collections()
        console.print(
            f"[green]Qdrant OK[/green] (url={url}, collections={len(collections.collections)})"
        )
        return True
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Qdrant FAILED at {url}: {e}[/red]")
        console.print("[dim]Hint: run `make up` to start Qdrant via docker-compose[/dim]")
        return False


def main() -> int:
    console.rule("Smoke test")
    ok_api = check_anthropic()
    ok_qdrant = check_qdrant()
    console.rule("Result")
    if ok_api and ok_qdrant:
        console.print("[green bold]ALL CHECKS PASSED[/green bold]")
        return 0
    console.print("[red bold]SOME CHECKS FAILED[/red bold]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
