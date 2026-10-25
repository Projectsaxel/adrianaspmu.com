#!/usr/bin/env python3
"""Trava de conteudo duplicado entre as paginas servico x cidade.

POR QUE EXISTE (auditoria 24-25/10/2026): os 12 pares Salem x Wilmington
tinham de 81% a 87% das palavras em secoes iguais, trocando so o nome da
cidade. A politica de spam do Google trata isso como doorway ("varias
paginas segmentadas por cidades que levam a uma pagina") e trata reescrever
com sinonimos como ofuscacao. Resultado medido: 7 das 24 fora do indice.

O QUE MEDE: a fracao das sequencias de 5 palavras do <main> de uma pagina
que tambem aparecem na pagina irma, com nomes de cidade, rua, rota e
telefone neutralizados (trocar "Salem" por "Wilmington" nao conta como
diferenca). Vale o maior dos dois sentidos.

QUANDO TRAVA: so nos pares em que pelo menos uma pagina ja foi reescrita
(marcador data-city-v2 no <main>). Os pares antigos sao reportados, mas nao
travam o deploy, senao nenhum deploy passaria ate a reescrita terminar.

LIMITE: 30%. Rode no BUILD (depois do enrich_pages.py), porque e o HTML
que o Google le que importa, nao o fonte.

Uso: python3 tests/check_city_pairs.py [--todos]
"""
import glob
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMITE = 0.30
N = 5

NEUTRO = re.compile(
    r"\b(Salem|Wilmington|New Hampshire|Massachusetts|NH|MA|Main Street|Lowell Street|"
    r"117A|211|Suite F|Route 97|Route 129|978|781|223-7496|853-8063|03079|01887)\b")


def texto_main(fp):
    with open(fp, encoding="utf-8") as f:
        s = f.read()
    m = re.search(r"<main\b.*?</main>", s, re.S)
    if not m:
        return "", False
    bloco = m.group(0)
    v2 = "data-city-v2" in bloco[:200]
    bloco = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", bloco, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", bloco))
    t = NEUTRO.sub("X", t)
    return re.sub(r"\s+", " ", t).lower(), v2


def shingles(t):
    p = re.findall(r"[a-z0-9$%']+", t)
    return {" ".join(p[i:i + N]) for i in range(len(p) - N + 1)}


def compartilhado(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return max(inter / len(a), inter / len(b))


def main():
    todos = "--todos" in sys.argv
    falhas, linhas = [], []
    for salem in sorted(glob.glob(os.path.join(ROOT, "services/*/*/salem-nh/index.html"))):
        wil = salem.replace("/salem-nh/", "/wilmington-ma/")
        if not os.path.exists(wil):
            continue
        ts, vs = texto_main(salem)
        tw, vw = texto_main(wil)
        r = compartilhado(shingles(ts), shingles(tw))
        par = os.path.relpath(os.path.dirname(os.path.dirname(salem)), ROOT)
        trava = vs or vw
        linhas.append((par, r, trava))
        if trava and r > LIMITE:
            falhas.append(f"{par}: {r:.0%} de texto igual entre Salem e Wilmington (limite {LIMITE:.0%})")
    for par, r, trava in linhas:
        if trava or todos:
            print(f"{'v2 ' if trava else '   '}{par:45} {r:5.0%}")
    if falhas:
        print("check_city_pairs: FALHOU")
        for f in falhas:
            print("  " + f)
        return 1
    print(f"check_city_pairs: ok ({sum(1 for _, _, t in linhas if t)} par(es) reescrito(s) dentro do limite)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
