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
    "services/eyebrows/index.html": "Microblading, nano brows, powder and combination brows in Wilmington MA and Salem NH. Compare techniques, see prices, and book a consultation.",
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
    "about/index.html": "Meet Adriana Souza Santos, Master PMU Artist with 20+ years and 5,000+ procedures, and the team behind the Adriana's studios in MA and NH.",
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


# Formas do link generico que aparecem no HTML. Comparar so com "&" era o
# bug de 25/09/2026: o HTML traz "&amp;", a troca nunca acontecia e o
# "Book Now in Wilmington" abria o seletor das duas unidades. O Book Now
# do header usa ainda uma terceira forma, sem share=true.
_FRESHA_GENERIC_FORMS = (
    FRESHA_GENERIC,
    FRESHA_GENERIC.replace("&", "&amp;"),
    "https://www.fresha.com/book-now/adrianas-permanent-makeup-zeaseit5/all-offer?pId=727586",
)

PHONE_W = "tel:+17818538063"
PHONE_S = "tel:+19782237496"


def fix_fresha(s, path_rel):
    """Pagina de cidade manda direto para o Fresha da unidade certa.
    Elimina a segunda escolha de unidade na jornada (feedback Rachel 16/08).

    Pagina de Salem tambem troca o Call do header no HTML estatico: antes so
    o main.js trocava, e crawler (sem JS) e o gemeo markdown viam o telefone
    de Wilmington."""
    p = "/" + path_rel
    if "/wilmington-ma/" in p:
        dest = FRESHA_W.replace("&", "&amp;")
    elif "/salem-nh/" in p:
        dest = FRESHA_S.replace("&", "&amp;")
        s = s.replace(f'header-call" href="{PHONE_W}"', f'header-call" href="{PHONE_S}"')
        s = s.replace('href="tel:9782237496"', f'href="{PHONE_S}"')
    else:
        return s
    for g in _FRESHA_GENERIC_FORMS:
        s = s.replace(f'href="{g}"', f'href="{dest}"')
    return s



# --- Correcoes de E-E-A-T e cross-linking (auditoria itens 10 e 14) ---

