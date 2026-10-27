"""Standalone TTS test: synthesize text to an MP3 file.

Usage:
    uv run python -m scripts.speak "สวัสดีครับ ยินดีที่ได้พบคุณ" -o hello.mp3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from app.voice.tts import detect_lang, synthesize

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("-o", "--out", type=Path, default=Path("tts_out.mp3"))
    parser.add_argument("--lang", default=None, help="th / en (default: auto)")
    parser.add_argument("--rate", default="+0%", help='e.g. "+10%", "-15%"')
    args = parser.parse_args()

    lang = args.lang or detect_lang(args.text)
    console.print(f"[dim]Lang:[/dim] {lang}  [dim]Rate:[/dim] {args.rate}")

    with console.status("Calling Edge-TTS..."):
        audio = synthesize(args.text, lang=lang, rate=args.rate)

    args.out.write_bytes(audio)
    console.print(f"[green]Wrote {len(audio)} bytes to {args.out}[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
