#!/usr/bin/env python3
"""Generate static HTML pages from semantic architecture PDF."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ORG_SCHEMA = """{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://adrianaspmu.com/#organization",
      "name": "Adriana Beauty Services, Inc.",
      "legalName": "Adriana Beauty Services, Inc.",
      "alternateName": ["Adriana's Permanent Makeup", "Adriana's PMU"],
      "url": "https://adrianaspmu.com/",
      "foundingDate": "2017",
      "sameAs": [
        "https://www.facebook.com/adrianaspmu",
        "https://www.instagram.com/adrianas_pmu/",
        "https://maps.app.goo.gl/oJRNewzwwWACAera6"
      ],
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.9",
        "reviewCount": "174",
        "bestRating": "5"
      }
    },
    {
      "@type": "BeautySalon",
      "@id": "https://adrianaspmu.com/#wilmington",
      "name": "Adriana's Permanent Makeup, Wilmington MA",
      "additionalType": "https://schema.org/HealthAndBeautyBusiness",
      "telephone": "+1-781-853-8063",
      "priceRange": "$$ to $$$",
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "211 Lowell Street, Suite F",
        "addressLocality": "Wilmington",
        "addressRegion": "MA",
        "postalCode": "01887",
        "addressCountry": "US"
      },
      "geo": {"@type": "GeoCoordinates", "latitude": 42.539192, "longitude": -71.148805},
      "openingHoursSpecification": {
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],
        "opens": "10:00",
        "closes": "18:00"
      }
    }
  ]
}"""

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">'


def depth_to_base(depth: int) -> str:
    return "../" * depth if depth else "./"


ASSETS = ROOT / "assets" / "images"


def img_src(path: str, depth: int = 0) -> str:
    return f"{depth_to_base(depth)}assets/images/{path}"


def img_tag(path: str, alt: str, depth: int = 0, css_class: str = "") -> str:
    cls = f' class="{css_class}"' if css_class else ""
    return (
        f'<img src="{img_src(path, depth)}" alt="{alt}" loading="lazy" decoding="async"{cls}>'
    )


def service_image_path(slug: str) -> str:
    p = ASSETS / "services" / f"{slug}.jpg"
    return f"services/{slug}.jpg" if p.exists() else "hero.webp"


def portfolio_files():
    folder = ASSETS / "portfolio"
    if not folder.is_dir():
        return []
    return sorted(f.name for f in folder.glob("*.jpg"))


def portfolio_alt(filename: str) -> str:
    name = filename.replace("Portfolio-", "").replace(".jpg", "").replace("-", " ")
    return f"Permanent makeup before and after — {name}"


def portfolio_gallery_html(depth: int, limit=None) -> str:
    files = portfolio_files()
    if limit:
        files = files[:limit]
    if not files:
        return "<p>Portfolio images loading soon.</p>"
    items = []
    for fn in files:
        items.append(
            f'<figure class="portfolio-item">'
            f'{img_tag(f"portfolio/{fn}", portfolio_alt(fn), depth, "portfolio-img")}'
            f"</figure>"
        )
    return f'<div class="portfolio-grid">{"".join(items)}</div>'


FAVICON = """
  <link rel="icon" href="{base}assets/images/favicon/favicon-32.png" sizes="32x32">
  <link rel="icon" href="{base}assets/images/favicon/favicon-192.png" sizes="192x192">
  <link rel="apple-touch-icon" href="{base}assets/images/favicon/apple-touch-icon.png">
"""


def shell(title, desc, h1, body, depth=0, extra_schema="", breadcrumbs=None):
    base = depth_to_base(depth)
    css = f"{base}css/styles.css"
    favicon = FAVICON.format(base=base)
    bc = ""
    if breadcrumbs:
        items = "".join(
            f'<li><a href="{base}{href}">{label}</a></li>' if i < len(breadcrumbs) - 1
            else f'<li aria-current="page">{label}</li>'
            for i, (label, href) in enumerate(breadcrumbs)
        )
        bc = f'<nav class="breadcrumb container" aria-label="Breadcrumb"><ol>{items}</ol></nav>'

    schema_block = f'<script type="application/ld+json">{ORG_SCHEMA}</script>'
    if extra_schema:
        schema_block += f'\n<script type="application/ld+json">{extra_schema}</script>'

    return f"""<!DOCTYPE html>
<html lang="en-US" data-base="{base}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="stylesheet" href="{css}">
  {favicon}
  {FONTS}
  {schema_block}
