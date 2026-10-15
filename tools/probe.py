"""Headless Chrome helpers for the blog's tests and screenshots.

Headless Chrome will not make a window narrower than 500 px, so phone widths are measured
and photographed inside an iframe of the wanted width.
"""
import contextlib
import functools
import http.server
import os
import re
import socketserver
import subprocess
import threading
import uuid
from pathlib import Path

CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def available():
    return Path(CHROME).exists()


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextlib.contextmanager
def serve(root):
    """Serve root's parent, so the site appears at /<root folder name>/ as on GitHub Pages. Yields that base URL."""
    root = Path(root).resolve()
    handler = functools.partial(_Quiet, directory=str(root.parent))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}/{root.name}/"
        finally:
            httpd.shutdown()


def _chrome(args):
    base = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--virtual-time-budget=4000"]
    return subprocess.run(base + args, capture_output=True, text=True, timeout=120)


def dump_dom(url, width=1200):
    """The page's DOM after load, as HTML text."""
    return _chrome([f"--window-size={max(width, 500)},900", "--dump-dom", url]).stdout


def _wrapper(root, page, width, height, script="", js=True):
    root = Path(root).resolve()
    w = root / f"_probe_{uuid.uuid4().hex[:8]}.html"
    w.write_text(f'<!DOCTYPE html><html><body style="margin:0;background:#111">'
                 f'<iframe id="f" src="{page}"{"" if js else ' sandbox="allow-same-origin"'} style="width:{width}px;height:{height}px;border:0;display:block"></iframe>'
                 f"{script}</body></html>", encoding="utf-8")
    return w


def measure(root, page, width, expr, js=True):
    """Evaluate a JavaScript expression against `page` (a path inside root) shown `width` px wide.
    In the expression, `document` and `window` are the page's own. With js=False the page runs
    with scripts disabled (a sandboxed frame), as for a reader without JavaScript. Returns text."""
    script = ('<script>document.getElementById("f").onload=function(){var f=this;setTimeout(function(){'
              'var r=(function(document,window){return ' + expr + '})(f.contentDocument,f.contentWindow);'
              'document.documentElement.setAttribute("data-probe",String(r));},300);};</script>')
    w = _wrapper(root, page, width, 900, script, js)
    try:
        with serve(root) as base:
            dom = dump_dom(base + w.name, width)
    finally:
        w.unlink()
    m = re.search(r'data-probe="([^"]*)"', dom)
    if not m:
        raise RuntimeError(f"no probe value from {page} at {width} px")
    return m.group(1).replace("&amp;", "&").replace("&quot;", '"')


def screenshot(root, page, width, height, out):
    """Photograph `page` at `width` x `height` CSS px into the PNG file `out`."""
    w = _wrapper(root, page, width, height)
    try:
        with serve(root) as base:
            _chrome([f"--window-size={max(width, 500)},{height}", f"--screenshot={Path(out).resolve()}", base + w.name])
    finally:
        w.unlink()
