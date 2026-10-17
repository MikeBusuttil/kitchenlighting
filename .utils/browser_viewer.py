"""Generate local-file HTML viewers that load their companion SVG drawings."""
from __future__ import annotations

import html
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET


ET.register_namespace('', 'http://www.w3.org/2000/svg')
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


def relative_asset_url(name: str, output_path: str | Path) -> str:
    """Link shared assets relative to the final output, independent of cwd."""
    asset = Path(__file__).resolve().with_name(name)
    relative = Path(os.path.relpath(asset, Path(output_path).resolve().parent))
    return quote(relative.as_posix(), safe='/')


def add_svg_bridge(svg_path: str | Path, *, output_path: str | Path | None = None) -> None:
    """Import the viewer bridge once, preserving the existing vector markup.

    For temporary exports, resolve the import against the eventual destination.
    """
    svg_path = Path(svg_path)
    source = svg_path.read_text(encoding='utf-8')
    source = re.sub(r'<script id="viewer-svg-bridge"(?: [^>]*)?>.*?</script>\n?', '',
                    source, flags=re.DOTALL)
    href = relative_asset_url('browser_viewer.js', output_path or svg_path)
    bridge = f'<script id="viewer-svg-bridge" href="{href}"></script>\n'
    source, count = re.subn(r'(</(?:[\w.-]+:)?svg>\s*)\Z',
                            lambda match: bridge + match[1], source)
    if count != 1:
        raise ValueError(f'Expected an SVG closing tag: {svg_path}')
    svg_path.write_text(source, encoding='utf-8')


def export_svg_view(svg_path: str | Path, title: str | None = None,
                    *, navigation: bool = False) -> Path:
    """Write a companion HTML viewer and add its message bridge to the SVG."""
    svg_path = Path(svg_path).resolve()
    if not svg_path.is_file() or svg_path.suffix.lower() != '.svg':
        raise ValueError(f'Expected an existing SVG file: {svg_path}')
    root = ET.parse(svg_path).getroot()
    bounds = list(map(float, root.get('viewBox', '').replace(',', ' ').split()))
    if (root.tag != '{http://www.w3.org/2000/svg}svg' or len(bounds) != 4
            or not all(math.isfinite(value) for value in bounds)
            or bounds[2] <= 0 or bounds[3] <= 0):
        raise ValueError(f'Expected an SVG with a valid viewBox: {svg_path}')
    if title is None:
        title = (root.findtext('{http://www.w3.org/2000/svg}title')
                 or svg_path.stem.replace('-', ' ').replace('_', ' '))
    html_path = svg_path.with_suffix('.html')
    viewer = render_viewer(title, [root], svg_names=[svg_path.name],
                           html_path=html_path, navigation=navigation)
    add_svg_bridge(svg_path)
    html_path.write_text(viewer, encoding='utf-8')
    return html_path


def render_viewer(title: str, pages: list[ET.Element], *, svg_names: list[str],
                  html_path: str | Path, navigation: bool = False) -> str:
    """Reference SVG files; JavaScript inserts them inline for Dark Reader."""
    if not pages or len(pages) != len(svg_names):
        raise ValueError('Each drawing page needs an SVG filename')
    sources = [quote(name, safe='') for name in svg_names]
    fallback = '\n'.join(
        f'<img src="{html.escape(source, quote=True)}" '
        f'alt="{html.escape(title, quote=True)}, page {number} of {len(pages)}">'
        for number, source in enumerate(sources, 1))
    nav_html = ''
    if navigation:
        links = '\n'.join(
            f'<a href="../{voltage}/{layout}.html" aria-label="{voltage[:-1]} V {label}" '
            f'title="{voltage[:-1]} V {label}">{voltage} {emoji}</a>'
            for layout, label, emoji in [('min', 'minimum', '🤏'), ('best', 'best practice', '💪')]
            for voltage in ('5v', '12v'))
        nav_html = f'<nav class="drawing-nav" aria-label="Breadboard drawings">\n{links}\n</nav>\n'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<script src="{relative_asset_url('browser_viewer_styles.js', html_path)}"></script>
<script src="{relative_asset_url('browser_viewer.js', html_path)}" defer></script>
</head>
<body>
{nav_html}<main id="drawings" data-sources="{html.escape(json.dumps(sources), quote=True)}">
<noscript>{fallback}</noscript>
</main>
<p id="viewer-error" role="alert" hidden>Could not load the drawing. <a href="{sources[0]}">Open SVG</a></p>
</body>
</html>
'''