</head>
<body class="beauty-site">
  <a class="skip-link" href="#main">Skip to content</a>
  <div id="site-header"></div>
  {bc}
  <main id="main">
    {body}
  </main>
  <div id="site-footer"></div>
  <script src="{base}js/site-config.js"></script>
  <script src="{base}js/main.js"></script>
</body>
</html>"""


def write(rel_path, content):
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {rel_path}")


# --- HOME ---
def home_body():
    hero_cards = ""
    for slug, href, label in [
        ("nano-brows", "services/eyebrows/nano-brows/", "Nano Brows"),
        ("microblading", "services/eyebrows/microblading/", "Microblading"),
        ("powder-brows", "services/eyebrows/powder-brows/", "Powder Brows"),
        ("lip-blush", "services/lips/lip-blush/", "Lip Blush"),
    ]:
        hero_cards += f"""<article class="card card-has-img">
        <a href="{href}" class="card-img-link">{img_tag(service_image_path(slug), label, 0, "card-thumb")}</a>
        <h3><a href="{href}">{label}</a></h3>
      </article>"""
    return f"""
<section class="hero hero--premium">
  <div class="hero-bg-accent" aria-hidden="true"></div>
  <div class="container hero-grid">
    <div class="hero-content">
      <p class="section-label">Master PMU Artist · Wilmington MA &amp; Salem NH</p>
      <h1>Permanent Makeup Studio and Academy in Wilmington, MA &amp; Salem, NH</h1>
      <p class="direct-answer">Master Permanent Makeup Artist Adriana Souza Santos with 20+ years and 5,000+ procedures. Nano Brows, Microblading, Lip Blush, and Eyeliner at two New England locations.</p>
      <div class="hero-badges">
        <span class="badge">Licensed PMU Artist</span>
        <span class="badge">LGBTQ+ Friendly</span>
        <span class="badge">Women-Owned</span>
        <span class="badge">Wheelchair Accessible</span>
        <span class="badge">4.9 ★ (174 reviews)</span>
      </div>
      <div class="hero-ctas">
        <a class="btn btn-primary" href="contact.html">Book Your Consultation ($50)</a>
        <a class="btn btn-secondary" href="services/">Explore Services</a>
      </div>
    </div>
    <div class="hero-visual hero-visual--framed">
      {img_tag("hero.webp", "Adriana's Permanent Makeup studio — Master PMU Artist in Wilmington MA and Salem NH", 0, "hero-img")}
      <div class="hero-visual-badge" aria-hidden="true">20+ Years · 5,000+ Procedures</div>
    </div>
  </div>
</section>

<section class="trust-bar" aria-label="Studio credentials">
  <div class="container trust-bar-inner">
    <div class="trust-item"><span class="trust-value">4.9★</span><span class="trust-key">Google Reviews</span></div>
    <div class="trust-divider" aria-hidden="true"></div>
    <div class="trust-item"><span class="trust-value">5,000+</span><span class="trust-key">Procedures</span></div>
    <div class="trust-divider" aria-hidden="true"></div>
    <div class="trust-item"><span class="trust-value">2</span><span class="trust-key">New England Studios</span></div>
    <div class="trust-divider" aria-hidden="true"></div>
    <div class="trust-item"><span class="trust-value">Licensed</span><span class="trust-key">MA &amp; NH</span></div>
  </div>
</section>

<section class="section section--elegant" id="what-is-pmu">
  <div class="container container--narrow">
    <p class="section-label section-label--center">The Art of Effortless Beauty</p>
    <h2 class="heading-centered">What Is Permanent Makeup?</h2>
    <p class="direct-answer">Permanent makeup, also called cosmetic tattooing or micropigmentation, places color pigment beneath the skin to enhance brows, lips, or eyeliner. Results last 1 to 3 years and save time on daily makeup.</p>
    <p class="fact-layer">PMU procedures use single-use sterile needles. Adriana's studio is licensed under Town of Wilmington Business Certificate #26-26 and complies with Salem NH Body Art Regulations Chapter 433.</p>
  </div>
</section>

