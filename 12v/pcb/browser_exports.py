#!/usr/bin/env python3
"""Export PDFs as vector SVG pages and an offline HTML viewer.

Requires the ``pdfinfo`` and ``pdftocairo`` commands from Poppler, but no
third-party Python packages. Run without arguments to export repository PDFs,
or pass one or more PDF paths. Each HTML file lives beside its PDF and SVGs.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / '.utils'))
from browser_viewer import add_svg_bridge, render_viewer

EXCLUDED_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules',
                 '.pytest_cache', '.mypy_cache', 'tmp', 'temp', 'logs'}


def _run(*args: str) -> str:
    try:
        result = subprocess.run(args, check=True, text=True,
                                capture_output=True,
                                env={**os.environ, 'LC_ALL': 'C'})
    except FileNotFoundError as exc:
        raise RuntimeError(f'{args[0]} is required; install Poppler '
                           '(Ubuntu/Debian: sudo apt install poppler-utils).') from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f'{args[0]} failed: {exc.stderr.strip()}') from exc
    return result.stdout


def export_browser_views(pdf_path: str | Path, title: str | None = None) -> list[Path]:
    """Write HTML plus one SVG per PDF page; return HTML, then ordered SVG paths.

    A single-page ``drawing.pdf`` creates ``drawing.html`` and ``drawing.svg``.
    Multiple pages use ``drawing-page-1.svg``, ``drawing-page-2.svg``, etc.
    Render all pages successfully before replacing existing companion files.
    """
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.is_file() or pdf_path.suffix.lower() != '.pdf':
        raise ValueError(f'Expected an existing PDF file: {pdf_path}')
    page_match = re.search(r'^Pages:\s+(\d+)\s*$', _run('pdfinfo', str(pdf_path)), re.MULTILINE)
    if page_match is None or int(page_match[1]) < 1:
        raise RuntimeError(f'Cannot determine the page count of {pdf_path}')
    count = int(page_match[1])
    paths = [pdf_path.with_suffix('.html')]
    pages = []
    with tempfile.TemporaryDirectory(prefix='.browser-export-', dir=pdf_path.parent) as temp:
        temporary = Path(temp)
        for page in range(1, count + 1):
            suffix = '' if count == 1 else f'-page-{page}'
            svg_path = pdf_path.with_name(f'{pdf_path.stem}{suffix}.svg')
            converted = temporary / svg_path.name
            _run('pdftocairo', '-svg', '-f', str(page), '-l', str(page),
                 '-origpagesizes', str(pdf_path), str(converted))
            root = ET.parse(converted).getroot()
            viewbox = list(map(float, root.attrib['viewBox'].split()))
            if root.tag != '{http://www.w3.org/2000/svg}svg' or len(viewbox) != 4 or viewbox[2] <= 0:
                raise RuntimeError(f'Invalid SVG exported from {pdf_path}, page {page}')
            pages.append(root)
            add_svg_bridge(converted, output_path=svg_path)
            paths.append(svg_path)
        page_title = title if title is not None else pdf_path.stem.replace('-', ' ').replace('_', ' ')
        (temporary / paths[0].name).write_text(
            render_viewer(page_title, pages, svg_names=[path.name for path in paths[1:]],
                          html_path=paths[0]),
            encoding='utf-8')
        for destination in paths[1:] + paths[:1]:
            (temporary / destination.name).replace(destination)
    return paths


def discover_pdfs(root: str | Path) -> list[Path]:
    """Find repository PDFs, respecting Git ignores and excluding temporary dirs."""
    root = Path(root).resolve()
    if shutil.which('git'):
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '--cached',
                                 '--others', '--exclude-standard', '-z'],
                                capture_output=True, check=False)
        if result.returncode == 0:
            candidates = (root / os.fsdecode(name) for name in result.stdout.split(b'\0') if name)
        else:
            candidates = root.rglob('*')
    else:
        candidates = root.rglob('*')
    return sorted({path for path in candidates
                   if path.suffix.lower() == '.pdf' and path.is_file()
                   and not any(part in EXCLUDED_DIRS or part.startswith('.browser-export-')
                               for part in path.relative_to(root).parts[:-1])})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdfs', metavar='PDF', nargs='*', type=Path,
                        help='PDFs to convert; default: all repository PDFs')
    parser.add_argument('--root', type=Path, default=REPO_ROOT,
                        help='root directory for default PDF discovery')
    args = parser.parse_args()
    pdfs = args.pdfs or discover_pdfs(args.root)
    if not pdfs:
        parser.error(f'No PDF files found under {args.root}')
    try:
        for path in pdfs:
            for output in export_browser_views(path):
                print(output)
    except (ValueError, RuntimeError, OSError, ET.ParseError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
