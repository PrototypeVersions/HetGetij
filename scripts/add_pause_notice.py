#!/usr/bin/env python3
"""Add the temporary site-development pause notice to the built home page."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'dist' / 'index.html'
html = path.read_text(encoding='utf-8')
notice = '''<aside role="status" aria-label="Updates gepauzeerd" style="box-sizing:border-box;max-width:1180px;margin:1.2rem auto 0;padding:.9rem 1.1rem;border:1px solid #bd8b58;border-radius:6px;background:rgba(189,139,88,.12);color:#f2eadf;font-family:system-ui,sans-serif;font-size:.95rem;font-weight:650;letter-spacing:.01em;text-align:center;">Updates zijn tijdelijk gepauzeerd vanwege werkzaamheden aan de site.</aside>'''
if 'Updates zijn tijdelijk gepauzeerd vanwege werkzaamheden aan de site.' not in html:
    marker = '<main '
    if marker not in html:
        raise SystemExit('Could not find the home-page <main> element')
    html = html.replace(marker, notice + '\n' + marker, 1)
    path.write_text(html, encoding='utf-8')
