#!/usr/bin/env python
"""
Local HTTP server for browsing and searching markdown files.

Usage:
    src/main/model/serve_markdown.sh --markdown <dir> [--port 8182]
    src/main/model/serve_markdown.sh --markdown <dir> --daemon [--port 8182]
    src/main/model/serve_markdown.sh stop
"""
import argparse
import json
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT  = Path(__file__).resolve().parents[3]
STATIC_DIR = REPO_ROOT / 'lib' / 'serve_markdown'

ASSETS = {
    'marked.min.js':      'https://cdn.jsdelivr.net/npm/marked@9/marked.min.js',
    'katex.min.js':       'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js',
    'katex.min.css':      'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css',
    'auto-render.min.js': 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js',
}
FONTS = [
    'KaTeX_Main-Regular.woff2', 'KaTeX_Main-Bold.woff2', 'KaTeX_Main-Italic.woff2',
    'KaTeX_Math-Italic.woff2',  'KaTeX_Size1-Regular.woff2', 'KaTeX_Size2-Regular.woff2',
    'KaTeX_Size3-Regular.woff2', 'KaTeX_Size4-Regular.woff2',
    'KaTeX_AMS-Regular.woff2',  'KaTeX_Caligraphic-Regular.woff2',
    'KaTeX_Fraktur-Regular.woff2', 'KaTeX_SansSerif-Regular.woff2',
    'KaTeX_Script-Regular.woff2',  'KaTeX_Typewriter-Regular.woff2',
]

def ensure_assets() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in ASSETS.items():
        dest = STATIC_DIR / name
        if not dest.exists():
            print(f'Downloading {name}…', flush=True)
            urllib.request.urlretrieve(url, dest)
    fonts_dir = STATIC_DIR / 'fonts'
    fonts_dir.mkdir(exist_ok=True)
    base = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/fonts/'
    for f in FONTS:
        dest = fonts_dir / f
        if not dest.exists():
            try: urllib.request.urlretrieve(base + f, dest)
            except Exception as e: print(f'Warning: could not download {f}: {e}', flush=True)


def conversations(markdown_dir: Path) -> list[dict]:
    """All .md files under the tree, sorted newest first."""
    result = []
    for md in sorted(markdown_dir.rglob('*.md'),
                     key=lambda p: p.stat().st_mtime, reverse=True):
        title = md.stem.replace('_', ' ').title()
        try:
            for line in md.open(errors='replace'):
                if line.startswith('# '):
                    title = line[2:].strip(); break
        except Exception:
            pass
        result.append({'title': title, 'path': str(md.relative_to(REPO_ROOT))})
    return result


def search(query: str, markdown_dir: Path) -> list[dict]:
    """Case-insensitive full-text grep across the markdown tree."""
    try:
        files = subprocess.run(
            ['grep', '-rli', '--include=*.md', query, str(markdown_dir)],
            capture_output=True, text=True, timeout=10
        ).stdout.strip().splitlines()
    except Exception:
        return []
    results = []
    for f in files:
        p = Path(f)
        title = p.stem.replace('_', ' ').title()
        try:
            for line in p.open(errors='replace'):
                if line.startswith('# '):
                    title = line[2:].strip(); break
        except Exception:
            pass
        try:
            snippet = subprocess.run(
                ['grep', '-m', '3', '-i', '-n', query, f],
                capture_output=True, text=True
            ).stdout.strip()
        except Exception:
            snippet = ''
        results.append({'title': title, 'path': str(p.relative_to(REPO_ROOT)), 'snippet': snippet})
    return results