<section class="section section-alt section--elegant" id="services">
  <div class="container">
    <p class="section-label section-label--center">Treatments</p>
    <h2 class="heading-centered">What Permanent Makeup Services Do You Offer?</h2>
    <p class="direct-answer">We specialize in permanent makeup for brows, lips, and eyeliner, plus combo packages and yearly touch-ups for existing clients.</p>
    <div class="card-grid">{hero_cards}
      <article class="card card-has-img">
        <a href="services/eyeliner/top-eyeliner/" class="card-img-link">{img_tag(service_image_path("top-eyeliner"), "Permanent eyeliner PMU", 0, "card-thumb")}</a>
        <h3><a href="services/eyeliner/">Eyeliner PMU</a></h3>
        <p>Top, Smokey, Bottom, and full eyeliner combo packages</p>
      </article>
      <article class="card card-has-img">
        <a href="services/combos/eyebrows-lips-combo/" class="card-img-link">{img_tag(service_image_path("eyebrows-lips-combo"), "Brows and lips combo PMU", 0, "card-thumb")}</a>
        <h3><a href="services/combos/">Combo Packages</a></h3>
        <p class="price">From $850</p>
        <a class="btn btn-secondary" href="services/combos/eyebrows-lips-combo/">Brows + Lips Combo</a>
      </article>
    </div>
  </div>
</section>

<section class="section section--elegant" id="why-us">
  <div class="container">
    <p class="section-label section-label--center">Why Adriana's</p>
    <h2 class="heading-centered">Why Choose Adriana's PMU for Permanent Makeup?</h2>
    <p class="direct-answer">Master PMU Artist Adriana Souza Santos creates natural-looking results fully customized to each client's facial features—never a one-size-fits-all approach.</p>
    <div class="stats-grid">
      <div><span class="stat-number">20+</span><span class="stat-label">Years experience</span></div>
      <div><span class="stat-number">5,000+</span><span class="stat-label">Procedures</span></div>
      <div><span class="stat-number">1,000+</span><span class="stat-label">Combined reviews</span></div>
      <div><span class="stat-number">4.9</span><span class="stat-label">Google rating</span></div>
    </div>
  </div>
</section>

<section class="section section-alt section--elegant" id="locations">
  <div class="container">
    <p class="section-label section-label--center">Visit Us</p>
    <h2 class="heading-centered">Where Are Adriana's PMU Locations?</h2>
    <div class="location-grid">
      <article class="location-card">
        <h3>Wilmington, Massachusetts</h3>
        <p><strong>211 Lowell Street, Suite F</strong><br>Wilmington, MA 01887<br><a href="tel:+17818538063">(781) 853-8063</a></p>
        <p>Hours: Mon–Sat 10am–6pm. Serving Wilmington, Reading, Andover, North Andover, and the Boston North Shore.</p>
        <a class="btn btn-primary" href="locations/wilmington-ma.html">Wilmington Studio</a>
      </article>
      <article class="location-card">
        <span class="tag">New Location</span>
        <h3>Salem, New Hampshire</h3>
        <p><strong>117A Main Street</strong><br>Salem, NH 03079<br><a href="tel:+19782237496">(978) 223-7496</a></p>
        <p>Hours: Mon–Sat 10am–6pm. Serving Salem NH, Derry, Windham, Methuen MA, and Lawrence MA.</p>
        <a class="btn btn-primary" href="locations/salem-nh.html">Salem Studio</a>
      </article>
    </div>
  </div>
</section>

<section class="section section--elegant" id="reviews">
  <div class="container">
    <p class="section-label section-label--center">Testimonials</p>
    <h2 class="heading-centered">What Do Clients Say About Adriana's PMU?</h2>
    <div class="reviews-track">
      <article class="review-card"><div class="review-stars">★★★★★</div><p>"Natural brows that look like my own hair. Adriana listened to exactly what I wanted."</p><cite>— Client, Wilmington MA</cite></article>
      <article class="review-card"><div class="review-stars">★★★★★</div><p>"Professional, clean studio and beautiful lip blush results. Worth every penny."</p><cite>— Client, North Shore MA</cite></article>
      <article class="review-card"><div class="review-stars">★★★★★</div><p>"20 years of experience shows. Custom shape and color—not a template."</p><cite>— Client, Andover MA</cite></article>
    </div>
    <p style="margin-top:1.5rem"><a href="https://maps.app.goo.gl/oJRNewzwwWACAera6" rel="noopener">Read 174+ Google reviews</a> · <a href="portfolio.html">View full portfolio</a></p>
  </div>
</section>

<section class="section section-alt section--elegant" id="portfolio-preview">
  <div class="container">
    <p class="section-label section-label--center">Real Results</p>
    <h2 class="heading-centered">Permanent Makeup Before and After Results</h2>
    <p class="direct-answer">Real client results from Nano Brows, Microblading, Lip Blush, and Eyeliner at our Wilmington and Salem studios.</p>
    {portfolio_gallery_html(0, limit=8)}
    <p style="margin-top:1.5rem"><a class="btn btn-secondary" href="portfolio.html">View full portfolio</a></p>
  </div>
</section>

