"""Standalone STT test: transcribe an audio file.

Usage:
    uv run python -m scripts.transcribe path/to/audio.wav [--lang th]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from app.voice.stt import transcribe

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--lang", default=None, help="Language hint (th/en)")
    args = parser.parse_args()

    if not args.path.exists():
        console.print(f"[red]File not found: {args.path}[/red]")
        return 1

    console.rule("Transcribing")
    console.print(f"[dim]File:[/dim] {args.path}  [dim]Lang hint:[/dim] {args.lang or 'auto'}")

    with console.status("Loading model + decoding..."):
        result = transcribe(args.path, language=args.lang)

    console.print(f"[dim]Detected:[/dim] {result.detected_language} "
                  f"({result.language_probability:.2f} prob)  "
                  f"[dim]Duration:[/dim] {result.duration_seconds:.1f}s")
    console.rule("Transcript")
    console.print(result.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
