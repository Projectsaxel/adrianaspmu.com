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
from urllib.parse import urljoin

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
    "locations/peabody-ma/index.html": "Adriana's Academy at 39 Cross Street, Peabody MA: AAM Diamond-certified PMU training. 100-Hour Fundamental, Apprenticeship, and VIP Masterclass courses.",
    "about/index.html": "Meet Adriana Souza Santos, Master PMU Artist with 18+ years and 5,000+ procedures, and the team behind the Adriana's studios in MA and NH.",
    "privacy-policy/index.html": "How Adriana's Permanent Makeup collects, uses and protects your personal information across our website and studios in MA and NH.",
    "terms-of-use/index.html": "Terms of use for the Adriana's Permanent Makeup website, including booking, deposits, cancellations and studio policies in MA and NH.",
}


# --- Camada de medicao (Fase 0 do plano de 12/08) -------------------
#
# Property GA4 "Adriana" (441132178), stream "adrianas pmu" (8152241977).
# Ate 17/08/2026 o site NAO tinha tag nenhuma: a property existia e
# estava vazia. Todo o trafego dos ultimos meses foi perdido.
#
# O gtag vai no build e nao no repo pelo mesmo motivo dos outros
# enriquecimentos: 63 paginas. E vai INLINE no head, nao via GTM,
# porque nao ha nenhum outro tag para gerenciar e o GTM custaria
# ~90KB de JS e um request extra antes do primeiro hit.
GA4_ID = "G-ZSD89WRHYZ"

CITY_LABEL = {"wilmington-ma": "wilmington", "salem-nh": "salem", "peabody-ma": "peabody"}


def classify(path_rel):
    """page_type, service e city de cada pagina, decididos no build.

    O evento sozinho ("clicou em agendar") nao responde nada. Com estes
    tres parametros ele responde: agendar O QUE, em QUAL cidade, vindo
    de QUAL tipo de pagina. E o que transforma o GA4 de contador de
    visita em ferramenta de decisao sobre onde investir conteudo.
    """
    p = path_rel[: -len("/index.html")] if path_rel.endswith("/index.html") else path_rel
    if path_rel == "index.html":
        return {"page_type": "home", "service": "", "city": ""}

    seg = p.split("/")

    if seg[0] == "services":
        if len(seg) == 1:
            return {"page_type": "service_hub", "service": "", "city": ""}
        if len(seg) == 2:
            return {"page_type": "service_category", "service": seg[1], "city": ""}
        if len(seg) == 3:
            return {"page_type": "service", "service": seg[2], "city": ""}
        return {"page_type": "service_city", "service": seg[2], "city": CITY_LABEL.get(seg[3], seg[3])}

    if seg[0] == "locations":
        if len(seg) == 1:
            return {"page_type": "locations_hub", "service": "", "city": ""}
        return {"page_type": "location", "service": "", "city": CITY_LABEL.get(seg[1], seg[1])}

    if seg[0] == "academy":
        if len(seg) == 1:
            return {"page_type": "academy_hub", "service": "", "city": ""}
        return {"page_type": "academy_course", "service": seg[1], "city": ""}

    simple = {
        "about": "about", "faq": "faq", "contact": "contact",
        "portfolio": "portfolio", "payment-plan": "payment",
        "privacy-policy": "legal", "terms-of-use": "legal",
    }
    return {"page_type": simple.get(seg[0], "other"), "service": "", "city": ""}


def add_analytics(s, path_rel):
    if GA4_ID in s:
        return s
    c = classify(path_rel)
    page_json = json.dumps(c, separators=(",", ":"))
    snippet = (
        f'<script>window.PMU_PAGE={page_json};</script>\n'
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>\n'
        "<script>window.dataLayer=window.dataLayer||[];"
        "function gtag(){dataLayer.push(arguments);}gtag('js',new Date());"
        # Os tres parametros da pagina viajam em TODO evento, inclusive
        # no page_view. Sem isso, so o evento de clique saberia o
        # contexto e nao daria para comparar visita com conversao.
        f"gtag('config','{GA4_ID}',{{page_type:'{c['page_type']}',"
        f"service:'{c['service'] or '(none)'}',city:'{c['city'] or '(none)'}'}});</script>\n"
        '<script src="/js/analytics.js" defer></script>\n'
    )
    return s.replace("</head>", snippet + "</head>", 1)


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