<section class="section section--elegant section--cta" id="academy">
  <div class="container cta-panel">
    <p class="section-label section-label--center">Academy</p>
    <h2 class="heading-centered">Looking to Become a Permanent Makeup Artist?</h2>
    <p>Adriana's PMU Academy offers 100-hour fundamental training, hands-on apprenticeship, and VIP masterclass at our Wilmington MA studio.</p>
    <a class="btn btn-primary" href="academy/">Explore Training Programs</a>
  </div>
</section>
"""


write("index.html", shell(
    "Permanent Makeup Studio & Academy | Wilmington MA & Salem NH | Adriana's PMU",
    "Master PMU Artist with 20+ years, 5,000+ procedures. Nano Brows, Microblading, Lip Blush in Wilmington MA & Salem NH. Book consultation.",
    "Permanent Makeup Studio and Academy in Wilmington, MA & Salem, NH",
    home_body(), 0))

# Service definitions for generator
SERVICES = {
    "nano-brows": {"cat": "eyebrows", "name": "Nano Brows", "price": 650,
        "h1": "Nano Brows in Massachusetts & New Hampshire",
        "desc": "Hyperrealistic hair-like strokes. $650 by Master PMU Artist in Wilmington MA & Salem NH.",
        "answer": "Nano Brows is a permanent makeup technique that uses an ultra-fine needle to create hyperrealistic, hair-like strokes for natural eyebrows. Results last 1 to 3 years.",
        "faqs": [
            ("How much do Nano Brows cost?", "Nano Brows costs $650 USD for the initial session, including a perfection touch-up at 6-8 weeks. Yearly maintenance starts at $300."),
            ("Does Nano Brows hurt?", "A topical anesthetic minimizes discomfort. Most clients describe mild scratching, not pain."),
            ("How long does Nano Brows last?", "Nano Brows typically last 1 to 3 years depending on skin type and aftercare."),
        ]},
    "microblading": {"cat": "eyebrows", "name": "Microblading", "price": 550,
        "h1": "Microblading in Massachusetts & New Hampshire",
        "desc": "Natural hair-stroke eyebrow tattoo. $550 in Wilmington MA & Salem NH by licensed Master Artist.",
        "answer": "Microblading creates natural hair-stroke eyebrows using a manual technique. Results last 1 to 3 years with proper aftercare.",
        "faqs": [
            ("How much is microblading?", "Microblading at Adriana's PMU costs $550 USD for the initial session."),
            ("Does microblading look natural?", "Yes—when performed by a Master Artist with customized mapping and color matching."),
        ]},
    "powder-brows": {"cat": "eyebrows", "name": "Powder Brows", "price": 550,
        "h1": "Powder Brows & Ombre Shading in MA & NH",
        "desc": "Soft defined ombre brows including microshading. $550 in Wilmington & Salem.",
        "answer": "Powder Brows (ombre shading) creates soft, makeup-ready eyebrow definition. Ideal for oily or mature skin.",
        "faqs": [("Powder brows vs microblading?", "Powder brows use shading; microblading uses hair strokes. Powder often retains better on oily skin.")]},
    "lip-blush": {"cat": "lips", "name": "Lip Blush", "price": 550,
        "h1": "Lip Blush in Massachusetts & New Hampshire",
        "desc": "Soft natural lip color lasting 2-3 years. $550 in Wilmington MA & Salem NH.",
        "answer": "Lip Blush adds soft, natural lip color customized to your skin tone. Results last 2 to 3 years.",
        "faqs": [("Lip blush for dark lips?", "We offer Dark Lip Neutralization for hyperpigmented lips before or alongside lip blush.")]},
    "combination-brows": {"cat": "eyebrows", "name": "Combination Brows", "price": None,
        "h1": "Combination Brows in MA & NH", "desc": "Hair strokes plus soft shading.", "answer": "Combination brows blend hair strokes with soft shading.", "faqs": []},
    "nano-combo": {"cat": "eyebrows", "name": "Nano Combo Brows", "price": 600,
        "h1": "Nano Combo Brows in MA & NH", "desc": "Nano strokes with soft shading. $600.", "answer": "Nano Combo combines nano hair strokes with soft shading.", "faqs": []},
    "dark-lip-neutralization": {"cat": "lips", "name": "Dark Lip Neutralization", "price": 550,
        "h1": "Dark Lip Neutralization in MA & NH", "desc": "Color correction for dark or hyperpigmented lips.", "answer": "Dark lip neutralization corrects uneven lip tone before lip blush.", "faqs": []},
    "top-eyeliner": {"cat": "eyeliner", "name": "Top Eyeliner", "price": 350,
        "h1": "Top Permanent Eyeliner in MA & NH", "desc": "Classic and cat eye styles. $350.", "answer": "Top permanent eyeliner defines the upper lash line in classic or cat eye styles.", "faqs": []},
    "smokey-eyeliner": {"cat": "eyeliner", "name": "Smokey Eyeliner", "price": 400,
        "h1": "Smokey Permanent Eyeliner in MA & NH", "desc": "Soft diffused shadow effect. $400.", "answer": "Smokey permanent eyeliner creates a soft, diffused upper-lid effect.", "faqs": []},
    "bottom-eyeliner": {"cat": "eyeliner", "name": "Bottom Eyeliner", "price": 250,
        "h1": "Bottom Permanent Eyeliner in MA & NH", "desc": "Subtle lower lash line. $250.", "answer": "Bottom permanent eyeliner subtly defines the lower lash line.", "faqs": []},
    "eyeliner-combo": {"cat": "eyeliner", "name": "Eyeliner Combo", "price": 500,
        "h1": "Permanent Eyeliner Combo in MA & NH", "desc": "Top + bottom. $500.", "answer": "Eyeliner combo includes top and bottom permanent eyeliner in one session.", "faqs": []},
    "eyebrows-lips-combo": {"cat": "combos", "name": "Brows + Lips Combo", "price": 850,
        "h1": "Brows + Lips Combo PMU in MA & NH", "desc": "Eyebrow PMU and lip blush together. $850.", "answer": "Combine eyebrow permanent makeup and lip blush in one session and save versus booking separately.", "faqs": []},
    "yearly-touch-up": {"cat": "touch-ups", "name": "Yearly Touch-Up", "price": 300, "priceNote": "from",
        "h1": "Yearly PMU Touch-Up for Brows in MA & NH", "desc": "Color refresh from $300.", "answer": "Yearly touch-ups refresh brow color for existing Adriana's PMU clients.", "faqs": []},
}

CITIES = {
    "wilmington-ma": {"city": "Wilmington", "region": "MA", "loc": "wilmington"},
    "salem-nh": {"city": "Salem", "region": "NH", "loc": "salem"},
}

CATEGORY_ORDER = [
    ("eyebrows", "Eyebrow Permanent Makeup", ["nano-brows", "microblading", "powder-brows", "combination-brows", "nano-combo"]),
    ("lips", "Lip Permanent Makeup", ["lip-blush", "dark-lip-neutralization"]),
    ("eyeliner", "Permanent Eyeliner", ["top-eyeliner", "smokey-eyeliner", "bottom-eyeliner", "eyeliner-combo"]),
    ("combos", "Combo Packages", ["eyebrows-lips-combo"]),
    ("touch-ups", "Touch-ups & Maintenance", ["yearly-touch-up"]),
]

HERO_SLUGS = {"nano-brows", "microblading", "powder-brows", "lip-blush"}


def service_hub_card(slug):
    info = SERVICES[slug]
    price = info.get("price")
    price_note = info.get("priceNote", "")
    price_html = ""
    if price:
        prefix = "from " if price_note else ""
        price_html = f'<p class="price">{prefix}${price}</p>'
    hero_badge = '<span class="badge">Hero service</span>' if slug in HERO_SLUGS else ""
    url = f'{info["cat"]}/{slug}/'
    loc_links = " · ".join(
        f'<a href="{info["cat"]}/{slug}/{c}.html">{CITIES[c]["city"]}, {CITIES[c]["region"]}</a>'
        for c in CITIES
    )
    thumb = img_tag(service_image_path(slug), info["name"], 1, "card-thumb")
    return f"""<article class="card card-has-img">
      <a href="{url}" class="card-img-link">{thumb}</a>
      {hero_badge}
      <h3><a href="{url}">{info["name"]}</a></h3>
      <p>{info["answer"]}</p>
      {price_html}
      <div class="card-links">
        <a href="{url}">Service details</a> · {loc_links}
      </div>
    </article>"""


def services_hub_body():
    intro = """<section class="page-hero"><div class="container">
      <h1>Permanent Makeup Services in Massachusetts and New Hampshire</h1>
      <p class="direct-answer">Browse every permanent makeup service at Adriana's PMU—brows, lips, eyeliner, combo packages, and touch-ups—available in Wilmington, MA and Salem, NH.</p>
    </div></section>"""
    blocks = []
    for _cat, title, slugs in CATEGORY_ORDER:
        cards = "".join(service_hub_card(s) for s in slugs)
        blocks.append(
            f'<section class="section section-alt"><div class="container">'
            f'<h2>{title}</h2>'
            f'<p class="section-intro"><a href="{_cat}/">Browse {_cat.replace("-", " ")} category</a></p>'
            f'<div class="card-grid">{cards}</div></div></section>'
        )
    return intro + "".join(blocks)


def service_page(slug, info):
    price_html = f'<p class="pricing-badge">Starting at ${info["price"]} USD</p>' if info.get("price") else ""
    faq_html = ""
    if info.get("faqs"):
        items = "".join(
            f'<div class="faq-item"><button type="button" aria-expanded="false">{q}</button><div class="faq-answer"><p>{a}</p></div></div>'
            for q, a in info["faqs"])
        faq_html = f'<section class="section section-alt"><div class="container"><h2>Frequently Asked Questions</h2><div class="faq-list">{items}</div></div></section>'

    city_btns = "".join(
        f'<a class="btn btn-secondary" href="{c}.html">Book in {CITIES[c]["city"]}, {CITIES[c]["region"]}</a>'
        for c in CITIES)

    svc_img = img_tag(service_image_path(slug), info["name"], 3, "service-hero-img")
    body = f"""
