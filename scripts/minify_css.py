#!/usr/bin/env python3
"""Gera css/styles.min.css a partir de css/styles.css.

POR QUE EXISTE: o styles.css e fortemente comentado de proposito - os
comentarios registram POR QUE cada regra existe, incluindo armadilhas de
especificidade que ja custaram regressao. Mas eles viajam ate o navegador:
medido em 26/09/2026, o arquivo comprimido caia de 51,4 KB para 20,7 KB so
tirando comentario, e para 18,4 KB minificado. O CSS bloqueia a renderizacao
(o Lighthouse media 462 ms), entao esses 33 KB estao no caminho critico do LCP.

O FONTE CONTINUA SENDO css/styles.css. Depois de editar, rode este script.
    python3 scripts/minify_css.py

Minificacao conservadora de proposito: tira comentario, colapsa espaco e
remove o ponto-e-virgula antes de }. Nao reordena, nao funde regras, nao
encurta cor nem unidade - nada que possa mudar cascata ou especificidade.
"""
import re, sys, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FONTE = RAIZ / "css" / "styles.css"
SAIDA = RAIZ / "css" / "styles.min.css"

def minifica(t: str) -> str:
    # Comentario CSS nao aninha. Conferido: nenhum "/*" dentro de url() ou
    # content: nesta folha, entao o regex e seguro aqui.
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*([{}:;,>~+])\s*", r"\1", t)
    t = re.sub(r";}", "}", t)
    # o combinador ~ tambem aparece em seletor de atributo [x~="y"]: ali o
    # espaco ja foi removido e nao faz falta, mas a barra de media query sim
    t = re.sub(r"\band\(", "and (", t)
    return t.strip()

def main():
    if not FONTE.exists():
        sys.exit(f"nao achei {FONTE}")
    bruto = FONTE.read_text(encoding="utf-8")
    saida = minifica(bruto)
    # Compara contra o fonte JA SEM COMENTARIO: ha chaves dentro de comentario
    # (exemplos de regra), e elas somem legitimamente. Comparar com o bruto
    # acusava divergencia falsa.
    limpo = re.sub(r"/\*.*?\*/", "", bruto, flags=re.S)
    for ch in "{}":
        if limpo.count(ch) != saida.count(ch):
            sys.exit(f"chave {ch} nao bate ({limpo.count(ch)} -> {saida.count(ch)}) - abortado")
    for regra in ("@media", "@font-face", "@supports", "@keyframes"):
        if limpo.count(regra) != saida.count(regra):
            sys.exit(f"{regra} nao bate - abortado")
    SAIDA.write_text(saida, encoding="utf-8")
    print(f"{FONTE.name} {len(bruto)/1024:.1f} KB -> {SAIDA.name} {len(saida)/1024:.1f} KB "
          f"({(1-len(saida)/len(bruto))*100:.0f}% menor)")

if __name__ == "__main__":
    main()