# "over 7 years" contava so os EUA (2017+). O numero correto e a carreira
# inteira, iniciada no Brasil: 18+ anos. Ver /about/.
TEXT_FIXES = [
    ("over 7 years of experience", "over 18 years of experience"),  # 18+ = carreira total (Brasil desde ~2008); EUA desde 2017
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


# --- Cherry: parcelamento em todo o site (08/09/2026) ---------------
#
# O pedido do cliente e do proprio Cherry: o parcelamento tem que
# aparecer em varios pontos, e o Cherry primeiro, antes de qualquer
# outro provedor. Fica aqui e nao no generate_pages.py porque sao
# ~55 paginas: aqui e uma regra, la seriam 55 edicoes.
#
# TRES EXCLUSOES DELIBERADAS, nao esquecer o motivo:
#
# 1. /payment-plan/ nao recebe o botao flutuante. Aquela pagina ja
#    carrega o widget FULL PAGE, e os dois snippets chamam _hw("init")
#    no mesmo escopo. Dois init na mesma pagina = comportamento
#    indefinido do widget.
#
# 2. /academy/* e /training/ nao recebem NADA do Cherry. O Cherry
#    cobre servicos, NAO cobre mensalidade de curso (confirmado com o
#    cliente em 08/09/2026). Anunciar Cherry ao lado de um curso de
#    $7.000 e prometer o que o Cherry pode recusar, com risco de
#    retencao de repasse. Essas paginas recebem o texto do
#    financiamento PROPRIO da casa.
#
# 3. /privacy-policy/ e /terms-of-use/ ficam de fora: nao ha intencao
#    comercial ali e o botao flutuante seria so ruido.
#
# NUMEROS: sao os da conta real, conferidos no portal. Pay in 4 ativo
# ($35 a $3.000, sem juros), teto $30.000, prazo maximo 24 meses, 0%
# APR mensal so em 1-3 meses. NAO escrever "12x sem juros" em lugar
# nenhum: o APR promocional de 6 a 24 meses esta desligado por decisao
# do cliente, que preferiu nao pagar a taxa da loja.

CHERRY_APPLY = "https://pay.withcherry.com/adrianas-beauty-services-inc"

# Snippet FLOATING BUTTON gerado em provider.withcherry.com, literal,
# menos o <link> de 11 familias do Google Fonts que o gerador emite.
# Aquele <link> e render-blocking e existiria so para o widget usar
# Montserrat; forcamos Inter (a fonte do site) via CSS .cherry-widget.
CHERRY_FLOATING = """
<div class="cherry-widget cherry-widget--floating">
<!-- CHERRY WIDGET BEGIN -->
<script>
    (function (w, d, s, o, f, js, fjs) {
        w[o] = w[o] || function () {
            (w[o].q = w[o].q || []).push(arguments);
        };
        (js = d.createElement(s)), (fjs = d.getElementsByTagName(s)[0]);
        js.id = o;
        js.src = f;
        js.async = 1;
        fjs.parentNode.insertBefore(js, fjs);
    })(window, document, "script", "_hw", "https://files.withcherry.com/widgets/widget.js");
    _hw("init", {
        debug: false,
        variables: {
            slug: "adrianas-beauty-services-inc",
            name: "Adrianas Beauty Services INC",
            images: [26],
            customLogo: "",
            defaultPurchaseAmount: 650,
            customImage: "",
            imageCategory: "medspa",
            language: "en",
        },
        styles: {
            primaryColor: "#c2286c",
            secondaryColor: "#c2286c10",
            fontFamily: "Montserrat",
            headerFontFamily: "Montserrat",
            floatingEstimator: {
                position: "bottom-left",
                offset: {
                    x: "0px",
                    y: "0px"
                },
                zIndex: 9999,
                ctaFontFamily: "Montserrat",
                bodyFontFamily: "Montserrat",
                ctaColor: "#c2286c",
                ctaTextColor: "#FFFFFF"
            }
        }
    }, ["floatingEstimator"]);
</script>
<div id="floatingEstimator"></div>
<!-- CHERRY WIDGET END -->
</div>
"""

# "locations/peabody-ma/" e a pagina do ACADEMY, nao de um estudio: mesma
# regra do item 2 acima (Cherry nao cobre mensalidade de curso). Sem esta
# entrada, add_financing e add_cherry_floating tratariam Peabody como
# "locations/" generico e anunciariam Cherry ao lado de tuition de $7.000.
NO_CHERRY = ("payment-plan/", "academy/", "training/", "privacy-policy/", "terms-of-use/", "locations/peabody-ma/")
IS_ACADEMY = ("academy/", "training/", "locations/peabody-ma/")


def _base(path_rel):
    """Prefixo relativo para a raiz, a partir do caminho da pagina."""
    depth = path_rel.count("/")
    return "../" * depth if depth else "./"


def finance_line(base):
    return (
        f'<p class="finance-line">or <strong>4 interest-free payments</strong> with Cherry &mdash; '
        f'<a href="{base}payment-plan/">see your options</a>, no impact on your credit score</p>'
    )


def academy_line(base):
    return (
        f'<p class="finance-line">an <strong>in-house payment plan</strong> is available for this '
        f'course &mdash; <a href="{base}payment-plan/#academy-plan">how it works</a></p>'
    )


def finance_banner(base):
    return f"""
<section class="section finance-banner">
  <div class="container finance-banner-inner">
    <div>
      <h2>Pay over time, starting today</h2>
      <p>Split any service into <strong>4 interest-free payments</strong> with Cherry, or over up
      to 24 months with interest. Checking your options takes about a minute and uses a soft credit
      check, so it does <strong>not</strong> affect your credit score.</p>
      <p class="pricing-note">Approval and rates subject to eligibility. Cherry is a financial
      technology company, not a bank or a lender.</p>
    </div>
    <div class="finance-banner-cta">
      <a class="btn btn-primary" href="{base}payment-plan/">See payment plans</a>
      <a class="btn btn-ghost" href="{CHERRY_APPLY}" target="_blank" rel="noopener noreferrer">Apply with Cherry</a>
    </div>
  </div>
</section>
"""


def academy_banner(base):
    return f"""
<section class="section finance-banner">
  <div class="container finance-banner-inner">
    <div>
      <h2>Training payment plans</h2>
      <p>Our courses are not financed through Cherry, which covers our permanent makeup services.
      For training we offer an <strong>in-house payment plan</strong>: place a deposit and pay the
      balance directly with us.</p>
    </div>
    <div class="finance-banner-cta">
      <a class="btn btn-primary" href="{base}payment-plan/#academy-plan">How it works</a>
      <a class="btn btn-ghost" href="{base}contact/">Talk to us</a>
    </div>
  </div>
</section>
"""


# --- Bloco de licenca por unidade (documentos verificados 11/09/2026) ---
# Os numeros sao identicos em todas as paginas da mesma cidade. Injetar no
# build evita escrever o mesmo bloco 13 vezes por unidade e garante que a
# renovacao seja feita num lugar so. Fonte: pasta Doc Adrianas pmu.
LICENCA_WILM = """<section class="section section-alt"><div class="container">
<h2>Which Licenses Cover This Work in Wilmington?</h2>
<p class="direct-answer">Massachusetts has no single state body art license. Wilmington&rsquo;s own Board of Health issues both licenses that cover this work: Body Art Facility License 20261921 for the studio at 211 Lowell Street, and Body Art Practitioner License 20261923 for the artist. Both run through 31 December 2026.</p>
<div class="table-scroll" tabindex="0" role="region" aria-label="Wilmington licenses"><table>
<thead><tr><th>License</th><th>Number</th><th>Issued by</th><th>Valid through</th></tr></thead>
<tbody>
<tr><td>Body Art Facility</td><td>20261921</td><td>Wilmington Board of Health</td><td>31 Dec 2026</td></tr>
<tr><td>Body Art Practitioner &mdash; Adriana Santos</td><td>20261923</td><td>Wilmington Board of Health</td><td>31 Dec 2026</td></tr>
<tr><td>Body Art Practitioner &mdash; Livian Camargo Gomes</td><td>20261923</td><td>Wilmington Board of Health</td><td>31 Dec 2026</td></tr>
</tbody></table></div>
<p>Under Massachusetts General Laws Chapter 111, Section 31, each town&rsquo;s Board of Health writes its own body art rules, so a permit issued in Wilmington does not carry over to another Massachusetts town. Both licenses are posted in the studio, as Wilmington requires.</p>
</div></section>"""

LICENCA_SALEM = """<section class="section section-alt"><div class="container">
<h2>Which Licenses Cover This Work in Salem, NH?</h2>
<p class="direct-answer">Two levels apply in New Hampshire. The state issues Body Artist license 4283 to Adriana Souza Santos, valid through 18 July 2028 and verifiable at the state&rsquo;s own public lookup. The Town of Salem separately licenses the artist as a Permanent Make-Up Artist under BODA-10 and the establishment under BODE-4.</p>
<div class="table-scroll" tabindex="0" role="region" aria-label="Salem NH licenses"><table>
<thead><tr><th>License</th><th>Classification</th><th>Number</th><th>Valid through</th></tr></thead>
<tbody>
<tr><td>New Hampshire OPLC</td><td>Body Artist</td><td>4283</td><td>18 Jul 2028</td></tr>
<tr><td>Town of Salem</td><td>Permanent Make-Up Artist</td><td>BODA-10</td><td>28 Feb 2027</td></tr>
<tr><td>Town of Salem</td><td>Body Art Establishment</td><td>BODE-4</td><td>28 Feb 2027</td></tr>
</tbody></table></div>
<p><strong>Check the state license yourself.</strong> New Hampshire publishes a lookup at <a href="https://forms.nh.gov/licenseverification/" rel="noopener" target="_blank">forms.nh.gov/licenseverification</a>. Search Adriana Souza Santos, or license 4283, and the state confirms the status without relying on anything published here.</p>
<p>The town license is worth noting: Salem issued BODA-10 specifically as a <strong>Permanent Make-Up Artist</strong> license under Salem Chapter 433, not as a general tattoo license.</p>
</div></section>"""


# --- alt e title das imagens (auditoria 12/09) ----------------------
# 165 tags <img> no <main> estavam sem "title" e 2 sem "alt". Fazer isso
# no build, e nao arquivo a arquivo, porque a mesma foto aparece em ate
# 4 paginas e o texto precisa ser o mesmo em todas.
#
# Regra: o "title" COMPLEMENTA o alt, nunca o repete. O alt descreve o que
# a imagem mostra, para quem nao a ve; o title diz o que ela prova ou por
# que ela esta ali. Repetir o alt no title e ruido para leitor de tela.
IMG_TEXT = {
    # servicos: o alt e o nome da tecnica, o title diz o resultado
    "nano-brows.jpg": (None, "Nano Brows: hair-like strokes made with an ultra-fine machine needle"),
    "microblading.jpg": (None, "Microblading: hair-like strokes made with a handheld blade"),
    "powder-brows.jpg": (None, "Powder Brows: soft shaded finish, like brows filled with powder"),
    "combination-brows.jpg": (None, "Combination Brows: hair-like strokes blended with soft shading"),
    "nano-combo.jpg": (None, "Nano Combo Brows: nano strokes layered with powder shading"),
    "lip-blush.jpg": (None, "Lip Blush: a soft tint that enhances natural lip colour and shape"),
    "dark-lip-neutralization.jpg": (None, "Dark Lip Neutralization: colour correction that evens out deeper lip tones"),
    "top-eyeliner.jpg": (None, "Top Eyeliner: definition along the upper lash line"),
    "smokey-eyeliner.jpg": (None, "Smokey Eyeliner: upper liner blended upward into soft shading"),
    "bottom-eyeliner.jpg": (None, "Bottom Eyeliner: fine definition along the lower lash line"),
    "eyeliner-combo.jpg": (None, "Eyeliner Combo: upper and lower lash lines in one session"),
    "eyebrows-lips-combo.jpg": (None, "Brows + Lips Combo: both treatments in one healing period"),
    "yearly-touch-up.jpg": (None, "Yearly Touch-Up: refreshing faded pigment about twelve months on"),
    # academia e credenciais
    "aam-seal.png": (None, "Diamond Certified Trainer status with the American Academy of Micropigmentation"),
    "adriana.jpg": (None, "Adriana Souza Santos, who teaches every class at the Peabody academy"),
    "apprenticeship.jpg": (None, "The apprenticeship year: supervised practice on live models"),
    "pmu-100h.jpg": (None, "The 100 Hours Fundamental Class, accredited by the AAM"),
    "classroom.jpg": (None, "The academy classroom at 39 Cross Street, Peabody"),
    "in-person-class.jpg": (None, "Small-group teaching, with the instructor correcting work in the room"),
    # o hero da academia nao tinha alt nenhum
    "hero.webp": ("Adriana teaching a permanent makeup class at Adriana's Academy in Peabody, MA",
                  "A class in progress at the Peabody academy"),
}

def _img_text(src, alt):
    """Devolve (alt, title) para uma imagem, por nome de arquivo ou familia."""
    name = src.split("/")[-1]
    if name in IMG_TEXT:
        a, t = IMG_TEXT[name]
        return (a or alt), t
    if name.startswith("Portfolio-"):
        # alt ja descreve o caso; o title diz o que a foto e
        return alt, "Before and after on a real client at Adriana's Permanent Makeup"
    if name.startswith("academy-"):
        return alt, "Students at work during a class at Adriana's Academy"
    if name.startswith("slide-"):
        return alt, "Course material from the 100 Hours Fundamental Class"
    if name.startswith(("student-", "Avatar-Aluna")):
        return alt, "One of the 300+ artists trained at Adriana's Academy"
    return alt, None


def add_img_text(s, path_rel):
    """Preenche alt e title faltantes nas <img> dentro do <main>."""
    m = re.search(r"<main.*?</main>", s, re.S)
    if not m:
        return s
    main = m.group(0)

    def fix(mt):
        tag = mt.group(0)
        src = re.search(r'src="([^"]*)"', tag)
        if not src:
            return tag
        cur_alt = re.search(r'alt="([^"]*)"', tag)
        alt_val = cur_alt.group(1) if cur_alt else ""
        new_alt, title = _img_text(src.group(1), alt_val)
        if new_alt and new_alt != alt_val:
            tag = (re.sub(r'alt="[^"]*"', 'alt="%s"' % new_alt, tag) if cur_alt
                   else tag[:-1] + ' alt="%s">' % new_alt)
        if title and not re.search(r'\btitle="[^"]+"', tag):
            tag = tag[:-1] + ' title="%s">' % title
        return tag

    new_main = re.sub(r"<img\b[^>]*>", fix, main)
    return s.replace(main, new_main) if new_main != main else s


# --- Organization completa (Is Agentic itens 5 e 6) -----------------
# O scan apontou: "Organization schema found but missing: contactPoint,
# address" e "JSON-LD has Organization type but missing key fields (name,
# description)". Sem esses campos a IA nao consegue verificar a empresa
# nem responder pergunta de contato. Preenchido no build, para valer nas
# 65 paginas de uma vez.
ORG_EXTRA = {
    "description": (
        "Permanent makeup studio and training academy serving Wilmington, Massachusetts "
        "and Salem, New Hampshire. Nano brows, microblading, powder brows, lip blush, "
        "dark lip neutralization and permanent eyeliner, performed by licensed artists. "
        "Consultations in English and Portuguese."
    ),
    "telephone": "+1-781-853-8063",
    "email": None,  # a empresa nao tem caixa generica monitorada; nao inventar
    "logo": {
        "@type": "ImageObject",
        "url": BASE + "/assets/images/logo.svg",
    },
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "211 Lowell Street, Suite F",
        "addressLocality": "Wilmington",
        "addressRegion": "MA",
        "postalCode": "01887",
        "addressCountry": "US",
    },
    "contactPoint": [
        {
            "@type": "ContactPoint",
            "contactType": "customer service",
            "telephone": "+1-781-853-8063",
            "areaServed": "US-MA",
            "availableLanguage": ["English", "Portuguese"],
        },
        {
            "@type": "ContactPoint",
            "contactType": "customer service",
            "telephone": "+1-978-223-7496",
            "areaServed": "US-NH",
            "availableLanguage": ["English", "Portuguese"],
        },
    ],
    "areaServed": [
        {"@type": "State", "name": "Massachusetts"},
        {"@type": "State", "name": "New Hampshire"},
    ],
    "knowsLanguage": ["en-US", "pt-BR"],
}