<section class="page-hero page-hero--split"><div class="container hero-grid">
  <div>
  <h1>{info["h1"]}</h1>
  <p class="direct-answer">{info["answer"]}</p>
  {price_html}
  <div class="city-buttons">{city_btns}</div>
  <a class="btn btn-primary" href="{depth_to_base(3)}contact.html">Book Consultation ($50)</a>
  </div>
  <div class="hero-visual">{svc_img}</div>
</div></section>
<section class="section"><div class="container">
  <h2>How Does {info["name"]} Differ from Similar Services?</h2>
  <p class="direct-answer">Each permanent makeup technique is customized to your features. <a href="{depth_to_base(3)}services/{info["cat"]}/">Explore all {info["cat"]} services</a> or <a href="{depth_to_base(3)}payment-plan.html">view payment plan options</a>.</p>
</div></section>
{faq_html}
"""
    path = f"services/{info['cat']}/{slug}/index.html"
    bc = [("Home", ""), ("Services", "services/"), (info["cat"].title(), f"services/{info['cat']}/"), (info["name"], "")]
    write(path, shell(info["h1"] + " | Adriana's PMU", info["desc"], info["h1"], body, 3, breadcrumbs=bc))


def city_combo(slug, info, city_slug):
    c = CITIES[city_slug]
    h1 = f'{info["name"]} in {c["city"]}, {c["region"]}'
    body = f"""