# "over 7 years" contava so os EUA (2017+). O numero correto e a carreira
# inteira, iniciada no Brasil: 18+ anos. Ver /about/.
TEXT_FIXES = [
    # A bio que a propria Adriana enviou (21/09/2026) diz que ela descobriu
    # permanent makeup em 2006, o que da 20 anos em 2026. O "~2008" que estava
    # escrito aqui era estimativa, e 2017 e a ABERTURA nos EUA, nao o inicio da
    # carreira. Subestimar experiencia enfraquece E-E-A-T sem ganho nenhum.
    ("over 7 years of experience", "over 20 years of experience"),
    ("over 18 years of experience", "over 20 years of experience"),
    ("18-plus year career", "20-plus year career"),
    ("18-plus years", "20-plus years"),
    ("18+ year", "20+ year"),
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
    // Adiado de proposito (auditoria 25/09/2026): o widget.js da Cherry tem
    // ~434 KB e ainda carrega o Segment. Entrava junto com a pagina e
    // disputava banda com o hero. Agora sobe na primeira interacao ou 4s
    // depois do load. A fila _hw("init", ...) abaixo segue valendo.
    (function (w, d, s, o, f) {
        w[o] = w[o] || function () {
            (w[o].q = w[o].q || []).push(arguments);
        };
        var done = false;
        function go() {
            if (done) return;
            done = true;
            var js = d.createElement(s), fjs = d.getElementsByTagName(s)[0];
            js.id = o;
            js.src = f;
            js.async = 1;
            fjs.parentNode.insertBefore(js, fjs);
        }
        ["pointerdown", "scroll", "keydown", "touchstart"].forEach(function (e) {
            w.addEventListener(e, go, { once: true, passive: true });
        });
        w.addEventListener("load", function () { setTimeout(go, 4000); });
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
<tr><td>Body Art Practitioner &mdash; Livian Camargo Gomes</td><td>20261924</td><td>Wilmington Board of Health</td><td>31 Dec 2026</td></tr>
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



# --- B08: foto de RESULTADO nas paginas servico-cidade (22/09/2026) ------
# As 26 paginas servico-cidade tinham UMA foto so, e era a mesma em todas:
# a sala de Salem nas 13 de Salem, a recepcao de Wilmington nas 13 de
# Wilmington. Zero foto de trabalho. B08 (prova) e OBR na tipologia local.
#
# Cada foto sai da pasta do PROPRIO servico em "Adrianas Project", conferida
# no olho: nada de montagem antes/depois, nada de luva em cena, nada de foto
# do antes. Ver a memoria adrianaspmu-selecao-de-fotos.
#
# A legenda NAO diz em qual unidade nem em que mes o trabalho foi feito,
# porque o arquivo nao carrega essa informacao e o EXIF mente. Enquanto a
# Adriana nao informar unidade + mes por foto, B08 fica PARCIAL de proposito:
# inventar a cidade seria pior do que nao ter a foto.
PROOF = {
 "microblading": {
  "salem-nh": ("Healed microblading brow seen in profile, individual hair strokes following the natural brow direction",
    "Microblading healed: individual strokes, not a solid block of colour.",
    "The strokes are cut one at a time with a handheld blade, which is why the brow keeps a broken edge instead of a printed outline. This is the result after the perfecting session."),
  "wilmington-ma": ("Healed microblading brow in profile with a defined tail and a softer, lighter front",
    "Microblading healed: denser at the tail, deliberately lighter at the front.",
    "The front of the brow is left lighter on purpose so the shape reads as hair rather than as makeup. The density builds toward the arch and tail."), },
 "nano-brows": {
  "salem-nh": ("Healed nano brows on a client facing the camera, fine machine-made strokes with a soft arch",
    "Nano brows healed: fine machine strokes, soft arch.",
    "Nano uses a single ultra-fine needle on a digital machine, so each stroke is thinner than a blade stroke and sits more evenly on mature or oily skin."),
  "wilmington-ma": ("Healed nano brows framing the eyes, with a fuller body and a clean but unpainted edge",
    "Nano brows healed: fuller body, edge still unpainted.",
    "The outline is never drawn as a hard line. Strokes are layered until the brow reads full, and the border stays broken so it holds up close."), },
 "nano-combo": {
  "salem-nh": ("Healed nano combo brows with hair strokes at the front blending into soft shading toward the tail",
    "Nano combo healed: strokes at the front, shading behind them.",
    "The combination is not half and half. Strokes carry the front, where the eye looks first, and the shading picks up behind them to give depth without a drawn edge."),
  "wilmington-ma": ("Healed nano combo brows seen straight on, with visible strokes over a light shaded base",
    "Nano combo healed: strokes sitting over a light shaded base.",
    "The shading is kept light enough that the strokes stay legible through it. Pushed darker, the two techniques collapse into one flat brow."), },
 "powder-brows": {
  "salem-nh": ("Healed powder brows with a soft shaded fill and a defined tail, no visible hair strokes",
    "Powder brows healed: shaded fill, no strokes.",
    "There are no hair strokes in this technique at all. The pigment is built in fine dots, densest at the tail and faded toward the front, which is what gives the makeup-like finish."),
  "wilmington-ma": ("Healed powder brows with a softly graded fill that is lightest at the inner corner",
    "Powder brows healed: lightest at the inner corner.",
    "The gradient runs front to tail. Keeping the inner corner light is what stops a shaded brow from reading as a block."), },
 "eyeliner-combo": {
  "salem-nh": ("Healed eyeliner combo on a closed eye, pigment along both the upper and the lower lash line",
    "Eyeliner combo healed: both lash lines treated in one session.",
    "The upper line carries the thickness and the lower stays deliberately thinner. Matching them would close the eye up rather than open it."),
  "wilmington-ma": ("Healed eyeliner combo seen close, upper line thicker toward the outer corner and a fine lower line",
    "Eyeliner combo healed: thickness added only toward the outer corner.",
    "Thickness is added toward the outer third, never evenly along the lid, because an even line shortens the eye."), },
 "lip-blush": {
  "salem-nh": ("Healed lip blush in a deep rose tone with a defined border and even colour across both lips",
    "Lip blush healed: deep rose, border defined without a drawn line.",
    "The border is defined by where the colour stops, not by an outline drawn around the lip. Saturation like this is built over two sessions."),
  "wilmington-ma": ("Healed lip blush in a bright warm tone with visible natural lip texture through the colour",
    "Lip blush healed: warm tone, natural texture still visible.",
    "The lip texture reads through the pigment, which is the point. Lip blush tints the lip; it does not coat it the way lipstick does."), },
 "dark-lip-neutralization": {
  "salem-nh": ("Lips after dark lip neutralization, showing an even warm pink tone with no grey cast",
    "After neutralization: the grey cast is gone and the tone reads even.",
    "Neutralizing works in layers. A correcting tone is laid first to cancel the cool pigment, and only then is the final colour built on top."),
  "wilmington-ma": ("Lips after dark lip neutralization, showing an even warm pink tone with no grey cast",
    "After neutralization: the grey cast is gone and the tone reads even.",
    "Neutralizing works in layers. A correcting tone is laid first to cancel the cool pigment, and only then is the final colour built on top."), },
 "eyebrows-lips-combo": {
  "salem-nh": ("Healed brows and lips done together, the brow shape and the lip tone balanced against each other",
    "Brows and lips healed together, balanced as one result.",
    "Doing both in one package is what lets the two be balanced against each other. A strong brow with a pale lip, or the reverse, is the usual result of booking them months apart."),
  "wilmington-ma": ("Healed brows and lips done together, the brow shape and the lip tone balanced against each other",
    "Brows and lips healed together, balanced as one result.",
    "Doing both in one package is what lets the two be balanced against each other. A strong brow with a pale lip, or the reverse, is the usual result of booking them months apart."), },
}


def add_proof(s, path_rel):
    """Injeta a foto de resultado antes do bloco de licencas. Idempotente."""
    # ATENCAO: o markup gerado e class="section proof-result". Procurar por
    # 'class="proof-result"' com a aspa antes de proof NUNCA casa, e cada
    # rodada do build empilha outra copia do bloco (erro de 22/09/2026, 3
    # copias por pagina). Mesma armadilha do breadcrumb: usar o nome da
    # classe sozinho, sem ancorar na aspa de abertura.
    if "proof-result" in s:
        return s
    m = re.match(r"services/[^/]+/([^/]+)/(salem-nh|wilmington-ma)/index\.html$", path_rel)
    if not m:
        return s
    slug, city = m.group(1), m.group(2)
    if slug not in PROOF:
        return s                                   # servico sem foto propria
    alt, cap, para = PROOF[slug][city]
    base = _base(path_rel)
    # ATENCAO: _h1_of() recebe URL, nao HTML. Aqui o <h1> sai do proprio
    # arquivo; passar 's' faz a funcao devolver None e cair no slug, o que
    # transformou "Brows + Lips Combo" em "Eyebrows Lips Combo" (22/09/2026).
    mh = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    h1 = re.sub(r"<[^>]+>", "", mh.group(1)).strip() if mh else slug.replace("-", " ").title()
    name = re.sub(r"\s+in\s+(Salem,\s*NH|Wilmington,\s*MA)\s*$", "", h1).strip()
    bloco = (
      '<section class="section proof-result"><div class="container">\n'
      f'<h2>What {name} {"Look Like Once They Have" if name.endswith("s") else "Looks Like Once It Has"} Healed</h2>\n'
      '<figure>'
      f'<img src="{base}assets/images/proof/{slug}-{city}.jpg" alt="{alt}" '
      f'title="{cap}" width="1080" height="1350" loading="lazy" decoding="async">'
      f'<figcaption>{cap}</figcaption></figure>\n'
      f'<p>{para}</p>\n'
      '</div></section>')
    anchor = "Which Licenses Cover This Work"
    i = s.find('<section class="section section-alt"><div class="container">\n<h2>' + anchor)
    if i == -1:
        i2 = s.find(anchor)
        i = s.rfind("<section", 0, i2) if i2 != -1 else -1
    if i == -1:
        mm = re.search(r'<section class="section[^"]*section--cta"', s)
        i = mm.start() if mm else s.find("</main>")
    if i == -1:
        return s
    return s[:i] + bloco + "\n" + s[i:]

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



# ====================================================================
# FASE 1 da auditoria de 21/09/2026 (skills semantic-site-architect e
# site-creator-framework atualizadas em 21/09).
#
# O que esta secao resolve, e por que no build e nao no repo:
# os quatro itens abaixo valem para TODAS as paginas. Escrever a mao
# em 63 arquivos e o que produziu a inconsistencia que a auditoria
# encontrou (as 26 paginas de cidade tinham byline; as 13 master, os
# 6 hubs, a home e a about nao tinham).
#
#   1. WebSite no grafo          — nao existia em NENHUMA pagina do site
#   2. CollectionPage + ItemList — nao existia NENHUM ItemList no site
#   4. Byline B11 + dateModified — 33 paginas sem autor, 59 sem dateModified
#   6. Link contextual p/ /about/ — a pagina que sustenta a entidade nao
#      recebia um unico link de corpo
#
# Os itens 4 e 6 sao resolvidos pelo MESMO bloco: a byline assina a
# pagina e, ao assinar, linka para a pagina da autora com ancora
# descritiva (regra 2 do internal-linking-engineering: proibido
# "saiba mais"; a ancora carrega a entidade do destino).
# ====================================================================

REVIEW_DATE_HUMAN = "September 21, 2026"
REVIEW_DATE_ISO = "2026-09-21"

# Nao tem SearchAction de proposito: o site nao tem busca interna.
# Declarar potentialAction sem a rota correspondente e schema que mente
# (schema-integrity-rules.md: "o JSON-LD so afirma o que existe").
WEBSITE_NODE = {
    "@type": "WebSite",
    "@id": f"{BASE}/#website",
    "url": BASE + "/",
    "name": "Adriana's Permanent Makeup",
    "alternateName": "Adriana's PMU",
    "description": (
        "Permanent makeup studio and training academy in Wilmington, Massachusetts "
        "and Salem, New Hampshire."
    ),
    "inLanguage": "en-US",
    "publisher": {"@id": f"{BASE}/#organization"},
}

PERSON_ID = f"{BASE}/about/#adriana"

PERSON_NODE = {
    "@type": "Person",
    "@id": PERSON_ID,
    "name": "Adriana Souza Santos",
    "jobTitle": "Master Permanent Makeup Artist",
    "worksFor": {"@id": f"{BASE}/#organization"},
    "url": f"{BASE}/about/",
    # Retrato individual. Antes apontava para about-adriana.jpg, que e uma
    # foto de GRUPO de quatro pessoas num evento (com TV de outra marca ao
    # fundo): o Person nomeava uma pessoa e mostrava quatro. Trocado em
    # 21/09/2026 pela foto de estudio da sessao Meet the Team.
    "image": f"{BASE}/assets/images/adriana-souza-santos.jpg",
    "knowsLanguage": ["en-US", "pt-BR"],
    "hasCredential": {
        "@type": "EducationalOccupationalCredential",
        "credentialCategory": "Professional certification",
        "name": "AAM Diamond Certified Trainer",
        "recognizedBy": {
            "@type": "Organization",
            "name": "American Academy of Micropigmentation",
        },
    },
}

# Paginas que NAO levam byline de autoria.
#   legais  -> carregam data de vigencia, nao autor (legal-pages-planning.md)
#   contact -> tipologia transactional na versao leve (B01/B15/B16/B17)
#   404     -> nao e pagina de conteudo
NO_BYLINE = {
    "privacy-policy/index.html",
    "terms-of-use/index.html",
    "contact/index.html",
    "404.html",
    "training/index.html",
}


def _up(path_rel):
    """Prefixo relativo da raiz a partir de uma pagina ("../../")."""
    depth = path_rel.count("/")
    return "../" * depth if depth else "./"


def _sitemap_lastmod():
    """lastmod declarado no sitemap, por caminho. E a data curada do site."""
    out = {}
    fp = os.path.join(ROOT, "sitemap.xml")
    if not os.path.exists(fp):
        return out
    with open(fp, encoding="utf-8") as f:
        sm = f.read()
    for loc, mod in re.findall(r"<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", sm):
        out[loc.replace(BASE, "").strip()] = mod.strip()
    return out


LASTMOD = _sitemap_lastmod()




# Equipe da /about/ (bios fornecidas pela cliente em 21/09/2026).
# So entra o que a bio ou a tabela de licencas da propria pagina afirma.
# Sofia Laura nao declara funcao na bio e nao consta como artista
# licenciada: por isso vai SEM jobTitle e SEM knowsAbout. Regra 1.
TEAM_NODES = [
    {
        "@type": "Person",
        "@id": f"{BASE}/about/#livian-gomes",
        "name": "Livian Gomes",
        "alternateName": "Livian Camargo Gomes",
        "jobTitle": "Permanent Makeup Artist",
        "worksFor": {"@id": f"{BASE}/#organization"},
        "url": f"{BASE}/about/#livian-gomes",
        "image": f"{BASE}/assets/images/livian-gomes.jpg",
        "nationality": {"@type": "Country", "name": "Brazil"},
        "knowsAbout": [
            "Permanent makeup",
            "Eyebrow permanent makeup",
            "Permanent eyeliner",
            "Lip blush",
        ],
        "hasCredential": {
            "@type": "EducationalOccupationalCredential",
            "credentialCategory": "Professional license",
            "name": "Body Art Practitioner License",
            # Numero proprio da Livian, confirmado pela Rachel em 25/09/2026.
            # A tabela chegou a repetir o 20261923 da Adriana nas duas linhas.
            "identifier": "20261924",
            "validUntil": "2026-12-31",
            "recognizedBy": {
                "@type": "GovernmentOrganization",
                "name": "Town of Wilmington Board of Health",
            },
        },
        "workLocation": {"@id": f"{BASE}/#wilmington"},
    },
    {
        "@type": "Person",
        "@id": f"{BASE}/about/#sofia-laura",
        "name": "Sofia Laura",
        "worksFor": {"@id": f"{BASE}/#organization"},
        "url": f"{BASE}/about/#sofia-laura",
        "image": f"{BASE}/assets/images/sofia-laura.jpg",
        "nationality": {"@type": "Country", "name": "Brazil"},
    },
]


def add_team(graph, path_rel):
    """Person de cada colega na /about/, onde as bios estao visiveis."""
    if path_rel != "about/index.html":
        return graph
    # Substitui o no existente em vez de so acrescentar quando falta: com
    # "se nao existe, acrescenta", uma correcao aqui (ex.: a licenca da
    # Livian, 25/09/2026) nunca chegava a pagina que ja tinha o no antigo.
    ids = {node["@id"] for node in TEAM_NODES}
    graph[:] = [n for n in graph if not (isinstance(n, dict) and n.get("@id") in ids)]
    for node in TEAM_NODES:
        graph.append(dict(node))
    # a Organization passa a listar quem trabalha nela
    for n in graph:
        if isinstance(n, dict) and n.get("@type") == "Organization":
            n["employee"] = [
                {"@id": PERSON_ID},
                {"@id": f"{BASE}/about/#livian-gomes"},
                {"@id": f"{BASE}/about/#sofia-laura"},
            ]
    return graph


# ====================================================================
# B06 — Criterios de escolha (FASE 2, 21/09/2026)
#
# A auditoria achou o bloco em 1 das 65 paginas. Ele e OBRIGATORIO na
# tipologia commercial (page-anatomy-by-intent.md), que aqui sao os
# hubs de categoria e as 13 master de servico.
#
# O formato e o da skill: tabela, nunca lista, com a pergunta que o
# cliente deveria fazer a QUALQUER artista — inclusive a um concorrente
# — e a resposta desta empresa. Cada resposta abaixo usa apenas dado
# ja publicado e verificavel neste site (numero de licenca, credencial,
# o que o preco inclui). Nada foi acrescentado para preencher linha.
# ====================================================================

# A ultima coluna muda por servico: e o que evita 23 tabelas identicas
# e o que torna a linha util na pagina em que ela esta.
SERVICE_FIT = {
    "microblading": (
        "Strokes hold best on normal to dry skin. On oily skin they tend to blur, "
        "and powder or combination work holds better."),
    "nano-brows": (
        "Nano strokes are machine-drawn and suit most skin types, which is why they "
        "cost more than microblading here ($650 against $550)."),
    "powder-brows": (
        "Powder shading is the technique that holds best on oily skin, where "
        "hair-stroke work tends to blur."),
    "combination-brows": (
        "Strokes at the front and shading through the body. Because the mix changes "
        "per face, this is the one service quoted at the consultation, not price-listed."),
    "nano-combo": (
        "Nano strokes plus soft shading, for density without a fully powdered look."),
    "lip-blush": (
        "Lip blush adds translucent colour. It is not a colour correction: lips with "
        "existing dark pigment start with neutralization instead."),
    "dark-lip-neutralization": (
        "This is corrective work on existing pigment, so it is quoted per case and "
        "may need more than one session."),
    "top-eyeliner": "Upper lash line only. Ask what happens to the line as it heals and softens.",
    "bottom-eyeliner": "Lower lash line only, the most subtle of the eyeliner options at $250.",
    "smokey-eyeliner": "A shaded, diffused finish rather than a defined line.",
    "eyeliner-combo": "Top and bottom in the same appointment, at $500 instead of $350 plus $250 separately.",
    "eyebrows-lips-combo": "Brows and lips in one visit at $850, against $1,100 booked separately.",
    "yearly-touch-up": (
        "Priced from $300 by how much pigment is left, so the quote depends on a look "
        "at your current result, not on a table."),
}

CATEGORY_FIT = {
    "eyebrows": ("Five brow techniques are offered here, and they are not "
                 "interchangeable: skin type decides which one holds."),
    "eyeliner": "Four eyeliner options, from a subtle lower line to a full shaded finish.",
    "lips": "Additive colour and corrective work are different services with different outcomes.",
    "combos": "Combining services in one visit costs less than booking them apart.",
    "touch-ups": "Maintenance of existing permanent makeup, priced by how much pigment remains.",
}


def _criteria_rows(fit_text):
    rows = [
        ("Practitioner licence",
         "Ask for the licence number and check it yourself with the state or the town, instead of taking a badge on a website at face value.",
         "New Hampshire Body Artist licence 4283, valid through 18 July 2028 and searchable at the state&rsquo;s own public lookup. Town of Salem BODA-10 and BODE-4. Body Art Practitioner licence from the Town of Wilmington Board of Health."),
        ("Who trained them",
         "Ask who certified the artist, and whether that credential can be checked with the body that issued it.",
         "AAM Diamond Certified Trainer, the American Academy of Micropigmentation&rsquo;s highest level of instructor recognition."),
        ("What the price includes",
         "Ask whether the perfecting session is included or billed later. This is where quoted prices most often stop matching the final bill.",
         "The perfecting session, 6 to 8 weeks after the appointment, is included in every original price. The yearly touch-up, from $300, is a separate visit about 12 months later."),
        ("Whether the price is published at all",
         "Ask for the price before the consultation. A studio that will not name a range before seeing you is not comparable to one that will.",
         "All 13 services are published with their prices, from $250 to $850, on the <a href=\"{up}prices/\">price list</a>."),
        ("When they say no",
         "Ask what would make them refuse to perform the procedure. An artist who never refuses is a warning sign.",
         "Pregnancy, breastfeeding, under 18 and isotretinoin are refused at both studios with no exception. The full list is in the <a href=\"{up}aftercare/\">contraindications guide</a>, published before you book rather than after."),
        ("Whether the technique fits you",
         "Ask which technique suits your skin type, and what they would recommend if this one does not.",
         fit_text + " This is settled at the free consultation, in English or Portuguese."),
    ]
    return rows


def add_criteria(s, path_rel):
    """B06: tabela de criterios nas paginas de tipologia commercial."""
    if "criteria-table" in s or "</main>" not in s:
        return s

    m = re.match(r"services/([a-z-]+)/([a-z0-9-]+)/index\.html$", path_rel)
    cat = re.match(r"services/([a-z-]+)/index\.html$", path_rel)
    if m:
        fit = SERVICE_FIT.get(m.group(2))
    elif cat:
        fit = CATEGORY_FIT.get(cat.group(1))
    else:
        return s
    if not fit:
        return s

    up = _up(path_rel)
    body = "".join(
        "<tr><th scope=\"row\">{}</th><td>{}</td><td>{}</td></tr>".format(
            c, q, a.replace("{up}", up))
        for c, q, a in _criteria_rows(fit)
    )
    block = (
        '<section class="section criteria-table"><div class="container">'
        "<h2>What Should You Check Before Booking Permanent Makeup Anywhere?</h2>"
        '<p class="direct-answer">Six things are worth verifying with any permanent makeup '
        "artist before you book: their licence number, who trained them, what the price "
        "includes, whether a price is published at all, what they refuse to do, and whether "
        "the technique actually suits your skin.</p>"
        '<div class="table-wrap"><table>'
        "<thead><tr><th scope=\"col\">What to check</th>"
        "<th scope=\"col\">What to ask any artist</th>"
        "<th scope=\"col\">The answer here</th></tr></thead>"
        "<tbody>" + body + "</tbody></table></div>"
        "</div></section>"
    )
    return s.replace("</main>", block + "\n</main>", 1)


# ====================================================================
# B12 — FAQ com as categorias obrigatorias (FASE 2, 21/09/2026)
#
# A auditoria achou 59 paginas abaixo do minimo de 10 perguntas, com
# respostas de ~20 palavras (o piso e 40 a 80, com dado concreto).
#
# As perguntas abaixo cobrem as categorias do B12 que faltavam em todo
# o site: preco, pagamento, garantia, manutencao, requisito e prova.
# Cada resposta usa numero ja publicado neste site. A categoria
# CANCELAMENTO ficou de fora de proposito: a politica de deposito e
# remarcacao nao esta documentada em lugar nenhum e nao se inventa
# politica comercial (Regra 1). Esta em pendencias-cliente.
# ====================================================================

FAQ_PRICES = {
    "microblading": "550", "nano-brows": "650", "powder-brows": "550",
    "nano-combo": "600", "lip-blush": "550", "dark-lip-neutralization": "550",
    "top-eyeliner": "350", "smokey-eyeliner": "400", "bottom-eyeliner": "250",
    "eyeliner-combo": "500", "eyebrows-lips-combo": "850",
}


def _faq_extra(label, price, up):
    """Perguntas por categoria do B12, com resposta de 40 a 80 palavras."""
    qa = []

    if price:
        qa.append((
            f"How much does {label} cost, and what is included?",
            f"{label} costs ${price} at both studios, and that price already includes the "
            f"perfecting session scheduled 6 to 8 weeks after the appointment. The "
            f"consultation, the mapping and the topical numbing are part of it as well. "
            f"A yearly touch-up, from $300, is a separate visit about 12 months later. "
            f"Every price is published on the <a href=\"{up}prices/\">price list</a>."))
    else:
        qa.append((
            f"How is {label} priced?",
            f"{label} is quoted at the consultation rather than listed at a fixed price, "
            f"because the work needed changes from face to face. Every other service is "
            f"published openly, from $250 to $850, on the "
            f"<a href=\"{up}prices/\">price list</a>, so you can see the range the studio "
            f"works in before you book anything."))

    qa.append((
        "Can I pay in installments?",
        "Yes. Cherry offers 4 interest-free payments, or a longer plan of up to 24 months "
        "with interest. Checking your options takes about a minute and uses a soft credit "
        "check, so it does not affect your credit score. Cherry is an independent financing provider: "
        "it sets approval and rates, not the studio. See "
        f"<a href=\"{up}payment-plan/\">how the payment plan works</a>."))

    qa.append((
        "What happens if the colour heals unevenly?",
        "The perfecting session exists for exactly that. It is scheduled 6 to 8 weeks after "
        "the first appointment, once the skin has healed, and it is included in the original "
        "price at no extra charge. Pigment settles differently on different skin, so the "
        "second pass is part of the procedure rather than a repair you pay for."))

    qa.append((
        "How often will I need a touch-up?",
        "Most clients book a colour refresh every 12 to 24 months; how long the pigment itself lasts depends on the technique and your skin (each service page gives its own range). After that, a "
        "yearly touch-up refreshes the colour from $300, priced by how much pigment is "
        "left rather than at a flat rate. That is a separate visit from the perfecting "
        "session, which is included in the original price and happens in the first weeks."))

    qa.append((
        "Is there anyone who should not book?",
        "Yes. Pregnancy, breastfeeding, being under 18, and current isotretinoin use are "
        "refused at both studios, with no exception. Blood thinners, autoimmune conditions "
        "and a history of keloid scarring need clearance from your doctor first. The full "
        f"list is published in the <a href=\"{up}aftercare/\">contraindications guide</a> "
        f"before you book, not after."))

    qa.append((
        "How experienced is the artist doing the work?",
        "Adriana Souza Santos has performed more than 5,000 procedures across 20+ years and "
        "trained over 300 students. She holds AAM Diamond Certified Trainer status and New "
        "Hampshire Body Artist licence 4283, valid through 18 July 2028, which you can "
        "verify yourself at the state&rsquo;s public lookup rather than take on trust."))

    return qa


def add_faq_items(s, path_rel):
    """Completa a FAQ ate cobrir as categorias obrigatorias do B12."""
    if "faq-list" not in s or "faq-b12" in s:
        return s
    # aria-expanded e OPCIONAL: as 26 paginas servico-cidade usam
    # <button type="button"> puro, e exigi-lo fazia o contador achar zero
    # pergunta justamente nas paginas que mais precisavam do bloco.
    existing = re.findall(r'class="faq-item[^"]*"><button[^>]*>(.*?)</button>', s, re.S)
    existing_l = [re.sub(r"<[^>]+>", "", q).strip().lower() for q in existing]
    if len(existing_l) >= 10:
        return s

    m = re.match(r"services/([a-z-]+)/([a-z0-9-]+)/", path_rel)
    cat = re.match(r"services/([a-z-]+)/index\.html$", path_rel)
    if m:
        slug = m.group(2)
        label = re.sub(r"<[^>]+>", "", get(r"<h1[^>]*>(.*?)</h1>", s, re.S) or "")
        label = re.sub(r"\s+in\s+.*$", "", re.sub(r"\s+", " ", label)).strip() or "This service"
        price = FAQ_PRICES.get(slug)
    elif cat:
        label = "This service"
        price = None
    else:
        return s

    up = _up(path_rel)
    add = []
    for q, a in _faq_extra(label, price, up):
        if any(q.lower()[:28] in e for e in existing_l):
            continue
        add.append(
            '<div class="faq-item faq-b12"><button type="button" aria-expanded="false">'
            f"{q}</button><div class=\"faq-answer\"><p>{a}</p></div></div>"
        )
    if not add:
        return s

    # Insere no fim do .faq-list. O replace literal de "</div></div></section>"
    # falhava nas paginas cujo HTML tem quebra de linha ali, que sao justamente
    # as de servico-cidade. Aqui o fechamento e encontrado contando <div>.
    start = s.find('<div class="faq-list"')
    if start < 0:
        return s
    i = s.find(">", start) + 1
    depth = 1
    while i < len(s) and depth:
        nxt = re.search(r"<(/?)div\b", s[i:])
        if not nxt:
            return s
        i += nxt.end()
        depth += -1 if nxt.group(1) else 1
    close = i - len("</div>") if s[i - len("</div>"):i] == "</div>" else None
    if close is None:
        close = s.rfind("</div>", 0, i)
    return s[:close] + "".join(add) + s[close:]


# Perguntas para as paginas que nao sao servico: cursos da academy, hub de
# servicos, lista de precos e aftercare. Mesmas categorias do B12, com o
# dado de cada contexto. Cancelamento continua fora (Regra 1).
FAQ_BY_PAGE = {
    "academy/pmu-100h-fundamental/index.html": [
        ("How much does the 100-Hour Fundamental course cost, and what is included?",
         "The 100-Hour Fundamental costs $7,000 and runs over 9 days in Peabody, MA. It covers "
         "five techniques &mdash; microblading, ombr&eacute; shading, microshading, lip blush and dark lip "
         "neutralization &mdash; with practice on live models under supervision, and it carries "
         "certification from the American Academy of Micropigmentation."),
        ("Can I pay the course in installments?",
         "Yes. Cherry offers 4 interest-free payments or a longer plan of up to 24 months with "
         "interest, and checking your options uses a soft credit check that does not affect your "
         "score. Cherry sets approval and rates, not the academy. The VIP Masterclass also has an "
         "in-house plan."),
        ("Do I need a licence to work after the course?",
         "Certification and licence are different things. The course gives you an AAM-accredited "
         "certificate; the licence to practise is issued by government. Massachusetts licenses "
         "body art town by town through each Board of Health, while New Hampshire licenses at "
         "state level under RSA 314-A. You apply where you intend to work."),
        ("Who teaches the course?",
         "Adriana Souza Santos, AAM Diamond Certified Trainer, which is the American Academy of "
         "Micropigmentation&rsquo;s highest level of instructor recognition. She has performed more "
         "than 5,000 procedures across 20+ years and has trained over 300 students. Classes are "
         "taught in English and in Portuguese."),
        ("Where are classes held?",
         "All training happens at Adriana&rsquo;s Academy, 39 Cross Street, Suite 206, Peabody, MA. "
         "That address is the training division and serves students only &mdash; no client procedures "
         "are performed there. Client appointments stay at the Wilmington, MA and Salem, NH studios."),
    ],
    "academy/pmu-apprenticeship/index.html": [
        ("How much does the apprenticeship cost?",
         "The apprenticeship runs $700 a month. It is the longer path: a year of supervised "
         "practice rather than an intensive, built around advanced model practice, client "
         "simulation, and the business side of working as an artist. The 100-Hour Fundamental, "
         "at $7,000, is the shorter and more structured alternative."),
        ("Can I pay in installments?",
         "The apprenticeship is already billed monthly at $700. For the 100-Hour Fundamental, "
         "Cherry offers 4 interest-free payments or up to 24 months with interest, using a soft "
         "credit check that does not affect your score. Cherry is an independent financing provider and sets "
         "approval and rates, not the academy."),
        ("Who supervises the apprenticeship?",
         "Adriana Souza Santos, AAM Diamond Certified Trainer &mdash; the American Academy of "
         "Micropigmentation&rsquo;s highest instructor level &mdash; with more than 5,000 procedures "
         "across 20+ years and over 300 students trained. Supervision happens in person at the "
         "Peabody studio, in English or in Portuguese."),
        ("Do I need the 100-hour course first?",
         "The two are separate paths and the right one depends on where you are starting. Bring "
         "that question to the consultation: the academy will tell you honestly which fits, "
         "rather than selling you both. The VIP Masterclass exists for exactly the cases that do "
         "not fit either standard format."),
        ("Where does the apprenticeship take place?",
         "At Adriana&rsquo;s Academy, 39 Cross Street, Suite 206, Peabody, MA, which is the training "
         "division and serves students only. No client procedures happen at that address; "
         "client work stays at the Wilmington, MA and Salem, NH studios."),
    ],
    "academy/vip-masterclass/index.html": [
        ("Why is there no fixed price for the VIP Masterclass?",
         "Because one number would be wrong for almost everyone. A complete beginner and a "
         "working artist fixing her lip blush healing need different classes, so the class is "
         "quoted after a short conversation about your level, the technique you want, how many "
         "sessions that honestly takes, and your schedule."),
        ("Can I pay the VIP Masterclass in installments?",
         "Yes. This course has an in-house payment plan, separate from the Cherry plan used for "
         "services and for the 100-Hour Fundamental. The terms are set when the class is quoted, "
         "since the scope and the number of sessions change from student to student."),
        ("Is it open to complete beginners?",
         "Yes, and also to artists already taking clients. That is the point of quoting it "
         "individually: the syllabus is built from where you actually are rather than from a "
         "fixed curriculum. Beginners and working artists simply get different classes under "
         "the same name."),
        ("Who teaches it?",
         "Adriana Souza Santos, AAM Diamond Certified Trainer, the American Academy of "
         "Micropigmentation&rsquo;s highest instructor level, with more than 5,000 procedures across "
         "20+ years and over 300 students trained. The class is one-on-one, in English or in "
         "Portuguese."),
        ("Where is it taught?",
         "At Adriana&rsquo;s Academy, 39 Cross Street, Suite 206, Peabody, MA &mdash; the training "
         "division, students only. No client procedures are performed at that address. Client "
         "appointments are at the Wilmington, MA and Salem, NH studios."),
    ],
    "services/index.html": [
        ("How much do the services cost?",
         "Thirteen services are published with their prices, from $250 for bottom eyeliner to "
         "$850 for the brows and lips combo. Every original price already includes the perfecting "
         "session 6 to 8 weeks later. The full table is on the price list, and combination brows "
         "is the one service quoted at the consultation."),
        ("Can I pay in installments?",
         "Yes. Cherry offers 4 interest-free payments, or up to 24 months with interest. Checking "
         "your options takes about a minute and uses a soft credit check, so it does not affect "
         "your credit score. Cherry is an independent financing provider: it sets approval and rates, not "
         "the studio."),
        ("What happens if the colour heals unevenly?",
         "The perfecting session covers it. Scheduled 6 to 8 weeks after the first appointment, "
         "once the skin has healed, it is included in the original price at no extra charge. "
         "Pigment settles differently on different skin, so a second pass is part of the "
         "procedure rather than a paid repair."),
        ("Who should not book any of these services?",
         "Pregnancy, breastfeeding, being under 18 and current isotretinoin use are refused at "
         "both studios with no exception. Blood thinners, autoimmune conditions and a history of "
         "keloid scarring need clearance from a doctor first. The full list is published in the "
         "contraindications guide before you book."),
        ("How experienced is the artist?",
         "Adriana Souza Santos has performed more than 5,000 procedures across 20+ years and "
         "trained over 300 students. She holds AAM Diamond Certified Trainer status and New "
         "Hampshire Body Artist licence 4283, valid through 18 July 2028, which anyone can verify "
         "at the state&rsquo;s public lookup."),
    ],
    "locations/index.html": [
        ("Which studio should I book for a procedure?",
         "Either Wilmington, MA or Salem, NH &mdash; they offer the same 13 services at the same "
         "prices. Pick by distance and by phone number: Wilmington is 211 Lowell Street, Suite F, "
         "(781) 853-8063; Salem is 117A Main Street, (978) 223-7496. The Peabody address is the "
         "academy and treats no clients."),
        ("Why is the Peabody address not an option for treatments?",
         "Because it is the training division. Adriana&rsquo;s Academy at 39 Cross Street, Suite 206, "
         "Peabody, MA serves students only &mdash; the 100-hour course, the apprenticeship and the "
         "VIP Masterclass are taught there. No client procedures happen at that address, so never "
         "book a brow or lip appointment for Peabody."),
        ("Do the two studios charge the same?",
         "Yes. The same 13 services are published at the same prices at both, from $250 to $850, "
         "and every original price includes the perfecting session 6 to 8 weeks later. What "
         "differs between them is the phone number and the licensing regime, not the price list."),
        ("Are the licences different in Massachusetts and New Hampshire?",
         "Yes, and that is worth knowing. Massachusetts has no single state body art licence: each "
         "town&rsquo;s Board of Health licenses separately, which is why Wilmington issues its own "
         "numbers. New Hampshire licenses at state level under RSA 314-A, and the Town of Salem "
         "licenses on top of that."),
        ("What are the opening hours?",
         "Both studios are open Monday to Saturday, 10:00 a.m. to 6:00 p.m., and closed on Sunday. "
         "Booking runs through Fresha for real-time availability, or by phone at the number of the "
         "studio you want: (781) 853-8063 for Wilmington, (978) 223-7496 for Salem."),
    ],
    "academy/index.html": [
        ("Which course should I start with?",
         "The 100-Hour Fundamental at $7,000 is the structured entry point: 9 days, five "
         "techniques, AAM-accredited. The apprenticeship at $700 a month is a year of supervised "
         "practice instead. The VIP Masterclass is quoted individually for cases that fit neither. "
         "The consultation tells you which, honestly."),
        ("Does the certificate let me work legally?",
         "No, and no school&rsquo;s does. The certificate is training; the licence to practise is "
         "issued by government. Massachusetts licenses body art town by town through each Board of "
         "Health, while New Hampshire licenses at state level under RSA 314-A. You apply where you "
         "intend to work, after training."),
        ("Can I pay in installments?",
         "Yes. Cherry offers 4 interest-free payments or up to 24 months with interest for the "
         "100-Hour Fundamental, using a soft credit check that does not affect your score. The "
         "apprenticeship is already monthly at $700, and the VIP Masterclass has its own in-house "
         "plan set when it is quoted."),
        ("Who teaches, and what backs them?",
         "Adriana Souza Santos, AAM Diamond Certified Trainer &mdash; the American Academy of "
         "Micropigmentation&rsquo;s highest instructor level. More than 5,000 procedures across 20+ "
         "years, over 300 students trained, and New Hampshire Body Artist licence 4283 that anyone "
         "can verify at the state&rsquo;s public lookup."),
        ("Do I practise on real people?",
         "Yes. The 100-Hour Fundamental includes practice on live models under supervision across "
         "its 9 days, and the apprenticeship is built around a year of supervised model practice "
         "and client simulation. Training happens only at the Peabody studio, which serves "
         "students and never clients."),
    ],
    "prices/index.html": [
        ("Is the perfecting session included in these prices?",
         "Yes, in every original price. It is scheduled 6 to 8 weeks after the first appointment, "
         "once the skin has healed, and costs nothing extra. The yearly touch-up is the one that "
         "is billed separately, from $300, about 12 months later and priced by how much pigment "
         "is left."),
        ("Can I pay in installments?",
         "Yes. Cherry offers 4 interest-free payments or a longer plan of up to 24 months with "
         "interest. Checking your options uses a soft credit check and takes about a minute, so "
         "it does not affect your credit score. Cherry sets approval and rates independently of "
         "the studio."),
        ("Why is combination brows the only service without a price?",
         "Because the mix of strokes and shading changes from face to face, and a single number "
         "would be wrong for most people. It is quoted at the consultation instead. Every other "
         "service is published openly, which is the opposite of the usual practice of hiding all "
         "prices behind a form."),
        ("Do prices differ between the Wilmington and Salem studios?",
         "No. The same 13 services are published at the same prices at both addresses: 211 Lowell "
         "Street, Suite F in Wilmington, MA, and 117A Main Street in Salem, NH. What differs "
         "between them is the phone number and the licensing regime, not the price."),
        ("How long do the results last before I pay again?",
         "Most clients book a colour refresh every 12 to 24 months; how long the pigment itself lasts depends on the technique and your skin (each service page gives its own range). The perfecting session "
         "in the first weeks is included; after that, the next paid visit is the yearly touch-up, "
         "from $300, priced by how much pigment remains rather than at a flat rate."),
    ],
    "aftercare/index.html": [
        ("How long does healing actually take?",
         "Surface healing takes about 4 weeks, and the colour keeps settling for a few weeks "
         "after that. This is why the perfecting session is scheduled 6 to 8 weeks out rather "
         "than sooner: judging the result before the skin has finished healing leads to "
         "correcting something that was going to settle on its own."),
        ("What should make me call a doctor instead of the studio?",
         "Spreading redness, swelling that increases after the first days, pus, fever, or pain "
         "that gets worse rather than better are signs for a clinician, not for the studio. The "
         "studio handles colour and healing of the pigment; it does not diagnose or treat "
         "infection, and will tell you to see a doctor."),
        ("Who should not book at all?",
         "Pregnancy, breastfeeding, being under 18 and current isotretinoin use are refused at "
         "both studios with no exception. Blood thinners, autoimmune conditions and a history of "
         "keloid scarring need written clearance from your doctor before booking. These are "
         "published here so you can check before paying anything."),
        ("Does aftercare differ between brows, lips and eyeliner?",
         "The principles are the same &mdash; keep it clean, do not pick, avoid soaking and direct sun "
         "&mdash; but the timelines and the specific cautions differ by area, and lips in particular "
         "have their own instructions around cold sores. The written instructions you take home "
         "are specific to the procedure you had."),
    ],
}



AFTERCARE_SECTION_QA = [
    {
        "@type": "Question",
        "name": "What Is Permanent Makeup Aftercare, and Why Does It Matter?",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": "Permanent makeup aftercare refers to the cleaning, moisturizing, and protective steps a client follows after a brow, lip, or eyeliner procedure to help the skin heal correctly and the pigment settle evenly. Because the treated area is an open micro-wound for the first 24 to 48 hours, aftercare directly affects both the healed color and the risk of infection."
        }
    },
    {
        "@type": "Question",
        "name": "Should I Dry Heal or Moist Heal My Permanent Makeup?",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": "Dry healing means cleaning the treated area and leaving it uncovered with no ointment, while moist healing means applying a thin layer of a fragrance-free aftercare balm two to three times a day. Eyeliner is almost always dry-healed; brows and lips are moist-healed at Adriana's Permanent Makeup unless the artist gives different instructions in writing."
        }
    },
    {
        "@type": "Question",
        "name": "What Should I Avoid After Permanent Makeup, and for How Long?",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": "Clients should avoid direct sun and tanning beds for 4 weeks, swimming pools, hot tubs, and natural bodies of water for 14 days, and makeup applied directly over the area until it has finished peeling, typically 10 to 14 days. Each restriction protects the pigment or the open skin from a different risk."
        }
    },
    {
        "@type": "Question",
        "name": "Who Should Not Get Permanent Makeup, or Needs Medical Clearance First?",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": "Certain conditions rule permanent makeup out entirely; others simply require written medical clearance first. Pregnancy, breastfeeding, active isotretinoin use, and being under 18 fall into the first group; diabetes, autoimmune disease, and blood-thinning medication fall into the second, decided case by case with a doctor's input."
        }
    },
    {
        "@type": "Question",
        "name": "What's Normal During Healing, and When Should I See a Doctor Instead of the Studio?",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": "Normal healing includes color that looks too dark for the first 3 to 5 days, mild swelling for 24 to 48 hours, light flaking through day 14, and patchy color before the touch-up. Spreading redness, pus, fever, or pain that worsens are signs of infection and need a doctor right away, not just the studio."
        }
    },
    {
        "@type": "Question",
        "name": "Why Do I Need a Touch-Up Session, and When Is It Scheduled?",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": "A touch-up session exists because the first appointment cannot fully predict how much pigment an individual client's skin will retain during healing. Adriana's Permanent Makeup schedules the perfecting touch-up 6 to 8 weeks after the initial procedure, once the skin has finished its full healing cycle and the true color has settled."
        }
    }
]