VIEWER_TEMPLATE = '''<!doctype html><html><head>
<meta charset="utf-8"><title>{name}</title>
<link rel="stylesheet" href="/static/katex.min.css">
<script src="/static/marked.min.js"></script>
<script defer src="/static/katex.min.js"></script>
<script defer src="/static/auto-render.min.js"></script>
<style>
  body{{max-width:860px;margin:2rem auto;padding:0 1.5rem;
       font:16px/1.7 system-ui,sans-serif;background:#1a1a1a;color:#ddd}}
  a{{color:#88aaff}} h1,h2,h3{{color:#eee}} hr{{border-color:#333}}
  code{{background:#2a2a2a;padding:.1em .3em;border-radius:3px;font-size:.9em}}
  pre{{background:#222;padding:1rem;border-radius:6px;overflow-x:auto}}
  pre code{{background:none;padding:0}}
  blockquote{{border-left:3px solid #555;margin:0;padding-left:1rem;color:#999}}
  #back{{position:fixed;top:1rem;right:1rem;font-size:.8rem}}
  #meta{{font-size:.75rem;color:#888;border-collapse:collapse;margin-bottom:1.5rem}}
  #meta td{{padding:.05rem .6rem .05rem 0;vertical-align:top}}
  #meta td:first-child{{color:#666;white-space:nowrap}}
</style></head><body>
<a id="back" href="/">← all conversations</a>
<div id="content"></div>
<script>
const raw={raw};const lines=raw.split('\\n');const CHUNK=150;
const root=document.getElementById('content');
const mathOpts={{delimiters:[
  {{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}},
  {{left:'\\\\(',right:'\\\\)',display:false}},{{left:'\\\\[',right:'\\\\]',display:true}}
]}};
let i=0;
/* provenance frontmatter (dressing, not conversation — see markdownConversation v3):
   marked has no YAML support, so lift a leading --- block into a muted meta table.
   Values that ARE references become links: the uuid item is the conversation's one
   claude.ai link (the old <url> preamble line retired into it), and relative paths
   (the summaries index, the conversation backlink) resolve against the served tree.
   A code-session's uuid is a session id, not a claude.ai chat — no link exists. */
if(lines[0]==='---'){{const c=lines.indexOf('---',1);if(c>0){{
  const t=document.createElement('table');t.id='meta';
  const isCode=lines.slice(1,c).includes('source: code-session');
  for(const l of lines.slice(1,c)){{const j=l.indexOf(': ');const r=t.insertRow();
    const k=j<0?l:l.slice(0,j),v=j<0?'':l.slice(j+2);
    r.insertCell().textContent=k;
    const cell=r.insertCell();
    const href=/^(\\.\\.?\\/|https?:\\/\\/)/.test(v)?v
      :(k==='uuid'&&!isCode&&/^[0-9a-f-]{{36}}$/.test(v)?'https://claude.ai/chat/'+v:null);
    if(href){{const a=document.createElement('a');a.href=href;a.textContent=v;cell.appendChild(a);}}
    else cell.textContent=v;}}
  root.appendChild(t);i=c+1;}}}}
function jump(){{
  if(!location.hash)return;
  const el=document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if(el)el.scrollIntoView();
}}
function chunkEnd(start){{
  /* never split a fenced code block across chunks: marked parses each chunk
     independently, so a fence opened in one chunk would leak into the next */
  let end=Math.min(start+CHUNK,lines.length),open=false;
  for(let k=start;k<end;k++)if(/^```/.test(lines[k]))open=!open;
  while(open&&end<lines.length){{if(/^```/.test(lines[end]))open=!open;end++;}}
  return end;
}}
function tick(){{
  if(i>=lines.length){{
    if(window.renderMathInElement)renderMathInElement(root,mathOpts);
    /* deep links (#<turn anchor>): the target exists only after chunked
       rendering — jump now, and AGAIN once webfonts settle: KaTeX's fonts
       arrive async and reflow every formula, silently dragging the viewport
       off the anchor on math-heavy pages */
    jump();
    if(document.fonts&&document.fonts.ready)
      document.fonts.ready.then(()=>requestAnimationFrame(jump));
    return;
  }}
  const end=chunkEnd(i);
  const d=document.createElement('div');
  d.innerHTML=marked.parse(lines.slice(i,end).join('\\n'));
  root.appendChild(d);i=end;
  /* setTimeout unconditionally: VSCode's simple-browser webview starves
     requestIdleCallback under scroll, freezing rendering after a few chunks */
  setTimeout(tick,0);
}}
tick();
</script></body></html>'''


