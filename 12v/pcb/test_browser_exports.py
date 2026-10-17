"""Integration checks for PDF page preservation and minimal HTML companions."""
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import unquote
import xml.etree.ElementTree as ET

from browser_exports import discover_pdfs, export_browser_views
from browser_viewer import export_svg_view, render_viewer

ROOT = Path(__file__).resolve().parents[2]


def write_pdf(path, sizes):
    """Tiny valid multi-page PDF fixture; no PDF library dependency."""
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'']
    kids = []
    for width, height in sizes:
        page_id = len(objects) + 1
        kids.append(f'{page_id} 0 R')
        objects.append((f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] '
                        f'/Contents {page_id + 1} 0 R /Resources << >> >>').encode())
        stream = b'0.2 0.4 0.8 rg 10 10 60 40 re f\n'
        objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'endstream')
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode()
    result = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, data in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f'{number} 0 obj\n'.encode() + data + b'\nendobj\n')
    xref = len(result)
    result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        result.extend(f'{offset:010d} 00000 n \n'.encode())
    result.extend((f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n'
                   f'startxref\n{xref}\n%%EOF\n').encode())
    path.write_bytes(result)


class DrawingHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.svgs = []
        self.elements = []
        self.body_elements = []
        self.in_body = False
        self.svg_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if self.in_body and self.svg_depth == 0:
            self.body_elements.append(tag)
        if tag == 'body':
            self.in_body = True
        elif tag == 'svg':
            self.svg_depth += 1
            self.svgs.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'svg':
            self.svg_depth -= 1
        elif tag == 'body':
            self.in_body = False


class LinkedSvgViewer(unittest.TestCase):
    def test_html_references_pages_without_copying_the_vector_markup(self):
        root = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg"
          xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 300">
          <defs>
            <clipPath id="clip-0"><rect width="200" height="300"/></clipPath>
            <path id="shape-0" d="M 0 0 L 100 100"/>
          </defs>
          <g clip-path="url(#clip-0)">
            <use xlink:href="#shape-0"/>
            <use href="#shape-0"/>
          </g>
        </svg>''')
        original = ET.tostring(root)
        document = DrawingHTML()
        document.feed(render_viewer('Two pages', [root, root],
                                    svg_names=['one #1.svg', 'two.svg'],
                                    html_path=ROOT / '12v' / 'pcb' / 'two.html'))
        self.assertEqual(document.svgs, [])
        source = next(attrs['data-sources'] for tag, attrs in document.elements
                      if tag == 'main')
        self.assertEqual(json.loads(source), ['one%20%231.svg', 'two.svg'])
        self.assertFalse(any(tag in ('path', 'clippath', 'use') for tag, _ in document.elements))
        self.assertEqual(ET.tostring(root), original)
        self.assertNotIn('style', [tag for tag, _ in document.elements])
        scripts = [attrs for tag, attrs in document.elements if tag == 'script']
        self.assertEqual(scripts, [{'src': '../../.utils/browser_viewer_styles.js'},
                                   {'src': '../../.utils/browser_viewer.js', 'defer': None}])

    def test_bridge_is_idempotent_and_leaves_drawing_content_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            svg = Path(directory) / 'one.svg'
            original = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 30"><rect width="20" height="30"/></svg>'
            svg.write_text(original.replace('</svg>',
                '<script id="viewer-svg-bridge">/* old inline bridge */</script></svg>'))
            export_svg_view(svg)
            first = svg.read_bytes()
            export_svg_view(svg)
            self.assertEqual(svg.read_bytes(), first)
            root = ET.parse(svg).getroot()
            scripts = root.findall('{http://www.w3.org/2000/svg}script')
            self.assertEqual(len(scripts), 1)
            self.assertEqual(scripts[0].get('id'), 'viewer-svg-bridge')
            self.assertIsNone(scripts[0].text)
            self.assertEqual((svg.parent / unquote(scripts[0].get('href'))).resolve(),
                             ROOT / '.utils' / 'browser_viewer.js')
            root.remove(scripts[0])
            self.assertEqual(ET.tostring(root), ET.tostring(ET.fromstring(original)))


@unittest.skipUnless(shutil.which('pdfinfo') and shutil.which('pdftocairo'), 'Poppler is required')
class BrowserExports(unittest.TestCase):
    def test_all_pages_keep_their_dimensions_in_linked_svg_html(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / 'two pages #1.pdf'
            sizes = [(200, 300), (400, 200)]
            write_pdf(pdf, sizes)
            outputs = export_browser_views(pdf)
            self.assertEqual([p.name for p in outputs], [
                'two pages #1.html', 'two pages #1-page-1.svg', 'two pages #1-page-2.svg'])
            for svg, size in zip(outputs[1:], sizes):
                root = ET.parse(svg).getroot()
                bounds = list(map(float, root.attrib['viewBox'].split()))
                self.assertEqual(bounds[2:], list(size))
                self.assertEqual(len(root.findall('{http://www.w3.org/2000/svg}script')), 1)
                bridge = root.find('{http://www.w3.org/2000/svg}script')
                self.assertEqual((svg.parent / unquote(bridge.get('href'))).resolve(),
                                 ROOT / '.utils' / 'browser_viewer.js')
            document = DrawingHTML()
            document.feed(outputs[0].read_text())
            self.assertEqual(document.svgs, [])
            source = next(attrs['data-sources'] for tag, attrs in document.elements
                          if tag == 'main')
            self.assertEqual(json.loads(source), ['two%20pages%20%231-page-1.svg',
                                                 'two%20pages%20%231-page-2.svg'])

    def test_single_page_and_title_are_safe_in_html(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / 'drawing.pdf'
            write_pdf(pdf, [(200, 300)])
            outputs = export_browser_views(pdf, title='Drawing <A> & "B"')
            self.assertEqual([p.name for p in outputs], ['drawing.html', 'drawing.svg'])
            self.assertIn('<title>Drawing &lt;A&gt; &amp; &quot;B&quot;</title>', outputs[0].read_text())
            self.assertNotIn('<A>', outputs[0].read_text())


@unittest.skipUnless(shutil.which('git'), 'Git is required')
class PdfDiscovery(unittest.TestCase):
    def test_default_discovery_skips_ignored_and_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / '.gitignore').write_text('ignored/\n')
            for name in ['drawing.pdf', 'nested/second.PDF', 'ignored/hidden.pdf',
                         '.venv/dependency.pdf', 'tmp/transient.pdf']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual([p.relative_to(root).as_posix() for p in discover_pdfs(root)],
                             ['drawing.pdf', 'nested/second.PDF'])


if __name__ == '__main__':
    unittest.main()
