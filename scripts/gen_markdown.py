#!/usr/bin/env python3
"""Gera o gemeo .md de cada pagina HTML, para negociacao de conteudo.

Por que existe: acceptmarkdown.com pede que o servidor devolva text/markdown
quando o cliente manda "Accept: text/markdown". Converter HTML em markdown em
tempo de request custaria CPU por visita; gerar no build custa uma vez.

Os arquivos saem em content/<caminho>/index.md. O Worker escolhe qual servir.
"""
import html as H
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "content")
SKIP_DIRS = {"node_modules", "assets", "scripts", "src", "css", "js",
             ".git", ".github", "docs", "content", ".wrangler"}


def clean(text):
    return re.sub(r"[ \t]+", " ", H.unescape(text)).strip()


def inline(frag):
    """Converte marcacao inline de HTML para markdown."""
    frag = re.sub(r"<br\s*/?>", "\n", frag)
    frag = re.sub(r"<a\b[^>]*href=\"([^\"]*)\"[^>]*>(.*?)</a>",
                  lambda m: "[%s](%s)" % (clean(re.sub(r"<[^>]+>", "", m.group(2))), m.group(1)),
                  frag, flags=re.S)
    frag = re.sub(r"<(strong|b)\b[^>]*>(.*?)</\1>", r"**\2**", frag, flags=re.S)
    frag = re.sub(r"<(em|i)\b[^>]*>(.*?)</\1>", r"*\2*", frag, flags=re.S)
    frag = re.sub(r"<code\b[^>]*>(.*?)</code>", r"`\1`", frag, flags=re.S)
    return clean(re.sub(r"<[^>]+>", "", frag))


def table(block):
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", block, re.S)
    out = []
    for i, row in enumerate(rows):
        cells = [inline(c) for c in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.S)]
        if not cells:
            continue
        out.append("| " + " | ".join(cells) + " |")
        if i == 0:
            out.append("|" + "|".join([" --- "] * len(cells)) + "|")
    return "\n".join(out)


def convert(path):
    src = open(path, encoding="utf-8").read()
    m = re.search(r"<main.*?</main>", src, re.S)
    if not m:
        return None
    body = re.sub(r"<(script|style|nav|form)\b.*?</\1>", "", m.group(0), flags=re.S)

    t = re.search(r"<title>(.*?)</title>", src, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', src)
    can = re.search(r'<link rel="canonical" href="([^"]*)"', src)

    parts = []
    if t:
        parts.append("<!-- %s -->" % clean(re.sub(r"<[^>]+>", "", t.group(1))))
    if can:
        parts.append("<!-- canonical: %s -->" % can.group(1))
    if d:
        parts.append("> " + clean(d.group(1)))
    parts.append("")

    # percorre os blocos na ordem em que aparecem
    pattern = (r"<h([1-6])\b[^>]*>(.*?)</h\1>"
               r"|<p\b[^>]*>(.*?)</p>"
               r"|<li\b[^>]*>(.*?)</li>"
               r"|<table\b[^>]*>(.*?)</table>"
               r"|<figcaption\b[^>]*>(.*?)</figcaption>")
    for mm in re.finditer(pattern, body, re.S):
        if mm.group(1):
            txt = inline(mm.group(2))
            if txt:
                parts += ["", "#" * int(mm.group(1)) + " " + txt, ""]
        elif mm.group(3) is not None:
            txt = inline(mm.group(3))
            if txt:
                parts.append(txt + "\n")
        elif mm.group(4) is not None:
            txt = inline(mm.group(4))
            if txt:
                parts.append("- " + txt)
        elif mm.group(5) is not None:
            tb = table("<table>" + mm.group(5) + "</table>")
            if tb:
                parts += ["", tb, ""]
        elif mm.group(6) is not None:
            txt = inline(mm.group(6))
            if txt:
                parts.append("*%s*\n" % txt)

    md = re.sub(r"\n{3,}", "\n\n", "\n".join(parts)).strip() + "\n"
    return md


def walk():
    made = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn not in ("index.html", "404.html"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            md = convert(full)
            if md is None:
                continue
            out = os.path.join(OUT_DIR, rel[: -len(".html")] + ".md")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            prev = open(out, encoding="utf-8").read() if os.path.exists(out) else None
            if prev != md:
                open(out, "w", encoding="utf-8").write(md)
            made += 1
    return made


if __name__ == "__main__":
    n = walk()
    print("gen_markdown: %d paginas convertidas" % n)
