#!/usr/bin/env python3
"""Extract header logo SVG from WordPress static export."""
import re
import sys
from pathlib import Path


def extract_logo(html_path: Path) -> str:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(
        r'<a class="elementor-icon" href="[^"]*">\s*(<svg[^>]+>.*?</svg>)',
        html,
        re.DOTALL,
    )
    if not m:
        m = re.search(
            r'(<svg xmlns="http://www.w3.org/2000/svg" width="254" height="66".*?</svg>)',
            html,
            re.DOTALL,
        )
    if not m:
        raise SystemExit(f"Logo SVG not found in {html_path}")
    svg = m.group(1)
    return svg.replace('fill="000000"', 'fill="currentColor"')


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads/adrianaspmu.com/index.html"
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "assets/images/logo.svg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(extract_logo(src), encoding="utf-8")
    print(f"Wrote {dest}")


if __name__ == "__main__":
    main()
