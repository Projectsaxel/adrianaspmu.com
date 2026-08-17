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



FRESHA_W = ("https://www.fresha.com/a/adrianas-permanent-makeup-wilmington-ma-"
            "wilmington-211-lowell-street-jalpqett/all-offer?menu=true&share=true&pId=727586")
FRESHA_S = ("https://www.fresha.com/a/adrianas-permanent-makeup-salem-nh-"
            "salem-eua-117a-main-street-w0he16uu/all-offer?menu=true&share=true&pId=727586")
FRESHA_GENERIC = "https://www.fresha.com/book-now/adrianas-permanent-makeup-zeaseit5/all-offer?share=true&pId=727586"

# Meta descriptions reescritas (auditoria 16/08: fracas, duplicadas ou truncadas).
# Chave: caminho relativo da pagina. Valor: 140-160 chars com servico+cidade+CTA.
DESCRIPTIONS = {
    "services/eyebrows/index.html": "Microblading, nano brows, powder and combination brows in Wilmington MA and Salem NH. Compare techniques, see prices, and book a free consultation.",
    "services/lips/index.html": "Lip blush and dark lip neutralization in Wilmington MA and Salem NH. Natural color and defined contour, with the perfecting session included.",
    "services/eyeliner/index.html": "Permanent eyeliner in Wilmington MA and Salem NH: top, bottom, smokey effect and combo. Smudge-proof definition that survives the gym, from $250.",
    "services/combos/index.html": "Permanent makeup combo packages in Wilmington MA and Salem NH. Pair brows, lips and eyeliner in one plan and save, perfecting session included.",
    "services/touch-ups/index.html": "Yearly permanent makeup touch-ups in Wilmington MA and Salem NH. Keep brows, lips and eyeliner fresh with a refresh by the original artist.",
    "portfolio/index.html": "Real before and after photos of microblading, nano brows, lip blush and eyeliner by the Adriana's PMU artists in Wilmington MA and Salem NH.",
    "payment-plan/index.html": "Split your permanent makeup service into easy payments at Adriana's PMU. Flexible payment plans in Wilmington MA and Salem NH, no hidden fees.",
    "faq/index.html": "Answers about permanent makeup: pain, healing, duration, prices and aftercare, from Master PMU Artist Adriana Souza Santos in MA and NH.",
    "contact/index.html": "Contact Adriana's Permanent Makeup: Wilmington MA (781) 853-8063 or Salem NH (978) 223-7496. Send a message or book your consultation online.",
    "locations/index.html": "Two Adriana's Permanent Makeup studios: 211 Lowell Street, Wilmington MA and 117A Main Street, Salem NH. Addresses, phones and booking links.",
    "locations/salem-nh/index.html": "Adriana's Permanent Makeup at 117A Main Street, Salem NH. Microblading, nano brows, lip blush and eyeliner near Derry, Windham and Methuen.",
    "locations/wilmington-ma/index.html": "Adriana's Permanent Makeup at 211 Lowell Street Suite F, Wilmington MA. Brows, lips and eyeliner near Burlington, Woburn and North Reading.",
    "about/index.html": "Meet Adriana Souza Santos, Master PMU Artist with 20+ years and 5,000+ procedures, and the team behind the Adriana's studios in MA and NH.",
    "privacy-policy/index.html": "How Adriana's Permanent Makeup collects, uses and protects your personal information across our website and studios in MA and NH.",
    "terms-of-use/index.html": "Terms of use for the Adriana's Permanent Makeup website, including booking, deposits, cancellations and studio policies in MA and NH.",
}


def fix_descriptions(s, path_rel):
    desc = DESCRIPTIONS.get(path_rel)
    if not desc:
        return s
    return re.sub(r'<meta name="description" content="[^"]*"',
                  f'<meta name="description" content="{desc}"', s, count=1)


