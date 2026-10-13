"""Integration checks for PDF page preservation and portable browser links."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from browser_exports import discover_pdfs, export_browser_views


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


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.targets.append(attrs['href'])
        elif tag == 'img':
            self.images.append(attrs['src'])


@unittest.skipUnless(shutil.which('pdfinfo') and shutil.which('pdftocairo'), 'Poppler is required')
class BrowserExports(unittest.TestCase):
    def test_all_pages_keep_their_dimensions_and_have_local_links(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / 'two pages #1.pdf'
            sizes = [(200, 300), (400, 200)]
            write_pdf(pdf, sizes)
            outputs = export_browser_views(pdf)
            self.assertEqual([p.name for p in outputs], [
                'two pages #1.html', 'two pages #1-page-1.svg', 'two pages #1-page-2.svg'])
            for svg, size in zip(outputs[1:], sizes):
                bounds = list(map(float, ET.parse(svg).getroot().attrib['viewBox'].split()))
                self.assertEqual(bounds[2:], list(size))
            links = Links()
            links.feed(outputs[0].read_text())
            self.assertEqual(len(links.images), 2)
            for target in links.targets + links.images:
                parsed = urlsplit(target)
                self.assertFalse(parsed.scheme, 'Browser viewing must work offline')
                if parsed.path:
                    self.assertTrue((pdf.parent / unquote(parsed.path)).is_file(), target)

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
