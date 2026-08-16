#!/usr/bin/env python3
"""
Enriquecimento SEO das paginas no BUILD (roda no deploy, antes do wrangler).

Por que no build e nao no repo: sao 63 paginas; commitar o resultado
transformado em cada uma esconde a fonte da verdade e infla cada diff.
O repo guarda o conteudo; este script injeta a camada tecnica de SEO.
E idempotente: pode rodar duas vezes sem duplicar nada.

O que injeta (auditoria de 16/08/2026):
  1. Open Graph + Twitter Card em toda pagina (og:image 1200x630)
  2. Schema por tipo de pagina, e a unidade SALEM NH no grafo global
     (antes o site declarava apenas Wilmington para o Google):
     Service+Offer, FAQPage, BreadcrumbList, Person na about
  3. LCP: primeira imagem da pagina vira eager + fetchpriority=high
     (+ preload do hero na home)
  4. CLS: width/height reais em toda <img> local que nao tiver
"""
import json
import os
import re
import sys
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://adrianaspmu.com"
OG_DEFAULT = f"{BASE}/assets/images/og/og-default.jpg"

SALEM_NODE = {
    "@type": "BeautySalon",
    "@id": f"{BASE}/#salem",
    "name": "Adriana's Permanent Makeup, Salem NH",
    "additionalType": "https://schema.org/HealthAndBeautyBusiness",
    "url": f"{BASE}/locations/salem-nh/",
    "telephone": "+1-978-223-7496",
    "parentOrganization": {"@id": f"{BASE}/#organization"},
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "117A Main Street",
        "addressLocality": "Salem",
        "addressRegion": "NH",
        "postalCode": "03079",
        "addressCountry": "US",
    },
    "geo": {"@type": "GeoCoordinates", "latitude": 42.782612, "longitude": -71.228213},
    "image": f"{BASE}/assets/images/locations/adrianas-permanent-makeup-salem-nh-storefront.jpg",
    "priceRange": "$250-$850",
}


# ---------- utilidades ----------