def fix_fresha(s, path_rel):
    """Pagina de cidade manda direto para o Fresha da unidade certa.
    Elimina a segunda escolha de unidade na jornada (feedback Rachel 16/08)."""
    if "/wilmington-ma/" in "/" + path_rel:
        return s.replace(FRESHA_GENERIC, FRESHA_W)
    if "/salem-nh/" in "/" + path_rel:
        return s.replace(FRESHA_GENERIC, FRESHA_S)
    return s



# --- Correcoes de E-E-A-T e cross-linking (auditoria itens 10 e 14) ---

# "over 7 years" e a marca antiga vieram do WordPress e contradizem os
# "20+ years" e "Adriana's PMU" do resto do site. Sinal conflitante de
# entidade para o Google e para LLMs.
TEXT_FIXES = [
    ("over 7 years of experience", "over 20 years of experience"),
    ("Adriana Beauty Services \u2013 Permanent Makeup", "Adriana's Permanent Makeup"),
]

BROW_SERVICES = [
    ("microblading", "Microblading", "Fios desenhados um a um" and "Hair-like strokes drawn one by one for natural fill"),
    ("nano-brows", "Nano Brows", "Machine-drawn nano strokes, great for most skin types"),
    ("nano-combo", "Nano Combo", "Nano strokes plus soft shading for extra density"),
    ("powder-brows", "Ombr\u00e9 Powder Brows", "Soft powdered finish, ideal for oily skin"),
    ("combination-brows", "Combination Brows", "Strokes at the front, shading through the body"),
]
EYELINER_SERVICES = [
    ("top-eyeliner", "Top Eyeliner", "Classic or winged definition on the upper lash line"),
    ("bottom-eyeliner", "Bottom Eyeliner", "Subtle lower lash line definition"),
    ("smokey-eyeliner", "Smokey Eyeliner", "Soft shaded effect that never smudges"),
    ("eyeliner-combo", "Eyeliner Combo", "Top and bottom in one appointment"),
]
LIP_SERVICES = [
    ("lip-blush", "Lip Blush", "Translucent color and defined contour"),
    ("dark-lip-neutralization", "Dark Lip Neutralization", "Evens tone before or with color work"),
]


def add_related(s, path_rel):
    """Bloco "Compare techniques" nas paginas de servico, linkando as irmas."""
    import re as _re
    m = _re.match(r"services/([a-z-]+)/([a-z0-9-]+)/index\.html$", path_rel)
    if not m or 'related-services' in s:
        return s
    cat, svc = m.group(1), m.group(2)
    groups = {"eyebrows": BROW_SERVICES, "eyeliner": EYELINER_SERVICES, "lips": LIP_SERVICES}
    group = groups.get(cat)
    if not group:
        return s
    siblings = [(slug, name, desc) for slug, name, desc in group if slug != svc]
    if not siblings:
        return s
    title = {"eyebrows": "Compare brow techniques", "eyeliner": "Other eyeliner styles", "lips": "Also for your lips"}[cat]
    cards = "".join(
        f'<article class="card"><h3><a href="../{slug}/">{name}</a></h3><p>{desc}</p></article>'
        for slug, name, desc in siblings
    )
    block = (f'<section class="section related-services"><div class="container">'
             f'<h2>{title}</h2><p>Not sure which technique fits you? '
             f'<a href="../../../contact/">Book a free consultation</a> and we will map it to your skin and routine. '
             f'You can also split any service with our <a href="../../../payment-plan/">payment plan</a>.</p>'
             f'<div class="card-grid">{cards}</div></div></section>')
    return s.replace("</main>", block + "\n</main>", 1)


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

    # 0. aggregateRating auto-declarado sai de TODAS as paginas.
    #    O Google ignora review snippet self-serving para LocalBusiness
    #    desde 2019, o numero conflitava com o "1,000+ reviews" da home,
    #    e markup de review auto-referente fora de pagina de review e
    #    risco de manual action de structured data spam (auditoria 12/08).
    for node in graph:
        if isinstance(node, dict):
            node.pop("aggregateRating", None)

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
                for a, b in TEXT_FIXES:
                    s = s.replace(a, b)
                s = add_related(s, rel)
                s = fix_descriptions(s, rel)
                s = fix_fresha(s, rel)
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