INDEX_TEMPLATE = '''<!doctype html><html><head>
<meta charset="utf-8"><title>Conversations</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font:15px/1.6 system-ui,sans-serif;background:#1a1a1a;color:#ddd;padding:2rem}}
  h1{{font-size:1.1rem;font-weight:500;color:#888;margin-bottom:1.2rem}}
  #q{{width:100%;padding:.6rem 1rem;font-size:1rem;background:#2a2a2a;
      border:1px solid #444;border-radius:6px;color:#ddd;margin-bottom:1.5rem}}
  #q:focus{{outline:none;border-color:#666}}
  .item{{padding:.5rem 0;border-bottom:1px solid #222}}
  .item a{{color:#ccc;text-decoration:none;font-size:.95rem}}
  .item a:hover{{color:#fff}}
  .snippet{{font-size:.8rem;color:#666;font-family:monospace;margin-top:.2rem;white-space:pre}}
  #status{{color:#555;font-size:.8rem;margin-bottom:1rem}}
</style></head><body>
<h1>Conversations ({count})</h1>
<input id="q" type="text" placeholder="Search…" autofocus>
<div id="status"></div>
<div id="list">{items}</div>
<script>
const all={data};
const q=document.getElementById('q');
const list=document.getElementById('list');
const status=document.getElementById('status');
let timer;
q.addEventListener('input',()=>{{clearTimeout(timer);timer=setTimeout(doSearch,300)}});
async function doSearch(){{
  const val=q.value.trim();
  if(!val){{renderAll();return;}}
  status.textContent='Searching…';
  const r=await fetch('/search?q='+encodeURIComponent(val));
  const hits=await r.json();
  status.textContent=hits.length+' result'+(hits.length!==1?'s':'');
  list.innerHTML=hits.map(h=>`<div class="item">
    <a href="/file/${{h.path}}">${{h.title}}</a>
    ${{h.snippet?'<div class="snippet">'+esc(h.snippet)+'</div>':''}}
  </div>`).join('');
}}
function renderAll(){{
  status.textContent='';
  list.innerHTML=all.map(h=>`<div class="item"><a href="/file/${{h.path}}">${{h.title}}</a></div>`).join('');
}}
function esc(s){{return s.replace(/&/g,'&amp;').replace(/</g,'&lt;')}}
</script></body></html>'''


def make_handler(markdown_dir: Path) -> type:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            print(format % args)

        def do_GET(self):
            parsed = urlparse(self.path)
            path   = parsed.path.lstrip('/')

            if path == '' or path == 'index.html':
                convs = conversations(markdown_dir)
                items = ''.join(
                    f'<div class="item"><a href="/file/{c["path"]}">{c["title"]}</a></div>'
                    for c in convs
                )
                body = INDEX_TEMPLATE.format(
                    count=len(convs),
                    items=items,
                    data=json.dumps(convs),
                )
                self._send(200, 'text/html', body.encode())

            elif path == 'search':
                q = parse_qs(parsed.query).get('q', [''])[0]
                self._send(200, 'application/json', json.dumps(search(q, markdown_dir)).encode())

            elif path.startswith('static/'):
                asset = STATIC_DIR / path[len('static/'):]
                if asset.exists() and asset.is_file():
                    ct = ('text/css' if asset.suffix == '.css' else
                          'font/woff2' if asset.suffix == '.woff2' else
                          'application/javascript')
                    self.send_response(200)
                    self.send_header('Content-Type', ct)
                    self.send_header('Cache-Control', 'max-age=86400')
                    self.end_headers()
                    self.wfile.write(asset.read_bytes())
                else:
                    self._send(404, 'text/plain', b'not found')

            elif path.startswith('file/'):
                rel   = path[len('file/'):]
                fpath = REPO_ROOT / rel
                if not fpath.exists() and '/' in rel:
                    parent, name = rel.rsplit('/', 1)
                    fpath = REPO_ROOT / parent / name.replace('-', '_')
                if fpath.exists() and fpath.is_file():
                    raw  = fpath.read_text(errors='replace')
                    body = VIEWER_TEMPLATE.format(
                        name=fpath.name,
                        raw=json.dumps(raw),
                    )
                    self._send(200, 'text/html', body.encode())
                else:
                    self._send(404, 'text/plain', b'not found')
            else:
                self._send(404, 'text/plain', b'not found')

        def _send(self, code: int, ct: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header('Content-Type', ct + '; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)

    return Handler


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--markdown', required=True, metavar='DIR',
                   help='Directory tree of markdown files to serve (e.g. gen/markdown)')
    p.add_argument('--port', type=int, default=8182, help='Port (default: 8182)')
    args = p.parse_args()

    # Absolutize WITHOUT resolving symlinks: lib/ is a symlink into the shared
    # medium, and resolving through it strands every served file outside
    # REPO_ROOT — relative_to() then fails, and the /file/ route needs
    # repo-relative spellings that traverse the symlink, not physical paths
    # beyond it.
    markdown_dir = Path(args.markdown)
    if not markdown_dir.is_absolute():
        markdown_dir = Path.cwd() / markdown_dir

    ensure_assets()

    print(f'Browse: http://localhost:{args.port}', flush=True)

    try:
        HTTPServer(('', args.port), make_handler(markdown_dir)).serve_forever()
    except OSError as e:
        if e.errno == 48:
            print(f'Port {args.port} already in use.', flush=True)
            print(f'To fix: lsof -ti :{args.port} | xargs kill', flush=True)
            print(f'     or: src/main/model/serve_markdown.sh stop', flush=True)
            sys.exit(1)
        raise