def add_faq_by_page(s, path_rel):
    """FAQ das paginas que nao sao servico (cursos, hubs, precos, aftercare)."""
    items = FAQ_BY_PAGE.get(path_rel)
    if not items or "faq-b12" in s:
        return s
    # /academy/ e /locations/ nao tinham bloco de FAQ nenhum: a secao inteira
    # e criada aqui. Nas demais, as perguntas entram na .faq-list existente.
    if "faq-list" not in s:
        if "</main>" not in s:
            return s
        body = "".join(
            '<div class="faq-item faq-b12"><button type="button" aria-expanded="false">'
            f"{q}</button><div class=\"faq-answer\"><p>{a}</p></div></div>"
            for q, a in items
        )
        sec = ('<section class="section section-alt" id="faq"><div class="container">'
               "<h2>Frequently Asked Questions</h2>"
               f'<div class="faq-list">{body}</div></div></section>')
        return s.replace("</main>", sec + "\n</main>", 1)
    existing = [re.sub(r"<[^>]+>", "", q).strip().lower()
                for q in re.findall(r'class="faq-item[^"]*"><button[^>]*>(.*?)</button>', s, re.S)]
    add = []
    for q, a in items:
        if any(q.lower()[:28] in e for e in existing):
            continue
        add.append('<div class="faq-item faq-b12"><button type="button" aria-expanded="false">'
                   f"{q}</button><div class=\"faq-answer\"><p>{a}</p></div></div>")
    if not add:
        return s
    start = s.find('<div class="faq-list"')
    if start < 0:
        return s
    i = s.find(">", start) + 1
    depth = 1
    while i < len(s) and depth:
        nxt = re.search(r"<(/?)div\b", s[i:])
        if not nxt:
            return s
        i += nxt.end()
        depth += -1 if nxt.group(1) else 1
    close = i - len("</div>") if s[i - len("</div>"):i] == "</div>" else s.rfind("</div>", 0, i)
    return s[:close] + "".join(add) + s[close:]