def complete_organization(graph):
    """Preenche os campos que faltavam no no Organization."""
    for node in graph:
        if not isinstance(node, dict):
            continue
        if node.get("@type") == "Organization":
            for k, v in ORG_EXTRA.items():
                if v is not None and k not in node:
                    node[k] = v
    return graph


def add_licenca(s, path_rel):
    """Injeta o bloco de licenca nas paginas servico-cidade, antes da secao
    final de CTA. Idempotente: nao reinjeta se a marca ja existe."""
    if "id=\"licencas\"" in s or "Which Licenses Cover This Work" in s:
        return s
    if path_rel.endswith("/wilmington-ma/index.html"):
        bloco = LICENCA_WILM
    elif path_rel.endswith("/salem-nh/index.html"):
        bloco = LICENCA_SALEM
    else:
        return s
    if not path_rel.startswith("services/"):
        return s
    # ancora: a secao de CTA final, qualquer que seja a combinacao de
    # modificadores; se nao houver CTA (pagina ainda esqueleto), entra
    # antes do fechamento do <main>.
    m = re.search(r'<section class="section[^"]*section--cta"', s)
    if m:
        return s[:m.start()] + bloco + "\n" + s[m.start():]
    m = re.search(r'</main>', s)
    if not m:
        return s
    return s[:m.start()] + bloco + "\n  " + s[m.start():]