def img_size(path):
    """Dimensoes de PNG/JPEG/WebP/SVG sem depender de bibliotecas externas."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        if head.startswith(b"\x89PNG"):
            w, h = struct.unpack(">II", head[16:24])
            return w, h
        if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
            if head[12:16] == b"VP8X":
                w = int.from_bytes(head[24:27], "little") + 1
                h = int.from_bytes(head[27:30], "little") + 1
                return w, h
            if head[12:16] == b"VP8 ":
                w = int.from_bytes(head[26:28], "little") & 0x3FFF
                h = int.from_bytes(head[28:30], "little") & 0x3FFF
                return w, h
            if head[12:16] == b"VP8L":
                b = head[21:25]
                w = 1 + (((b[1] & 0x3F) << 8) | b[0])
                h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
                return w, h
        if head[:3] == b"\xff\xd8\xff":  # JPEG
            with open(path, "rb") as f:
                f.read(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        return None
                    if marker[1] in (0xC0, 0xC1, 0xC2, 0xC3):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    size = struct.unpack(">H", f.read(2))[0]
                    f.seek(size - 2, 1)
        if b"<svg" in head:
            m = re.search(rb'width="(\d+)"[^>]*height="(\d+)"', head)
            if m:
                return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return None


def get(pattern, s, flags=0):
    m = re.search(pattern, s, flags)
    return m.group(1).strip() if m else None


# ---------- transformacoes ----------

def add_og(s, page_dir):
    if 'property="og:title"' in s:
        return s
    title = get(r"<title>(.*?)</title>", s, re.S) or "Adriana's Permanent Makeup"
    desc = get(r'<meta name="description" content="([^"]*)"', s) or title
    canonical = get(r'<link rel="canonical" href="([^"]*)"', s) or BASE + "/"
    og = (
        f'<meta property="og:type" content="website">'
        f'<meta property="og:site_name" content="Adriana\'s Permanent Makeup">'
        f'<meta property="og:url" content="{canonical}">'
        f'<meta property="og:title" content="{title}">'
        f'<meta property="og:description" content="{desc}">'
        f'<meta property="og:image" content="{OG_DEFAULT}">'
        f'<meta property="og:image:width" content="1200">'
        f'<meta property="og:image:height" content="630">'
        f'<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{title}">'
        f'<meta name="twitter:description" content="{desc}">'
        f'<meta name="twitter:image" content="{OG_DEFAULT}">'
    )
    return s.replace("</head>", og + "\n</head>", 1)


def enrich_schema(s, path_rel):
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    if not m:
        return s
    try:
        data = json.loads(m.group(1))
    except Exception:
        return s
    graph = data.get("@graph")
    if not isinstance(graph, list):
        return s

    ids = {n.get("@id") for n in graph if isinstance(n, dict)}

    # 1. Salem NH no grafo de TODAS as paginas
    if f"{BASE}/#salem" not in ids:
        graph.append(SALEM_NODE)

    canonical = get(r'<link rel="canonical" href="([^"]*)"', s) or BASE + "/"

    # 2. Service + Offer nas paginas de servico (nao nas variantes de cidade)
    svc = re.match(r"services/([a-z-]+)/([a-z0-9-]+)/index\.html$", path_rel)
    if svc and not any(n.get("@type") == "Service" for n in graph if isinstance(n, dict)):
        name = get(r"<h1[^>]*>(.*?)</h1>", s, re.S)
        price = get(r"Starting at \$(\d+)", s)
        if name:
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", name))
            node = {
                "@type": "Service",
                "@id": canonical + "#service",
                "name": name,
                "serviceType": "Permanent makeup",
                "url": canonical,
                "provider": [{"@id": f"{BASE}/#wilmington"}, {"@id": f"{BASE}/#salem"}],
                "areaServed": ["Wilmington MA", "Salem NH"],
            }
            if price:
                node["offers"] = {
                    "@type": "Offer",
                    "price": price,
                    "priceCurrency": "USD",
                    "url": canonical,
                }
            graph.append(node)

    # 3. FAQPage onde ha FAQ visivel (2+ pares pergunta/resposta)
    if "faq-item" in s and not any(n.get("@type") == "FAQPage" for n in graph if isinstance(n, dict)):
        pairs = re.findall(
            r'class="faq-item"><button[^>]*>(.*?)</button><div class="faq-answer">(.*?)</div>',
            s, re.S,
        )
        qa = []
        for q, a in pairs:
            q = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", q)).strip()
            a = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", a)).strip()
            if q and a:
                qa.append({
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a},
                })
        if len(qa) >= 2:
            graph.append({"@type": "FAQPage", "@id": canonical + "#faq", "mainEntity": qa})

    # 4. BreadcrumbList onde ha breadcrumb visivel
    bc = re.search(r'<nav class="breadcrumb[^"]*"[^>]*>(.*?)</nav>', s, re.S)
    if bc and not any(n.get("@type") == "BreadcrumbList" for n in graph if isinstance(n, dict)):
        items = []
        for i, mm in enumerate(re.finditer(r"<li[^>]*>(?:<a href=\"([^\"]*)\">)?(.*?)(?:</a>)?</li>", bc.group(1))):
            href, label = mm.group(1), re.sub(r"<[^>]+>", "", mm.group(2)).strip()
            item = {"@type": "ListItem", "position": i + 1, "name": label}
            if href:
                # resolve relativo contra o canonical
                depth = href.count("../")
                base_parts = canonical[len(BASE):].strip("/").split("/")
                kept = base_parts[: max(0, len(base_parts) - depth)]
                tail = href.replace("../", "")
                item["item"] = BASE + "/" + "/".join(p for p in kept[:0] + [tail.strip("/")] if p) + "/"
                item["item"] = item["item"].replace("//", "/").replace("https:/", "https://")
                if tail in ("", "./"):
                    item["item"] = BASE + "/"
            items.append(item)
        if items:
            graph.append({"@type": "BreadcrumbList", "@id": canonical + "#breadcrumb", "itemListElement": items})

    # 5. Person na about
    if path_rel == "about/index.html" and not any(n.get("@type") == "Person" for n in graph if isinstance(n, dict)):
        graph.append({
            "@type": "Person",
            "@id": f"{BASE}/about/#adriana",
            "name": "Adriana Souza Santos",
            "jobTitle": "Master Permanent Makeup Artist",
            "worksFor": {"@id": f"{BASE}/#organization"},
            "url": f"{BASE}/about/",
            "image": f"{BASE}/assets/images/about-adriana.jpg",
        })

    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return s[: m.start()] + '<script type="application/ld+json">' + out + "</script>" + s[m.end():]


def fix_lcp(s, path_rel):
    # primeira <img> do documento vira eager + fetchpriority (uma so)
    def repl(m):
        tag = m.group(0)
        if "fetchpriority" in tag:
            return tag
        tag = tag.replace('loading="lazy"', 'loading="eager" fetchpriority="high"')
        if "loading=" not in tag:
            tag = tag.replace("<img ", '<img loading="eager" fetchpriority="high" ', 1)
        return tag

    s = re.sub(r"<img [^>]*>", repl, s, count=1)

    if path_rel == "index.html" and "rel=\"preload\" as=\"image\"" not in s:
        s = s.replace(
            "</head>",
            f'<link rel="preload" as="image" href="/assets/images/hero.webp" fetchpriority="high">\n</head>',
            1,
        )
    return s


def fix_dimensions(s, page_dir):
    def repl(m):
        tag = m.group(0)
        if "width=" in tag or 'src="http' in tag or "data:image" in tag:
            return tag
        src = get(r'src="([^"]*)"', tag)
        if not src:
            return tag
        fs = os.path.normpath(os.path.join(page_dir, src))
        size = img_size(fs)
        if not size:
            return tag
        return tag[:-1] + f' width="{size[0]}" height="{size[1]}">'

    return re.sub(r"<img [^>]*>", repl, s)


def main():
    changed = 0
    for dirpath, _, files in os.walk(ROOT):
        if any(seg in dirpath for seg in (".git", "node_modules", "scripts", "src", "docs")):
            continue
        for fn in files:
            if fn != "index.html" and fn != "404.html":
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, ROOT).replace(os.sep, "/")
            with open(fp, encoding="utf-8") as f:
                s = f.read()
            orig = s
            if fn == "index.html":
                s = add_og(s, dirpath)
                s = enrich_schema(s, rel)
                s = fix_lcp(s, rel)
            s = fix_dimensions(s, dirpath)
            if s != orig:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(s)
                changed += 1
    print(f"enrich_pages: {changed} paginas enriquecidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