# B06/B04 para a Academy (FASE 2). As perguntas que um aluno deveria fazer a
# QUALQUER escola de PMU. Todo dado abaixo ja esta publicado neste site.
ACADEMY_CRITERIA = [
    ("Who is actually teaching",
     "Ask for the instructor&rsquo;s name and credential, not the school&rsquo;s. Many schools sell a brand and hand the class to someone else.",
     "Adriana Souza Santos teaches, and holds AAM Diamond Certified Trainer status &mdash; the American Academy of Micropigmentation&rsquo;s highest instructor level &mdash; with 5,000+ procedures and 300+ students trained."),
    ("Whether the certificate is accredited",
     "Ask which body accredits the certificate, and confirm that body exists and recognises the school.",
     "The 100-Hour Fundamental is accredited by the American Academy of Micropigmentation."),
    ("Certificate against licence",
     "Ask whether the certificate lets you work legally. A school that lets you believe it does is selling you a problem.",
     "It does not, and that is stated plainly here: the certificate is training. The licence to practise is issued by government &mdash; town by town in Massachusetts, at state level in New Hampshire under RSA 314-A."),
    ("Hands-on practice on live models",
     "Ask how many live models you work on, and who supervises while you do.",
     "The 100-Hour Fundamental is 9 days with practice on live models under supervision; the apprenticeship is a year of supervised practice at $700 a month."),
    ("What the price covers",
     "Ask for the total, and what is not in it.",
     "$7,000 for the 100-Hour Fundamental, $700 a month for the apprenticeship. The VIP Masterclass is quoted per student because the scope changes. Cherry installments are available."),
    ("Where the training happens",
     "Ask for the training address, and whether clients are treated in the same room.",
     "All training is at 39 Cross Street, Suite 206, Peabody, MA, students only. Client procedures happen at the Wilmington and Salem studios, never at the academy."),
]