def add_aftercare_link(s, path_rel):
    """Linka /aftercare/ a partir da secao 'Healing and Aftercare' das
    paginas de servico (auditoria 10/09: a pagina de aftercare estava
    orfa, zero links de entrada). Roda no build, nao a mao em cada
    pagina de servico: sao 12+ arquivos e crescem a cada servico novo.
    """
    if path_rel == "aftercare/index.html":
        return s
    marker_h2 = "<h2>Healing and Aftercare</h2>"
    if marker_h2 not in s:
        return s
    base = _base(path_rel)
    href = f"{base}aftercare/"
    if f'href="{href}"' in s:
        return s                                    # idempotente
    line = (f'<p class="aftercare-link">Read the full <a href="{href}">'
            f'aftercare and healing guide</a> for the day-by-day timeline '
            f'and the signs that need a doctor instead of the studio.</p>')
    return s.replace(marker_h2, marker_h2 + "\n    " + line, 1)


def add_financing(s, path_rel):
    """Linha sob o preco e banner de parcelamento nas paginas comerciais."""
    if path_rel.startswith(("payment-plan/", "privacy-policy/", "terms-of-use/")):
        return s
    if "finance-banner" in s or "finance-line" in s:
        return s                                    # idempotente
    base = _base(path_rel)
    academy = path_rel.startswith(IS_ACADEMY)
    line = academy_line(base) if academy else finance_line(base)
    banner = academy_banner(base) if academy else finance_banner(base)

    # 1) linha logo abaixo do preco, onde a objecao de preco nasce
    if 'class="pricing-badge"' in s:
        i = s.index('class="pricing-badge"')
        j = s.index("</p>", i) + len("</p>")
        s = s[:j] + line + s[j:]

    # 2) banner antes do CTA final; se a pagina nao tem CTA final,
    #    no fim do <main>. Paginas sem intencao comercial ficam fora.
    anchor = '<section class="section section--cta"'
    if anchor in s:
        s = s.replace(anchor, banner + anchor, 1)
    elif path_rel.startswith(("services/", "locations/")):
        s = s.replace("</main>", banner + "\n</main>", 1)
    return s