<section class="page-hero"><div class="container">
  <h1>{h1}</h1>
  <p class="direct-answer">{info["answer"]} Book at our {c["city"]}, {c["region"]} studio with Master PMU Artist Adriana Souza Santos.</p>
  <p><strong>Address:</strong> See <a href="{depth_to_base(3)}locations/{city_slug}.html">{c["city"]} location</a></p>
  <a class="btn btn-primary" href="{depth_to_base(3)}contact.html">Book in {c["city"]}</a>
</div></section>
"""
    path = f"services/{info['cat']}/{slug}/{city_slug}.html"
    write(path, shell(h1 + " | Adriana's PMU", f'{info["name"]} in {c["city"]} {c["region"]}. Licensed Master PMU Artist.', h1, body, 3))


print("Generating pages...")
for slug, info in SERVICES.items():
    service_page(slug, info)
    for city in CITIES:
        city_combo(slug, info, city)

# Category hubs
for cat, title, items in CATEGORY_ORDER:
    cards = "".join(
        f'<article class="card card-has-img"><a href="{s}/" class="card-img-link">'
        f'{img_tag(service_image_path(s), SERVICES[s]["name"], 2, "card-thumb")}</a>'
        f'<h3><a href="{s}/">{SERVICES[s]["name"]}</a></h3><p>{SERVICES[s]["answer"][:120]}...</p></article>'
        for s in items)
    body = f'<section class="page-hero"><div class="container"><h1>{title}</h1><p class="direct-answer">Professional {title.lower()} in Wilmington MA and Salem NH.</p></div></section><section class="section"><div class="container"><div class="card-grid">{cards}</div></div></section>'
    write(f"services/{cat}/index.html", shell(title + " | Adriana's PMU", title, title, body, 2))

write("services/index.html", shell(
    "Permanent Makeup Services in MA & NH | Adriana's PMU",
    "All permanent makeup services: Nano Brows, Microblading, Lip Blush, Eyeliner, combos and touch-ups in Wilmington MA & Salem NH.",
    "Permanent Makeup Services in Massachusetts and New Hampshire",
    services_hub_body(),
    1))

# Locations
for city_file, h1, street, phone, area, tag in [
    ("wilmington-ma", "Adriana's Permanent Makeup Studio in Wilmington, MA", "211 Lowell Street, Suite F, Wilmington, MA 01887", "(781) 853-8063",
     "Wilmington, Reading, Andover, North Andover, Lowell, and the I-93 corridor", ""),
    ("salem-nh", "Adriana's Permanent Makeup Studio in Salem, NH", "117A Main Street, Salem, NH 03079", "(978) 223-7496",
     "Salem NH, Derry, Windham, Methuen MA, Lawrence MA", '<span class="tag">New Location</span>'),
]:
    svc_links = "".join(
        f'<li><a href="../services/{SERVICES[s]["cat"]}/{s}/{city_file}.html">{SERVICES[s]["name"]} in {city_file.replace("-", " ").title().replace("Ma", "MA").replace("Nh", "NH")}</a></li>'
        for s in ["nano-brows", "microblading", "powder-brows", "lip-blush"])
    body = f'<section class="page-hero"><div class="container">{tag}<h1>{h1}</h1><p>{street}<br><a href="tel:{phone.replace("(","").replace(")","").replace(" ","").replace("-","")}">{phone}</a></p><p>Serving {area}.</p><ul>{svc_links}</ul></div></section>'
    write(f"locations/{city_file}.html", shell(h1, h1, h1, body, 1))

write("locations/index.html", shell(
    "Locations | Wilmington MA & Salem NH",
    "Two permanent makeup studio locations in New England.",
    "Adriana's Permanent Makeup Locations",
    '<section class="page-hero"><div class="container"><h1>Adriana\'s Permanent Makeup Locations: Wilmington MA & Salem NH</h1></div></section>'
    + '<section class="section"><div class="container location-grid">'
    + '<article class="location-card"><h3><a href="wilmington-ma.html">Wilmington, MA</a></h3></article>'
    + '<article class="location-card"><h3><a href="salem-nh.html">Salem, NH</a></h3></article></div></section>',
    1))

# Academy
write("academy/index.html", shell(
    "PMU Academy | Permanent Makeup Training Massachusetts",
    "100-hour fundamental class, apprenticeship, VIP masterclass.",
    "Adriana's PMU Academy: Permanent Makeup Training in Massachusetts",
    f"""<section class="page-hero"><div class="container"><h1>Adriana's PMU Academy</h1>
    <p class="direct-answer">Train with a Master Artist who has taught since 2017.</p></div></section>
    <section class="section"><div class="container card-grid">
    <article class="card card-has-img"><a href="pmu-100h-fundamental.html" class="card-img-link">{img_tag("academy/pmu-100h.jpg", "100-hour PMU training class", 1, "card-thumb")}</a>
    <h3><a href="pmu-100h-fundamental.html">100-Hour Fundamental</a></h3><p class="price">$7,000</p><p>In-person professional PMU training.</p></article>
    <article class="card card-has-img"><a href="pmu-apprenticeship.html" class="card-img-link">{img_tag("academy/apprenticeship.jpg", "PMU apprenticeship program", 1, "card-thumb")}</a>
    <h3><a href="pmu-apprenticeship.html">Apprenticeship</a></h3><p class="price">$700/month</p><p>Hands-on apprenticeship program.</p></article>
    <article class="card"><h3><a href="vip-masterclass.html">VIP Masterclass</a></h3><p>Custom advanced training by request.</p></article>
    </div></section>""", 1))

for course, title, price, desc in [
    ("pmu-100h-fundamental", "100-Hour Fundamental Permanent Makeup Training", "$7,000", "100 hours in-person covering Nano Brows, Microblading, Powder Brows, Lip Blush, and Eyeliner."),
    ("pmu-apprenticeship", "Permanent Makeup Apprenticeship", "$700/month", "Hands-on apprenticeship at Wilmington MA studio."),
    ("vip-masterclass", "VIP Permanent Makeup Masterclass", "Contact for pricing", "Custom advanced training for experienced artists."),
]:
    acad_img = {"pmu-100h-fundamental": "academy/pmu-100h.jpg", "pmu-apprenticeship": "academy/apprenticeship.jpg"}.get(course)
    img_block = f'<div class="hero-visual">{img_tag(acad_img, title, 1, "service-hero-img")}</div>' if acad_img else ""
    write(f"academy/{course}.html", shell(title, desc, title,
        f'<section class="page-hero page-hero--split"><div class="container hero-grid"><div><h1>{title}</h1><p class="pricing-badge">{price}</p><p>{desc}</p><a class="btn btn-primary" href="../contact.html">Apply Now</a></div>{img_block}</div></section>', 1))

# Support pages
write("about.html", shell(
    "About Adriana Souza Santos | Master PMU Artist",
    "20+ years, 5,000+ procedures, founder of Adriana's PMU and Academy.",
    "About Adriana Souza Santos: Master Permanent Makeup Artist",
    f"""<section class="page-hero page-hero--split"><div class="container hero-grid">
    <div><h1>About Adriana Souza Santos</h1>
    <p class="direct-answer">Master Permanent Makeup Artist with 20+ years of experience and 5,000+ procedures performed. Founder of Adriana's PMU and educator since 2017.</p>
    <p class="fact-layer">Licensed under Town of Wilmington Business Certificate #26-26. Women-owned business. LGBTQ+ friendly.</p></div>
    <div class="hero-visual">{img_tag("about-adriana.jpg", "Adriana Souza Santos — Master Permanent Makeup Artist", 0, "hero-img")}</div>
    </div></section>""", 0))

write("contact.html", shell(
    "Contact | Book Permanent Makeup Wilmington MA & Salem NH",
    "Book consultation or contact both studio locations.",
    "Contact Adriana's Permanent Makeup",
    """<section class="page-hero"><div class="container"><h1>Contact Adriana's Permanent Makeup</h1></div></section>
    <section class="section"><div class="container" style="max-width:560px">
    <form id="contact-form">
      <div class="form-group"><label for="name">Name</label><input id="name" name="name" required></div>
      <div class="form-group"><label for="email">Email</label><input id="email" name="email" type="email" required></div>
      <div class="form-group"><label for="location">Preferred location</label>
        <select id="location" name="location"><option>Wilmington, MA</option><option>Salem, NH</option></select></div>
      <div class="form-group"><label for="message">Message</label><textarea id="message" name="message"></textarea></div>
      <button class="btn btn-primary" type="submit">Send Message</button>
      <p class="form-message" hidden role="status"></p>
    </form>
    <p style="margin-top:2rem">Wilmington: <a href="tel:+17818538063">(781) 853-8063</a> · Salem: <a href="tel:+19782237496">(978) 223-7496</a></p>
    </div></section>""", 0))

write("faq.html", shell(
    "Permanent Makeup FAQ | Brows, Lips, Eyeliner",
    "Answers to common permanent makeup questions.",
    "Permanent Makeup FAQ",
    """<section class="page-hero"><div class="container"><h1>Permanent Makeup FAQ</h1></div></section>
    <section class="section"><div class="container faq-list">
    <div class="faq-item"><button type="button">How much does permanent makeup cost?</button><div class="faq-answer"><p>Nano Brows from $650, Microblading and Powder Brows from $550, Lip Blush from $550. See individual service pages for details.</p></div></div>
    <div class="faq-item"><button type="button">Does insurance cover PMU?</button><div class="faq-answer"><p>Permanent makeup is cosmetic and not covered by insurance.</p></div></div>
    <div class="faq-item"><button type="button">Is permanent makeup safe?</button><div class="faq-answer"><p>Yes, when performed by a licensed Master Artist using sterile single-use needles in a compliant studio.</p></div></div>
    </div></section>""", 0))

write("portfolio.html", shell("Portfolio | Before & After PMU", "Real client permanent makeup results.", "Permanent Makeup Before & After Results",
    f'<section class="page-hero"><div class="container"><h1>Permanent Makeup Before & After Results</h1>'
    f'<p class="direct-answer">Real Nano Brows, Microblading, Lip Blush, and Eyeliner results from Adriana\'s PMU studios.</p></div></section>'
    f'<section class="section"><div class="container">{portfolio_gallery_html(0)}</div></section>', 0))

write("payment-plan.html", shell("Payment Plan | PMU Financing MA & NH", "Financing options for permanent makeup.", "Payment Plan for Permanent Makeup",
    '<section class="page-hero"><div class="container"><h1>Payment Plan for Permanent Makeup Services</h1><p>Flexible payment options available. <a href="contact.html">Contact us</a> for details.</p></div></section>', 0))

write("privacy-policy.html", shell("Privacy Policy", "Privacy policy.", "Privacy Policy",
    '<section class="section"><div class="container"><h1>Privacy Policy</h1><p>Content to be finalized before publish.</p></div></section>', 0))

write("terms-of-use.html", shell("Terms of Use", "Terms of use.", "Terms of Use",
    '<section class="section"><div class="container"><h1>Terms of Use</h1><p>Content to be finalized before publish.</p></div></section>', 0))

print("Done.")