ACADEMY_FIT = {
    "academy/index.html": (
        "anyone building a career in permanent makeup, from complete beginners to working "
        "artists correcting a specific technique",
        "you want a weekend hobby certificate, or you expect the certificate itself to license "
        "you to work &mdash; licensing is issued by government, not by a school"),
    "academy/pmu-100h-fundamental/index.html": (
        "you are starting from zero and want a structured, accredited foundation across five "
        "techniques in 9 days",
        "you already take clients and need to fix one specific technique &mdash; the "
        "<a href=\"{up}academy/vip-masterclass/\">VIP Masterclass</a> is built for that case"),
    "academy/pmu-apprenticeship/index.html": (
        "you want a year of supervised practice rather than an intensive, and can commit to "
        "$700 a month over that period",
        "you need certification quickly &mdash; the "
        "<a href=\"{up}academy/pmu-100h-fundamental/\">100-Hour Fundamental</a> is the shorter path"),
    "academy/vip-masterclass/index.html": (
        "your case does not fit a standard class: a specific technique, an odd schedule, or a "
        "level between beginner and working artist",
        "a standard curriculum already fits you &mdash; the "
        "<a href=\"{up}academy/pmu-100h-fundamental/\">100-Hour Fundamental</a> costs less for the same foundation"),
}


