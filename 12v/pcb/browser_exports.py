#!/usr/bin/env python3
"""Export PDFs as vector SVG pages and an offline HTML viewer.

Requires the ``pdfinfo`` and ``pdftocairo`` commands from Poppler, but no
third-party Python packages. Run without arguments to export repository PDFs,
or pass one or more PDF paths. Each HTML file lives beside its PDF and SVGs.
"""
from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[2]
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


def _viewer(title: str, pdf_name: str, pages: list[tuple[str, float]]) -> str:
    title_text = html.escape(title)
    sections = []
    for number, (name, width) in enumerate(pages, 1):
        url = quote(name, safe='')
        label = f'{title}, page {number} of {len(pages)}'
        sections.append(f'''<figure class="page" id="page-{number}" data-width="{width:g}"
  style="width: {width:g}px">
  <img src="{url}" alt="{html.escape(label, quote=True)}" decoding="async">
  <figcaption>Page {number} of {len(pages)} · <a href="{url}">Open SVG</a></figcaption>
</figure>''')
    page_links = ''
    if len(pages) > 1:
        page_links = '<nav aria-label="Pages">Pages: ' + ' · '.join(
            f'<a href="#page-{n}">{n}</a>' for n in range(1, len(pages) + 1)) + '</nav>'
    return '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light; font-family: system-ui, sans-serif; color: #172334; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #f4f6f8; }
  header { padding: 1rem 1.5rem; background: #fff; border-bottom: 1px solid #cbd5e1; }
  h1 { font-size: 1.3rem; margin: 0 0 .65rem; }
  p { margin: .5rem 0; }
  a { color: #1255a1; text-underline-offset: .15em; }
  a:focus-visible, button:focus-visible { outline: 3px solid #c26500; outline-offset: 3px; }
  nav { margin: .6rem 0 0; }
  .toolbar { display: flex; gap: .6rem; align-items: center; flex-wrap: wrap; margin-top: .8rem; }
  [hidden] { display: none !important; }
  button { font: inherit; border: 1px solid #94a3b8; border-radius: .25rem;
           background: #fff; color: #172334; padding: .35rem .75rem; cursor: pointer; }
  button:disabled { opacity: .45; cursor: default; }
  output { min-width: 4rem; text-align: center; font-variant-numeric: tabular-nums; }
  main { margin: 1rem; }
  .viewer { overflow: auto; max-width: 100%; background: #dfe5ec;
            border: 1px solid #bdc8d5; border-radius: .25rem; }
  .pages { min-width: 100%; width: max-content; padding: 24px; }
  .page { margin: 0 auto 24px; scroll-margin-top: 1rem; }
  .page:last-child { margin-bottom: 0; }
  .page img { display: block; width: 100%; height: auto; background: white;
              box-shadow: 0 2px 6px #0003; }
  figcaption { font-size: .9rem; padding: .7rem 0; }
  @media print {
    header, figcaption { display: none; }
    body, main, .viewer, .pages { margin: 0; padding: 0; background: white; border: 0;
                                 width: auto; overflow: visible; }
    .page { width: 100% !important; margin: 0; break-after: page; }
    .page:last-child { break-after: auto; }
    .page img { box-shadow: none; }
  }
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <p><a href="__PDF_URL__">Open PDF</a> · <a href="__PDF_URL__" download>Download PDF</a></p>
  <p>Vector drawings stay sharp when zoomed. This viewer works offline.</p>
  __PAGE_LINKS__
  <div class="toolbar" id="controls" aria-label="Drawing zoom" hidden>
    <button type="button" id="zoom-out" aria-label="Zoom out">−</button>
    <output id="zoom-value" aria-live="polite" aria-label="Zoom level"></output>
    <button type="button" id="zoom-in" aria-label="Zoom in">+</button>
    <button type="button" id="fit">Fit width</button>
    <button type="button" id="actual">100%</button>
  </div>
</header>
<main>
  <div class="viewer" id="viewer" tabindex="0" role="region" aria-label="Drawing pages">
    <div class="pages">
__SECTIONS__
    </div>
  </div>
</main>
<script>
(() => {
  const viewer = document.getElementById('viewer');
  const pages = Array.from(document.querySelectorAll('.page'));
  const minus = document.getElementById('zoom-out');
  const plus = document.getElementById('zoom-in');
  const value = document.getElementById('zoom-value');
  const widest = Math.max(...pages.map(page => Number(page.dataset.width)));
  let scale = 1;
  let fitMode = true;
  function zoom(next, fitting = false) {
    fitMode = fitting;
    scale = Math.min(8, Math.max(0.1, next));
    pages.forEach(page => { page.style.width = `${Number(page.dataset.width) * scale}px`; });
    value.textContent = `${Math.round(scale * 100)}%`;
    minus.disabled = scale <= 0.1;
    plus.disabled = scale >= 8;
  }
  function fit() { zoom((viewer.clientWidth - 48) / widest, true); }
  minus.addEventListener('click', () => zoom(scale / 1.25));
  plus.addEventListener('click', () => zoom(scale * 1.25));
  document.getElementById('fit').addEventListener('click', fit);
  document.getElementById('actual').addEventListener('click', () => zoom(1));
  window.addEventListener('resize', () => { if (fitMode) fit(); });
  document.getElementById('controls').hidden = false;
  fit();
})();
</script>
</body>
</html>
'''.replace('__TITLE__', title_text).replace('__PDF_URL__', quote(pdf_name, safe='')).replace(
        '__PAGE_LINKS__', page_links).replace('__SECTIONS__', '\n'.join(sections))


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
            pages.append((svg_path.name, viewbox[2]))
            paths.append(svg_path)
        page_title = title if title is not None else pdf_path.stem.replace('-', ' ').replace('_', ' ')
        (temporary / paths[0].name).write_text(_viewer(page_title, pdf_path.name, pages), encoding='utf-8')
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
