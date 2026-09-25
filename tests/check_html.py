#!/usr/bin/env python3
"""Portao de qualidade do build: roda no CI antes do deploy.

Cada checagem aqui ja foi um defeito publicado ou quase publicado
(auditoria pre-lancamento de 25/09/2026). Se falhar, o deploy para.

1. Link que aponta para a propria pagina: href feito so de "./" fora da
   raiz. O travessao.py colapsou "../" em "./" e 211 links Home/breadcrumb
   passaram a apontar para a pagina atual.
2. <head> quebrado: um ">" sobrando numa meta description fez o parser
   mandar canonical, og e JSON-LD para o <body> do Apprenticeship.
3. aggregateRating: proibido sem depoimentos individuais visiveis
   (self-serving reviews). O gerador antigo ainda tinha um.
4. "18+ years": a experiencia e 20+ (PMU desde 2006).
"""
import os
import re
import sys

import html5lib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {".git", "node_modules", "scripts", "src", "docs", "tests", ".github", ".wrangler"}

erros = []


def paginas():
    for dp, dirs, fs in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for fn in fs:
            if fn == "index.html" or fn == "404.html":
                yield os.path.join(dp, fn)


for fp in paginas():
    rel = os.path.relpath(fp, ROOT)
    h = open(fp, encoding="utf-8").read()

    if rel != "index.html":
        for m in re.finditer(r'href="((?:\./)+)"', h):
            erros.append(f"{rel}: link para a propria pagina href=\"{m.group(1)}\"")

    doc = html5lib.parse(h, namespaceHTMLElements=False)
    body = doc.find("body")
    if body is not None:
        for tag in body.iter():
            if tag.tag == "link" and tag.get("rel") == "canonical":
                erros.append(f"{rel}: <link rel=canonical> caiu no <body> (head quebrado)")
            if tag.tag == "meta" and (tag.get("property") or "").startswith("og:"):
                erros.append(f"{rel}: meta og: caiu no <body> (head quebrado)")
                break

    if re.search(r"aggregateRating", h, re.I):
        erros.append(f"{rel}: aggregateRating no schema")

    if re.search(r"18\+ ?years|over 18 years", h, re.I):
        erros.append(f"{rel}: '18+ years' (o correto e 20+)")

llms = os.path.join(ROOT, "llms.txt")
if os.path.exists(llms) and re.search(r"18\+ ?years", open(llms, encoding="utf-8").read(), re.I):
    erros.append("llms.txt: '18+ years' (o correto e 20+)")

if erros:
    print(f"check_html: {len(erros)} problema(s)")
    for e in erros[:60]:
        print("  " + e)
    sys.exit(1)
print("check_html: ok")