def add_academy_blocks(s, path_rel):
    """B04 e B06 nas quatro paginas da Academy."""
    fit = ACADEMY_FIT.get(path_rel)
    if not fit or "academy-criteria" in s or "</main>" not in s:
        return s
    up = _up(path_rel)
    yes, no = (x.replace("{up}", up) for x in fit)

    b04 = (
        '<section class="section academy-fit"><div class="container service-prose">'
        "<h2>Who Is This Training For, and Who Is It Not For?</h2>"
        f'<p class="direct-answer">This is for {yes}.</p>'
        f"<p><strong>It is not for you if</strong> {no}.</p>"
        "</div></section>"
    )
    rows = "".join(
        f'<tr><th scope="row">{c}</th><td>{q}</td><td>{a}</td></tr>'
        for c, q, a in ACADEMY_CRITERIA
    )
    b06 = (
        '<section class="section academy-criteria"><div class="container">'
        "<h2>What Should You Check Before Paying for Any PMU Course?</h2>"
        '<p class="direct-answer">Six things are worth verifying with any permanent makeup '
        "school: who actually teaches, whether the certificate is accredited, whether it "
        "licenses you to work, how much live-model practice you get, what the price covers, "
        "and where the training happens.</p>"
        '<div class="table-wrap"><table>'
        '<thead><tr><th scope="col">What to check</th><th scope="col">What to ask any school</th>'
        '<th scope="col">The answer here</th></tr></thead>'
        "<tbody>" + rows + "</tbody></table></div></div></section>"
    )
    return s.replace("</main>", b04 + b06 + "\n</main>", 1)


def add_payment_steps(s, path_rel):
    """B05 (como funciona) na pagina de parcelamento."""
    if path_rel != "payment-plan/index.html" or "payment-steps" in s or "</main>" not in s:
        return s
    block = (
        '<section class="section payment-steps"><div class="container service-prose">'
        "<h2>How Does Paying Over Time Actually Work?</h2>"
        '<p class="direct-answer">Five steps, from checking your options to the last '
        "installment. Checking does not affect your credit score, and the studio is paid in "
        "full either way &mdash; the plan is between you and Cherry.</p>"
        "<ol>"
        "<li><strong>Check your options</strong> at Cherry. Takes about a minute and uses a "
        "soft credit check, so your score is untouched.</li>"
        "<li><strong>See what you qualify for</strong>: 4 interest-free payments, or a longer "
        "plan of up to 24 months with interest. Cherry sets the terms and the approval, not "
        "the studio.</li>"
        "<li><strong>Book the appointment</strong> at Wilmington or Salem for the service you "
        "chose, from $250 to $850.</li>"
        "<li><strong>Have the procedure</strong>, perfecting session included in the original "
        "price, 6 to 8 weeks later at no extra charge.</li>"
        "<li><strong>Pay Cherry on your schedule</strong> over the plan you picked, rather "
        "than the studio.</li>"
        "</ol>"
        "<p>Approval and rates are subject to eligibility. Cherry Technologies is a financial "
        "technology company, not a bank or a lender, and is independent of Adriana&rsquo;s "
        "Permanent Makeup.</p>"
        "</div></section>"
    )
    return s.replace("</main>", block + "\n</main>", 1)