def add_cherry_floating(s, path_rel):
    """Botao flutuante do Cherry (estimador de parcelas) antes de </body>."""
    if path_rel.startswith(NO_CHERRY) or path_rel == "404.html":
        return s
    if "floatingEstimator" in s:
        return s                                    # idempotente
    return s.replace("</body>", CHERRY_FLOATING + "</body>", 1)


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
        graph = complete_organization(graph)

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
            # resolve relativo (ou o proprio canonical, se for o crumb atual,
            # sem <a>) via RFC 3986 de verdade: urljoin trata corretamente
            # "../" e "../../" contra um canonical terminado em "/". A conta
            # manual anterior (contar "../" e fatiar o canonical) colapsava
            # QUALQUER href so-de-"../" para BASE+"/", perdendo os crumbs
            # intermediarios (ex.: "Locations" virava a home). Bug pego na
            # pagina de Peabody, 10/09/2026.
            target = urljoin(canonical, href) if href else canonical
            if "#" not in target and "?" not in target and not target.endswith("/"):
                target += "/"
            item["item"] = target
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
                s = add_aftercare_link(s, rel)
                s = add_licenca(s, rel)
                s = add_img_text(s, rel)
                s = add_financing(s, rel)
                s = fix_descriptions(s, rel)
                s = fix_fresha(s, rel)
                s = add_og(s, dirpath)
                s = enrich_schema(s, rel)
                s = fix_lcp(s, rel)
            # A 404 tambem leva tag: pagina de erro sem medicao e a
            # forma mais comum de um link quebrado sobreviver meses.
            s = add_analytics(s, rel)
            s = fix_dimensions(s, dirpath)
            s = add_cherry_floating(s, rel)
            if s != orig:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(s)
                changed += 1
    print(f"enrich_pages: {changed} paginas enriquecidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
