#!/usr/bin/env python3
"""sitemap.xml com <lastmod> real, gerado no BUILD a partir do git.

Auditoria de SEO de 25/09/2026, achado 4.1: 60 das 63 URLs declaravam
<lastmod>2026-09-08</lastmod>, editado a mao, quando todas as paginas
tinham mudado ate 25/09. O Google so usa o lastmod se ele for
"consistente e comprovavelmente correto"; quando nao confere, ignora o
sinal. E o mesmo valor alimentava o WebPage.dateModified do schema.

Regra agora: lastmod de cada URL = data (YYYY-MM-DD) do ultimo commit que
tocou o HTML DE ORIGEM da pagina:

    git log -1 --format=%cs -- <pagina>/index.html

A mesma funcao (lastmod_for_url) e importada por enrich_pages.py para o
WebPage.dateModified, entao sitemap e schema nunca divergem.

O que NAO conta como alteracao da pagina (e esta certo assim): mudar o
rodape no js/main.js, o CSS ou as avaliacoes do Google. O Google considera
significativa a mudanca no conteudo principal, dados estruturados ou
links, nao a data de copyright.

Fallback seguro (git ausente, checkout raso ou arquivo sem historico):
usa o lastmod que ja esta no sitemap.xml do repositorio; se nao houver,
a URL sai SEM lastmod. Nunca inventa data. Checkout raso (fetch-depth: 1,
o padrao do actions/checkout) e detectado de proposito: nele o git log
devolveria a data do HEAD para TODAS as paginas, que e uma mentira pior
do que nao declarar nada. Por isso o deploy.yml usa fetch-depth: 0.

<priority> e <changefreq> nao existem mais: o Google ignora os dois.

Uso: python3 scripts/sitemap_lastmod.py   (reescreve sitemap.xml)
"""
import os
import re
import subprocess
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://adrianaspmu.com"
SITEMAP = os.path.join(ROOT, "sitemap.xml")

# Pastas que nao sao paginas publicas (mesma lista do tests/check_html.py)
SKIP_DIRS = {".git", "node_modules", "scripts", "src", "docs", "tests", ".github",
             ".wrangler", "content"}
# 404.html nao e indexavel
SKIP_FILES = {"404.html"}


def _git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


@lru_cache(maxsize=1)
def git_usable():
    """True so com repositorio git COMPLETO (nao raso)."""
    if _git("rev-parse", "--is-inside-work-tree") != "true":
        return False
    return _git("rev-parse", "--is-shallow-repository") == "false"


@lru_cache(maxsize=1)
def _committed_lastmod():
    """lastmod ja declarado no sitemap.xml do repo (fallback sem git)."""
    out = {}
    if not os.path.exists(SITEMAP):
        return out
    with open(SITEMAP, encoding="utf-8") as f:
        sm = f.read()
    for block in re.findall(r"<url>(.*?)</url>", sm, re.S):
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        mod = re.search(r"<lastmod>([^<]+)</lastmod>", block)
        if loc and mod:
            out[loc.group(1).strip()] = mod.group(1).strip()
    return out


def url_to_file(url):
    """https://adrianaspmu.com/about/ -> about/index.html (relativo a ROOT)."""
    path = url.replace(BASE, "").strip("/")
    return f"{path}/index.html" if path else "index.html"


def file_to_url(rel):
    rel = rel.replace(os.sep, "/")
    path = rel[: -len("index.html")]
    return f"{BASE}/{path}"


@lru_cache(maxsize=None)
def lastmod_for_file(rel):
    """Data do ultimo commit que tocou o arquivo, ou None."""
    if git_usable():
        d = _git("log", "-1", "--format=%cs", "--", rel)
        if d and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            return d
    return _committed_lastmod().get(file_to_url(rel))


def lastmod_for_url(url):
    return lastmod_for_file(url_to_file(url))


def _is_indexable(fp, url):
    """Fica fora do sitemap a pagina com noindex ou canonical para outra URL."""
    with open(fp, encoding="utf-8") as f:
        head = f.read().split("</head>", 1)[0]
    if re.search(r'<meta[^>]+name="robots"[^>]+noindex', head, re.I):
        return False
    can = re.search(r'<link rel="canonical" href="([^"]+)"', head)
    return not can or can.group(1) == url


def pages():
    out = []
    for dp, dirs, fs in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fs:
            if fn != "index.html":
                continue
            rel = os.path.relpath(os.path.join(dp, fn), ROOT).replace(os.sep, "/")
            if rel in SKIP_FILES:
                continue
            url = file_to_url(rel)
            if _is_indexable(os.path.join(ROOT, rel), url):
                out.append((url, rel))
    return sorted(out)


def write_sitemap():
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    sem_data = []
    for url, rel in pages():
        mod = lastmod_for_file(rel)
        if mod:
            lines.append(f"  <url><loc>{url}</loc><lastmod>{mod}</lastmod></url>")
        else:
            sem_data.append(url)
            lines.append(f"  <url><loc>{url}</loc></url>")
    lines.append("</urlset>")
    with open(SITEMAP, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    fonte = "git" if git_usable() else "fallback (sitemap do repo)"
    print(f"sitemap_lastmod: {len(lines) - 3} URLs, lastmod via {fonte}"
          + (f"; {len(sem_data)} sem lastmod" if sem_data else ""))


if __name__ == "__main__":
    write_sitemap()