def add_breadcrumb_nav(s, path_rel):
    """B03: breadcrumb VISIVEL nas paginas que so tinham o schema.

    A auditoria de 21/09/2026 achou 15 paginas (as 13 master de servico,
    /payment-plan/ e /flash-sale/) com BreadcrumbList no JSON-LD e nenhuma
    trilha na pagina. O schema afirmava uma navegacao que o visitante nao
    via — anti-pattern direto do B17 ("o JSON-LD so afirma o que esta
    visivel") e um OBR faltando na tipologia commercial.

    A trilha e montada A PARTIR do proprio BreadcrumbList, e nao de uma
    lista paralela, para que as duas nunca possam divergir.
    """
    # ATENCAO a detecao: o site usa DOIS padroes de classe para a mesma
    # trilha, 'breadcrumb' e 'breadcrumb container'. Procurar por
    # 'class="breadcrumb"' com a aspa final nao encontra o segundo e
    # injeta uma trilha duplicada em 15 paginas (erro cometido e
    # revertido em 21/09/2026). O prefixo sem aspa cobre os dois.
    if 'class="breadcrumb' in s or "</main>" not in s:
        return s
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    if not m:
        return s
    try:
        graph = json.loads(m.group(1)).get("@graph", [])
    except Exception:
        return s
    bc = next((n for n in graph if isinstance(n, dict) and n.get("@type") == "BreadcrumbList"), None)
    if not bc:
        return s
    items = sorted(bc.get("itemListElement", []), key=lambda x: x.get("position", 0))
    if len(items) < 2:
        return s
    up = _up(path_rel)
    lis = []
    for i, it in enumerate(items):
        name = str(it.get("name", "")).strip()
        if not name:
            return s
        if i == len(items) - 1:
            lis.append(f'<li aria-current="page">{name}</li>')
        else:
            target = str(it.get("item", "")).replace(BASE, "").lstrip("/")
            href = (up + target) if target else up
            lis.append(f'<li><a href="{href}">{name}</a></li>')
    nav = ('<nav class="breadcrumb" aria-label="Breadcrumb"><ol>'
           + "".join(lis) + "</ol></nav>")
    return re.sub(r'(<main[^>]*>)', r"\1\n    " + nav.replace("\\", "\\\\"), s, count=1)


def add_byline(s, path_rel):
    """B11 (autoria) visivel + link contextual para /about/ (item 6).

    Idempotente: se a pagina ja tem byline (as 26 de cidade tem), sai.
    """
    if path_rel in NO_BYLINE or "page-byline" in s:
        return s
    if "</main>" not in s:
        return s
    up = _up(path_rel)
    anchor = "Adriana Souza Santos, Master Permanent Makeup Artist"
    block = (
        '<section class="section"><div class="container">'
        f'<p class="page-byline">Reviewed by <a href="{up}about/">{anchor}</a> '
        "with 20+ years and 5,000+ procedures, AAM Diamond Certified Trainer, "
        "responsible for this page&#39;s accuracy. "
        f'Questions: <a href="{up}contact/">contact page</a>. '
        f"Last reviewed {REVIEW_DATE_HUMAN}.</p>"
        "</div></section>"
    )
    return s.replace("</main>", block + "\n</main>", 1)


# Hubs que declaram um cluster. O ItemList e montado a partir dos links
# de FILHO DIRETO que a propria pagina ja emite no corpo — nao ha lista
# fixa aqui de proposito: hub e ItemList nunca divergem.
HUB_TYPES = {
    "index.html": "WebPage",
    "services/index.html": "CollectionPage",
    "services/eyebrows/index.html": "CollectionPage",
    "services/eyeliner/index.html": "CollectionPage",
    "services/lips/index.html": "CollectionPage",
    "services/combos/index.html": "CollectionPage",
    "services/touch-ups/index.html": "CollectionPage",
    "locations/index.html": "CollectionPage",
    "academy/index.html": "CollectionPage",
    "portfolio/index.html": "CollectionPage",
}



_WEAK = {"learn more", "read more", "see more", "view more", "more", "click here",
         "book now", "see details", "details", "view", "here", "explore", "start"}


def _weak_anchor(name):
    return (not name) or name.strip().lower() in _WEAK or len(name.strip()) < 4


def _h1_of(url):
    """<h1> da pagina de destino, lido do arquivo local."""
    rel = url.replace(BASE, "").strip("/")
    fp = os.path.join(ROOT, rel, "index.html") if rel else os.path.join(ROOT, "index.html")
    if not os.path.exists(fp):
        return None
    with open(fp, encoding="utf-8") as f:
        h = f.read()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() or None


def _children_links(s, canonical):
    """URLs de filho direto linkadas no corpo, na ordem em que aparecem."""
    body = re.search(r"<main[^>]*>(.*?)</main>", s, re.S)
    if not body:
        return []
    seen, out = set(), []
    for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body.group(1), re.S):
        if href.startswith(("http", "tel:", "mailto:", "#")):
            continue
        target = urljoin(canonical, href.split("#")[0].split("?")[0])
        if not target.startswith(canonical) or target == canonical:
            continue
        if not target.endswith("/"):
            target += "/"
        # filho DIRETO: exatamente um segmento abaixo do hub
        rest = target[len(canonical):].strip("/")
        if not rest or "/" in rest:
            continue
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", label)).strip()
        # O name do ListItem nomeia a ENTIDADE, nao a acao. A ancora
        # ("See how the apprenticeship works") serve ao leitor; o <h1> da
        # pagina de destino e o nome canonico e e ele que entra aqui.
        # A ancora so e usada se a pagina de destino nao tiver <h1>.
        # Nada e inventado: o h1 e lido do arquivo de destino.
        name = _h1_of(target) or name
        if _weak_anchor(name):
            continue
        if not name or target in seen:
            continue
        seen.add(target)
        out.append((target, name))
    return out


def add_collection(graph, s, path_rel, canonical):
    """CollectionPage + ItemList nos hubs (nao existia nenhum no site)."""
    kind = HUB_TYPES.get(path_rel)
    if not kind or kind != "CollectionPage":
        return graph
    kids = _children_links(s, canonical)
    if len(kids) < 2:
        return graph
    # regenera: remove a versao anterior antes de recriar
    stale = {canonical + "#collection", canonical + "#itemlist"}
    graph[:] = [n for n in graph if not (isinstance(n, dict) and n.get("@id") in stale)]
    graph.append({
        "@type": "CollectionPage",
        "@id": canonical + "#collection",
        "url": canonical,
        "isPartOf": {"@id": f"{BASE}/#website"},
        "mainEntity": {"@id": canonical + "#itemlist"},
    })
    graph.append({
        "@type": "ItemList",
        "@id": canonical + "#itemlist",
        "numberOfItems": len(kids),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "url": url}
            for i, (url, name) in enumerate(kids)
        ],
    })
    return graph


def add_webpage(graph, s, path_rel, canonical):
    """WebPage com dateModified e autoria. Eram 5 paginas com dateModified."""
    if any(n.get("@id") == canonical + "#webpage" for n in graph if isinstance(n, dict)):
        return graph
    title = get(r"<title>(.*?)</title>", s, re.S)
    title = re.sub(r"\s+", " ", title).strip() if title else ""
    node = {
        "@type": "WebPage",
        "@id": canonical + "#webpage",
        "url": canonical,
        "isPartOf": {"@id": f"{BASE}/#website"},
        "inLanguage": "en-US",
        "dateModified": LASTMOD.get(canonical.replace(BASE, ""), REVIEW_DATE_ISO),
    }
    if title:
        node["name"] = title
    if path_rel not in NO_BYLINE:
        node["author"] = {"@id": PERSON_ID}
        node["reviewedBy"] = {"@id": PERSON_ID}
    graph.append(node)
    if not any(n.get("@id") == PERSON_ID for n in graph if isinstance(n, dict)):
        graph.append(dict(PERSON_NODE))
    return graph

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


HOURS = {
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    "opens": "10:00",
    "closes": "18:00",
}

# Campos que TODO no de unidade leva, em todas as paginas (auditoria
# pre-lancamento 25/09/2026). Antes: #wilmington sem url/image/
# parentOrganization em nenhuma pagina, #salem sem horario em 62 paginas,
# priceRange em dois formatos e nenhum hasMap. hasMap usa o CID da ficha
# do Google de cada unidade (lido no Local Falcon em 25/09/2026).
LOCATION_FIELDS = {
    f"{BASE}/#wilmington": {
        "url": f"{BASE}/locations/wilmington-ma/",
        "image": f"{BASE}/assets/images/locations/wilmington-ma-studio-entrance.jpg",
        "parentOrganization": {"@id": f"{BASE}/#organization"},
        "priceRange": "$250-$850",
        "openingHoursSpecification": HOURS,
        "hasMap": "https://maps.google.com/?cid=16715673055892397510",
    },
    f"{BASE}/#salem": {
        "url": f"{BASE}/locations/salem-nh/",
        "parentOrganization": {"@id": f"{BASE}/#organization"},
        "priceRange": "$250-$850",
        "openingHoursSpecification": HOURS,
        "hasMap": "https://maps.google.com/?cid=8332848331847351639",
    },
}


def normalize_graph(graph):
    """Unidades completas e iguais em todo o site, uma Adriana so, texto limpo.

    - no de unidade: garante os LOCATION_FIELDS (priceRange e hasMap sempre
      sobrescrevem; os outros so entram se faltarem)
    - Adriana aparecia como duas pessoas: /about/#adriana em 58 paginas e
      /#adriana em 6. Toda referencia passa para PERSON_ID e nos duplicados
      viram um so
    - entidades HTML (&rsquo;, &amp;) saiam cruas no JSON-LD de 52 paginas
    """
    import html as _html

    def fix(v):
        if isinstance(v, str):
            v = _html.unescape(v)
            return PERSON_ID if v == f"{BASE}/#adriana" else v
        if isinstance(v, list):
            return [fix(x) for x in v]
        if isinstance(v, dict):
            return {k: fix(x) for k, x in v.items()}
        return v

    graph = [fix(n) for n in graph]
    merged, out = {}, []
    for n in graph:
        if not isinstance(n, dict):
            out.append(n)
            continue
        nid = n.get("@id")
        if nid in LOCATION_FIELDS:
            for k, val in LOCATION_FIELDS[nid].items():
                if k in ("priceRange", "hasMap") or k not in n:
                    n[k] = val
        if nid and nid in merged and len(n) > 1:
            base = merged[nid]
            for k, val in n.items():
                base.setdefault(k, val)
            continue
        if nid:
            merged[nid] = n
        out.append(n)
    return out


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

    # 1b. WebSite (auditoria 21/09/2026: nao existia em NENHUMA pagina).
    #     E a ancora de entidade do site; sem ele o grafo nao tem raiz e
    #     nada pode declarar isPartOf.
    if f"{BASE}/#website" not in ids:
        graph.append(dict(WEBSITE_NODE))

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

    # 3. FAQPage a partir da FAQ VISIVEL.
    #    REGENERA em vez de so criar: quando a Fase 2 completou as perguntas
    #    (B12 exige 10 no minimo), o FAQPage tinha ficado com as 5 antigas
    #    enquanto a pagina mostrava 12. Schema que afirma menos do que a
    #    pagina mostra e a mesma classe de erro que schema que afirma mais.
    #    O seletor aceita classes extras em .faq-item (ex.: "faq-item faq-b12"),
    #    que era o outro motivo de os itens novos ficarem de fora.
    if "faq-item" in s:
        # MESCLA, nao substitui. Regenerar cegamente apagou as 6 perguntas da
        # /aftercare/, que vivem como secoes <h2> e nao como .faq-item: o
        # FAQPage caiu de 6 para 4. Perguntas antigas cujo texto ainda aparece
        # na pagina sao preservadas; as que sumiram do HTML saem, que era o
        # objetivo original da regeneracao.
        visible_text = re.sub(r"<[^>]+>", " ", s)
        kept = []
        for n in graph:
            if isinstance(n, dict) and n.get("@type") == "FAQPage":
                for qa in n.get("mainEntity", []):
                    name = str(qa.get("name", "")).strip()
                    probe = re.sub(r"\s+", " ", re.sub(r"&[a-z]+;", "", name))[:40]
                    if probe and probe.lower() in re.sub(r"\s+", " ", visible_text).lower():
                        kept.append(qa)
        graph[:] = [n for n in graph
                    if not (isinstance(n, dict) and n.get("@type") == "FAQPage")]
        pairs = re.findall(
            r'class="faq-item[^"]*"><button[^>]*>(.*?)</button><div class="faq-answer">(.*?)</div>',
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
        if path_rel == "aftercare/index.html":
            kept = AFTERCARE_SECTION_QA + kept
        seen_q = {q["name"] for q in qa}
        for k in kept:
            if k.get("name") not in seen_q:
                qa.append(k)
                seen_q.add(k.get("name"))
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
            "image": f"{BASE}/assets/images/adriana-souza-santos.jpg",
        })

    # 6. CollectionPage + ItemList nos hubs (nao havia nenhum ItemList no site)
    graph = add_collection(graph, s, path_rel, canonical)

    # 7. WebPage com dateModified e autoria (eram 5 paginas com dateModified)
    graph = add_webpage(graph, s, path_rel, canonical)

    # 8. Equipe na /about/
    graph = add_team(graph, path_rel)

    data["@graph"] = normalize_graph(graph)
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return s[: m.start()] + '<script type="application/ld+json">' + out + "</script>" + s[m.end():]


def _logo_sem_prioridade(m):
    tag = m.group(0).replace(' fetchpriority="high"', "").replace('loading="eager" ', "")
    return tag


def wrap_tables(s, path_rel):
    """Toda <table> dentro de .table-scroll (rolagem horizontal no celular).

    49 das 165 tabelas estavam fora dele. Com overflow-wrap:anywhere no CSS
    elas cabiam na tela quebrando palavra no meio ('Proced/ure', 'LICEN/SE');
    sem o corte, estourariam a largura. Com o wrapper, palavra inteira e a
    tabela rola quando nao cabe. Idempotente."""
    out, pos = [], 0
    for m in re.finditer(r"<table\b.*?</table>", s, re.S):
        antes = s[max(0, m.start() - 200):m.start()]
        out.append(s[pos:m.start()])
        if "table-scroll" in antes:
            out.append(m.group(0))
        else:
            cap = re.search(r"<caption[^>]*>(.*?)</caption>", m.group(0), re.S)
            rot = re.sub(r"<[^>]+>", "", cap.group(1)).strip() if cap else "Table"
            rot = rot.replace('"', "&quot;")
            out.append(f'<div class="table-scroll" tabindex="0" role="region" aria-label="{rot}">'
                       + m.group(0) + "</div>")
        pos = m.end()
    out.append(s[pos:])
    return "".join(out)


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

    # A primeira <img> do DOCUMENTO e o logo do header: ele recebia
    # fetchpriority=high em todas as paginas e disputava banda com o hero,
    # que e o LCP. A regra passa a valer para a primeira imagem do <main>.
    i = s.find("<main")
    if i < 0:
        i = 0
    s = s[:i] + re.sub(r"<img [^>]*>", repl, s[i:], count=1)
    s = re.sub(r'<img\b[^>]*class="logo-img"[^>]*>', _logo_sem_prioridade, s)

    if path_rel == "index.html" and 'rel="preload" as="image"' not in s:
        # O caminho do preload sai do PROPRIO hero da pagina, nao de uma
        # constante. Estava fixo em hero.webp; quando essa foto saiu do site
        # (21/09/2026, tinha uma colega que nao esta mais na equipe), a
        # constante teria reintroduzido um preload para um arquivo
        # inexistente — o navegador baixaria um 404 com prioridade alta.
        # Preload com media: sem ele o celular baixava o hero de 1600px E a
        # versao -m do <picture> (auditoria 25/09/2026).
        pic = re.search(r'<picture><source media="\(max-width: 767px\)" srcset="\.?/?(assets/images/[^"]+)"[^>]*>'
                        r'<img src="\.?/?(assets/images/[^"]+)"', s)
        hero = re.search(r'<img[^>]+src="\.?/?(assets/images/[^"]+)"[^>]*fetchpriority="high"', s)
        if pic:
            s = s.replace(
                "</head>",
                f'<link rel="preload" as="image" href="/{pic.group(1)}" media="(max-width: 767px)" fetchpriority="high">\n'
                f'<link rel="preload" as="image" href="/{pic.group(2)}" media="(min-width: 768px)" fetchpriority="high">\n</head>',
                1,
            )
        elif hero:
            s = s.replace(
                "</head>",
                f'<link rel="preload" as="image" href="/{hero.group(1)}" fetchpriority="high">\n</head>',
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
                s = add_proof(s, rel)
                s = add_licenca(s, rel)
                s = add_img_text(s, rel)
                s = add_financing(s, rel)
                s = add_faq_items(s, rel)
                s = add_faq_by_page(s, rel)
                s = add_criteria(s, rel)
                s = add_academy_blocks(s, rel)
                s = add_payment_steps(s, rel)
                s = add_breadcrumb_nav(s, rel)
                s = add_byline(s, rel)
                s = fix_descriptions(s, rel)
                s = fix_fresha(s, rel)
                s = add_og(s, dirpath)
                s = enrich_schema(s, rel)
                s = fix_lcp(s, rel)
                s = wrap_tables(s, rel)
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
