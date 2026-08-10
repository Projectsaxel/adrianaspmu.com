#!/usr/bin/env python3
"""Generate static HTML pages from semantic architecture PDF."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from academy_content import academy_body  # noqa: E402
from service_content.nano_brows import nano_brows_sections  # noqa: E402
from service_content.microblading import microblading_sections  # noqa: E402
from service_content.powder_brows import powder_brows_sections  # noqa: E402
from service_content.lip_blush import lip_blush_sections  # noqa: E402
from service_content.dark_lip_neutralization import dark_lip_neutralization_sections  # noqa: E402
from service_content.combination_brows import combination_brows_sections  # noqa: E402
from service_content.nano_combo_brows import nano_combo_brows_sections  # noqa: E402
from service_content.top_eyeliner import top_eyeliner_sections  # noqa: E402
from service_content.smokey_eyeliner import smokey_eyeliner_sections  # noqa: E402
from service_content.bottom_eyeliner import bottom_eyeliner_sections  # noqa: E402
from service_content.eyeliner_combo import eyeliner_combo_sections  # noqa: E402
from service_content.eyebrows_lips_combo import eyebrows_lips_combo_sections  # noqa: E402
from service_content.yearly_touch_up import yearly_touch_up_sections  # noqa: E402

RICH_SERVICE_SECTIONS = {
    "nano-brows": nano_brows_sections,
    "microblading": microblading_sections,
    "powder-brows": powder_brows_sections,
    "lip-blush": lip_blush_sections,
    "dark-lip-neutralization": dark_lip_neutralization_sections,
    "combination-brows": combination_brows_sections,
    "nano-combo": nano_combo_brows_sections,
    "top-eyeliner": top_eyeliner_sections,
    "smokey-eyeliner": smokey_eyeliner_sections,
    "bottom-eyeliner": bottom_eyeliner_sections,
    "eyeliner-combo": eyeliner_combo_sections,
    "eyebrows-lips-combo": eyebrows_lips_combo_sections,
    "yearly-touch-up": yearly_touch_up_sections,
}

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

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet">'


SITE_URL = "https://adrianaspmu.com"


def public_url(rel_path: str) -> str:
    """Final public URL of a generated file: dir pages end with a trailing slash."""
    rel = rel_path.replace("\\", "/")
    if rel == "index.html":
        return f"{SITE_URL}/"
    if rel.endswith("/index.html"):
        return f"{SITE_URL}/{rel[:-len('index.html')]}"
    return f"{SITE_URL}/{rel}"


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


PORTFOLIO_CATEGORIES = [("eyebrows", "Eyebrows"), ("lips", "Lips"), ("eyeliner", "Eyeliner")]


def portfolio_category(filename: str) -> str:
    lowered = filename.lower()
    for slug, _label in PORTFOLIO_CATEGORIES:
        if slug in lowered:
            return slug
    return "other"


def portfolio_filters_html(files) -> str:
    present = [c for c in PORTFOLIO_CATEGORIES if any(portfolio_category(f) == c[0] for f in files)]
    if len(present) < 2:
        return ""
    buttons = ['<button type="button" class="portfolio-filter is-active" data-filter="all" aria-pressed="true">All</button>']
    buttons += [
        f'<button type="button" class="portfolio-filter" data-filter="{slug}" aria-pressed="false">{label}</button>'
        for slug, label in present
    ]
    return (
        '<div class="portfolio-filters" role="group" aria-label="Filter results by category">'
        f'{"".join(buttons)}</div>'
    )


def portfolio_sample(files, limit):
    """Round-robin across categories so every filter has results."""
    buckets = {}
    for fn in files:
        buckets.setdefault(portfolio_category(fn), []).append(fn)
    order = [c for c, _ in PORTFOLIO_CATEGORIES if c in buckets]
    order += [c for c in buckets if c not in order]
    picked, i = [], 0
    while len(picked) < limit and any(i < len(buckets[c]) for c in order):
        for c in order:
            if i < len(buckets[c]) and len(picked) < limit:
                picked.append(buckets[c][i])
        i += 1
    return picked


def portfolio_gallery_html(depth: int, limit=None, filters=False) -> str:
    files = portfolio_files()
    if limit:
        files = portfolio_sample(files, limit) if filters else files[:limit]
    if not files:
        return "<p>Portfolio images loading soon.</p>"
    items = []
    for fn in files:
        alt = portfolio_alt(fn)
        items.append(
            f'<button type="button" class="portfolio-item" data-category="{portfolio_category(fn)}" '
            f'aria-label="View larger: {alt}">'
            f'{img_tag(f"portfolio/{fn}", alt, depth, "portfolio-img")}'
            f"</button>"
        )
    grid = f'<div class="portfolio-grid">{"".join(items)}</div>'
    return f"{portfolio_filters_html(files)}{grid}" if filters else grid


FAVICON = """
  <link rel="icon" href="{base}assets/images/favicon/favicon-32.png" sizes="32x32">
  <link rel="icon" href="{base}assets/images/favicon/favicon-192.png" sizes="192x192">
  <link rel="apple-touch-icon" href="{base}assets/images/favicon/apple-touch-icon.png">
"""


def shell(title, desc, h1, body, depth=0, extra_schema="", breadcrumbs=None, body_class="beauty-site", head_extra=""):
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
  {head_extra}
  {schema_block}
</head>
<body class="{body_class}">
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


def add_canonical(rel_path, content):
    """Insert the self-referencing canonical unless the page declares its own."""
    if 'rel="canonical"' in content:
        return content
    marker = '<meta name="description"'
    i = content.index(marker)
    eol = content.index("\n", i)
    tag = f'\n  <link rel="canonical" href="{public_url(rel_path)}">'
    return content[:eol] + tag + content[eol:]


def write(rel_path, content):
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(add_canonical(rel_path, content), encoding="utf-8")
    print(f"  {rel_path}")


# --- HOME ---
def home_body():
    service_cards = "".join(
        home_category_card(cat) for cat, _title, _slugs in CATEGORY_ORDER
    )
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
        <span class="badge">Women-Owned</span>
        <span class="badge">Wheelchair Accessible</span>
        <span class="badge">4.9 ★ (174 reviews)</span>
      </div>
      <div class="hero-ctas">
        <a class="btn btn-primary" href="contact/">Book Your Consultation</a>
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
    <p class="fact-layer">PMU procedures use single-use sterile needles. Adriana is licensed in Wilmington, MA, Salem, NH, and Peabody, MA — under Town of Wilmington Business Certificate #26-26 and in compliance with Salem NH Body Art Regulations Chapter 433.</p>
  </div>
</section>

<section class="section section-alt section--elegant" id="services">
  <div class="container">
    <p class="section-label section-label--center">Treatments</p>
    <h2 class="heading-centered">What Permanent Makeup Services Do You Offer?</h2>
    <p class="direct-answer">We specialize in permanent makeup for brows, lips, and eyeliner, plus combo packages and yearly touch-ups for existing clients.</p>
    <div class="card-grid">{service_cards}</div>
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
        <a class="btn btn-primary" href="locations/wilmington-ma/">Wilmington Studio</a>
      </article>
      <article class="location-card">
        <span class="tag">New Location</span>
        <h3>Salem, New Hampshire</h3>
        <p><strong>117A Main Street</strong><br>Salem, NH 03079<br><a href="tel:+19782237496">(978) 223-7496</a></p>
        <p>Hours: Mon–Sat 10am–6pm. Serving Salem NH, Derry, Windham, Methuen MA, and Lawrence MA.</p>
        <a class="btn btn-primary" href="locations/salem-nh/">Salem Studio</a>
      </article>
      <article class="location-card">
        <span class="tag">Academy</span>
        <h3>Peabody, Massachusetts</h3>
        <p><strong>39 Cross Street, Suite 206</strong><br>Peabody, MA 01960<br><a href="tel:+17818538063">(781) 853-8063</a></p>
        <p>Adriana's Academy — our training division, where the 100-hour fundamental course, apprenticeship, and VIP masterclass are taught.</p>
        <a class="btn btn-primary" href="academy/">Adriana's Academy</a>
      </article>
    </div>
  </div>
</section>

<section class="section section--elegant" id="reviews">
  <div class="container">
    <p class="section-label section-label--center">Testimonials</p>
    <h2 class="heading-centered">What Our Clients<br>Are Saying</h2>
    <p class="direct-answer heading-centered">We are proud to be a <strong>5-star service</strong> — see verified Google reviews from clients in Wilmington MA, Salem NH, and across New England.</p>
    <div class="reviews-trustindex" id="google-reviews-widget">
      <script defer async src="https://cdn.trustindex.io/loader.js?a8b99d8541280410986623737af"></script>
    </div>
    <noscript>
      <div class="reviews-track">
        <article class="review-card"><div class="review-stars" aria-hidden="true">★★★★★</div><p>This was my first time doing a Nano brow treatment. Adriana was incredible! She was meticulous and made sure I was happy with every step.</p><cite>— Karen G., Google review</cite></article>
        <article class="review-card"><div class="review-stars" aria-hidden="true">★★★★★</div><p>Adriana is so professional — she really takes the time and makes sure you are happy with her work.</p><cite>— Josie G., Google review</cite></article>
        <article class="review-card"><div class="review-stars" aria-hidden="true">★★★★★</div><p>Excellent! Adriana is so precise and takes a lot of care and pride in the finished results of her clients.</p><cite>— Brenda C., Google review</cite></article>
        <article class="review-card"><div class="review-stars" aria-hidden="true">★★★★★</div><p>Livy is wonderful! She did a great job and I am extremely happy with the result.</p><cite>— Julie L., Google review</cite></article>
      </div>
    </noscript>
    <div class="reviews-cta">
      <a class="btn btn-secondary" href="https://www.fresha.com/a/adrianas-permanent-makeup-wilmington-ma-wilmington-211-lowell-street-jalpqett#modal-reviews" target="_blank" rel="noopener noreferrer">Check our reviews on Fresha</a>
      <a class="btn btn-secondary reviews-cta-google" href="https://www.google.com/maps/place/Adriana's+Permanent+Makeup/@42.5388138,-71.1485431,17z/data=!4m8!3m7!1s0x89e30b1334f8bef9:0xe7fa0014b608ddc6!8m2!3d42.5388138!4d-71.1485431!9m1!1b1!16s%2Fg%2F11tm_909cb" target="_blank" rel="noopener noreferrer">
        <span class="reviews-cta-google-icon" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 48 48" fill="currentColor"><path d="M43.48 22.14c-.1-1.02-.96-1.78-1.98-1.78H26.4c-1.1 0-2 .9-2 2v3.42c0 1.1.9 2 2 2h9.02c-.22 1.84-1.42 4.62-4.08 6.48-1.7 1.18-4.02 1.93-6.98 1.93-.14 0-.26 0-.4-.02-5.1-.16-9.42-3.58-10.98-8.28-.42-1.26-.66-2.58-.66-3.94 0-1.36.24-2.7.64-3.94.12-.36.26-.72.42-1.06 1.84-4.14 5.86-7.06 10.58-7.2.12-.02.26-.02.4-.02 2.86 0 5 1.14 6.5 2.18.78.54 1.82.42 2.5-.24l2.78-2.72c.88-.86.8-2.32-.2-3.04-3.18-2.34-7.06-3.72-11.58-3.72-.14 0-.28 0-.4.02-8.66.14-15.24 4.58-18.46 11-.68 2.72-1.46 5.76-1.46 9 0 3.22.78 6.26 2.14 8.98h.02c3.22 6.42 9.8 10.86 17.44 11 .14.02.28.02.4.02 5.4 0 9.94-1.78 13.24-4.84 3.78-3.5 5.96-8.62 5.96-14.72 0-.86-.04-1.6-.12-2.3zM24 11.76c2.12 0 3.74.55 4.64 1.52.98.98 1.32 2.66.82 4.65-.88.96-2.03 1.43-3.46 1.43-2.82 0-4.72-1.74-4.72-4.6 0-2.35 1.34-3.7 3.25-4.47.58-.23 1.26-.35 1.97-.35z"/></svg>
        </span>
        Check more reviews on Google
      </a>
    </div>
  </div>
</section>

<section class="section section-alt section--elegant" id="portfolio-preview">
  <div class="container">
    <p class="section-label section-label--center">Real Results</p>
    <h2 class="heading-centered">Permanent Makeup Before and After Results</h2>
    <p class="direct-answer">Real client results from Nano Brows, Microblading, Lip Blush, and Eyeliner at our Wilmington and Salem studios.</p>
    {portfolio_gallery_html(0, limit=8, filters=True)}
    <p style="margin-top:1.5rem"><a class="btn btn-secondary" href="portfolio/">View full portfolio</a></p>
  </div>
</section>

<section class="section section--elegant section--cta" id="academy">
  <div class="container cta-panel">
    <p class="section-label section-label--center">Academy</p>
    <h2 class="heading-centered">Looking to Become a Permanent Makeup Artist?</h2>
    <p>Adriana's PMU Academy offers 100-hour fundamental training, hands-on apprenticeship, and VIP masterclass at our academy in Peabody, MA.</p>
    <a class="btn btn-primary" href="academy/">Explore Training Programs</a>
  </div>
</section>
"""


# Service definitions for generator
SERVICES = {
    "nano-brows": {"cat": "eyebrows", "name": "Nano Brows", "price": 650,
        "title": "Nano Brows in Wilmington MA & Salem NH | Adriana Beauty Services",
        "h1": "Nano Brows in Wilmington, MA & Salem, NH",
        "desc": "Get natural-looking, long-lasting eyebrows with Nano Brows in Wilmington, MA and Salem, NH. Customized permanent makeup services by Adriana Beauty Services.",
        "answer": "Nano Brows uses an ultra-fine needle and digital machine to create realistic, hair-like strokes for fuller, natural-looking eyebrows that last 1 to 3 years.",
        "rich_content": True,
        "cta_heading": "Book Your Nano Brows Appointment Today",
        "cta_body": "Ready to enjoy beautifully defined brows without the hassle of daily makeup? Schedule your Nano Brows consultation with Adriana Beauty Services – Permanent Makeup and discover how natural, customized brows can enhance your confidence every day.",
        "faqs": [
            ("Are Nano Brows painful?", "Most clients experience minimal discomfort thanks to the use of topical numbing agents throughout the procedure."),
            ("Is Nano Brows better than Microblading?", "Nano Brows is often preferred because it creates highly realistic hair strokes while causing less trauma to the skin."),
            ("How long is the healing process?", "Most clients heal within 4 to 8 weeks, although initial healing occurs much sooner."),
            ("Can Nano Brows be performed on oily skin?", "Yes. Nano Brows is often considered an excellent option for clients with oily skin."),
            ("Will my brows look natural?", "Absolutely. Our goal is to create soft, realistic hair strokes that blend seamlessly with your natural brow hair."),
        ]},
    "microblading": {"cat": "eyebrows", "name": "Microblading", "price": 550,
        "title": "Microblading in Wilmington MA & Salem NH | Natural-Looking Brows",
        "h1": "Microblading in Wilmington, MA & Salem, NH",
        "desc": "Enhance your eyebrows with professional Microblading in Wilmington, MA and Salem, NH. Achieve fuller, natural-looking brows with long-lasting results.",
        "answer": "Microblading uses a handheld tool to create fine, hair-like strokes for fuller, natural-looking brows that typically last 12 to 24 months.",
        "rich_content": True,
        "cta_heading": "Schedule Your Microblading Consultation",
        "cta_lead": "Ready to enjoy fuller, beautifully shaped eyebrows every day?",
        "cta_body": "Book your Microblading consultation with Adriana Beauty Services – Permanent Makeup and discover a customized solution designed to enhance your natural beauty.",
        "faqs": [
            ("Is Microblading painful?", "Most clients report minimal discomfort due to the use of topical numbing products during the procedure."),
            ("How long does Microblading take?", "Appointments typically last between 2 and 3 hours, including consultation and brow design."),
            ("How long is the healing process?", "Most healing occurs within a few weeks, with complete results visible after approximately 4 to 8 weeks."),
            ("Can I wear makeup after Microblading?", "You should avoid applying makeup directly on the treated area until the healing process is complete."),
            ("Will my brows look natural?", "Yes. Our goal is to create realistic hair strokes that blend seamlessly with your natural brows."),
        ]},
    "powder-brows": {"cat": "eyebrows", "name": "Powder Brows", "price": 550,
        "title": "Powder Brows in Wilmington MA & Salem NH | Soft Shaded Brows",
        "h1": "Powder Brows in Wilmington, MA & Salem, NH",
        "desc": "Get beautifully defined Powder Brows in Wilmington, MA and Salem, NH. Enjoy soft, long-lasting, makeup-inspired eyebrows customized for your unique look.",
        "answer": "Powder Brows uses a digital machine to create a soft, shaded brow effect with a polished makeup-like finish that typically lasts 1 to 3 years.",
        "rich_content": True,
        "cta_heading": "Schedule Your Powder Brows Appointment",
        "cta_lead": "Ready to enjoy beautifully defined brows with a soft makeup finish?",
        "cta_body": "Book your Powder Brows consultation with Adriana Beauty Services – Permanent Makeup and discover how effortless beautiful brows can be.",
        "faqs": [
            ("Are Powder Brows painful?", "Most clients experience minimal discomfort thanks to topical numbing products used during the procedure."),
            ("Are Powder Brows better for oily skin?", "Yes. Powder Brows are often recommended for clients with oily skin because the shading technique tends to heal beautifully and retain pigment well."),
            ("How long does the appointment take?", "Most sessions take approximately 2 to 3 hours."),
            ("How long is the healing process?", "Initial healing typically occurs within 1 to 2 weeks, while complete healing may take up to 8 weeks."),
            ("Will my brows look too dark?", "No. Brows will initially appear darker and gradually soften as they heal, resulting in a natural and balanced appearance."),
        ]},
    "lip-blush": {"cat": "lips", "name": "Lip Blush", "price": 550,
        "title": "Lip Blush in Wilmington MA & Salem NH | Permanent Lip Color",
        "h1": "Lip Blush in Wilmington, MA & Salem, NH",
        "desc": "Enhance your natural lip color and definition with Lip Blush in Wilmington, MA and Salem, NH. Enjoy beautiful, long-lasting results and a youthful appearance.",
        "answer": "Lip Blush is a semi-permanent cosmetic tattoo that enhances natural lip color, shape, and definition with a soft, healthy-looking tint that typically lasts 2 to 3 years.",
        "rich_content": True,
        "cta_heading": "Schedule Your Lip Blush Consultation",
        "cta_lead": "Ready to enjoy naturally beautiful lips with long-lasting color and definition?",
        "cta_body": "Book your Lip Blush consultation with Adriana Beauty Services – Permanent Makeup and discover how this advanced treatment can enhance your confidence and simplify your daily beauty routine.",
        "faqs": [
            ("Does Lip Blush make lips look bigger?", "Lip Blush enhances the appearance of the lips by improving color and definition, which can create the illusion of fuller lips."),
            ("Is Lip Blush painful?", "Most clients experience only mild discomfort thanks to the use of topical numbing products."),
            ("How long does the healing process take?", "Initial healing typically occurs within 1 to 2 weeks, while full healing may take up to 8 weeks."),
            ("Can I choose my lip color?", "Yes. We work with you to select a shade that complements your skin tone and desired outcome."),
            ("Will I still need lipstick?", "Many clients find they use significantly less lipstick after Lip Blush because their lips already have enhanced color and definition."),
        ]},
    "combination-brows": {"cat": "eyebrows", "name": "Combination Brows", "price": None,
        "title": "Combination Brows in Wilmington MA & Salem NH | Full Natural Brows",
        "h1": "Combination Brows in Wilmington, MA & Salem, NH",
        "desc": "Get the best of Microblading and Powder Brows with Combination Brows in Wilmington, MA and Salem, NH. Enjoy natural-looking, fuller, beautifully defined eyebrows.",
        "answer": "Combination Brows blends hair-like strokes with soft shading for fuller, natural-looking eyebrows that typically last 1 to 3 years.",
        "rich_content": True,
        "cta_heading": "Schedule Your Combination Brows Consultation",
        "cta_lead": "Ready to achieve fuller, beautifully balanced brows?",
        "cta_body": "Book your Combination Brows consultation with Adriana Beauty Services – Permanent Makeup and discover a customized brow solution designed specifically for you.",
        "faqs": [
            ("What is the difference between Combination Brows and Microblading?", "Microblading uses only hair-like strokes, while Combination Brows combines hair strokes with soft shading for added fullness and definition."),
            ("Are Combination Brows suitable for oily skin?", "Yes. Many clients with oily or combination skin benefit from the added shading component of this technique."),
            ("How long does the appointment take?", "Most Combination Brows appointments take approximately 2 to 3 hours."),
            ("How long does healing take?", "Initial healing typically occurs within 1 to 2 weeks, while full healing may take several weeks."),
            ("Will my brows look natural?", "Absolutely. The combination of realistic hair strokes and soft shading creates a natural yet polished appearance."),
        ]},
    "nano-combo": {"cat": "eyebrows", "name": "Nano Combo Brows", "price": 600,
        "title": "Nano Combo Brows in Wilmington MA & Salem NH | Natural Fuller Brows",
        "h1": "Nano Combo Brows in Wilmington, MA & Salem, NH",
        "desc": "Enhance your brows with Nano Combo Brows in Wilmington, MA and Salem, NH. Combining realistic nano hair strokes and soft shading for beautiful, long-lasting results.",
        "answer": "Nano Combo Brows combine ultra-fine nano hair strokes with soft powder shading for fuller, natural-looking brows that typically last 1 to 3 years.",
        "rich_content": True,
        "cta_heading": "Schedule Your Nano Combo Brows Consultation",
        "cta_lead": "Ready to experience one of the most advanced brow enhancement techniques available?",
        "cta_body": "Book your Nano Combo Brows consultation with Adriana Beauty Services – Permanent Makeup and discover beautifully customized brows designed to complement your natural beauty.",
        "faqs": [
            ("What is the difference between Nano Combo Brows and Combination Brows?", "Nano Combo Brows use machine-created nano hair strokes instead of traditional Microblading strokes, offering greater precision and often gentler treatment of the skin."),
            ("Are Nano Combo Brows suitable for oily skin?", "Yes. Many clients with oily skin experience excellent results with Nano Combo Brows."),
            ("How long does the procedure take?", "Most appointments take approximately 2 to 3 hours."),
            ("Does the procedure hurt?", "Most clients report minimal discomfort due to the use of topical numbing products throughout the treatment."),
            ("Will the results look natural?", "Absolutely. Nano Combo Brows are specifically designed to create realistic hair strokes combined with soft shading for a naturally enhanced appearance."),
        ]},
    "dark-lip-neutralization": {"cat": "lips", "name": "Dark Lip Neutralization", "price": 550,
        "title": "Dark Lip Neutralization in Wilmington MA & Salem NH | Lip Color Correction",
        "h1": "Dark Lip Neutralization in Wilmington, MA & Salem, NH",
        "desc": "Correct uneven or dark lip pigmentation with Dark Lip Neutralization in Wilmington, MA and Salem, NH. Customized permanent makeup treatments for beautiful, balanced lips.",
        "answer": "Dark Lip Neutralization uses advanced color correction to neutralize dark, cool, or uneven lip pigmentation and create a more balanced, natural-looking tone.",
        "rich_content": True,
        "cta_heading": "Schedule Your Dark Lip Neutralization Consultation",
        "cta_lead": "Ready to achieve a more balanced and even lip tone?",
        "cta_body": "Book your consultation with Adriana Beauty Services – Permanent Makeup and learn how Dark Lip Neutralization can help you achieve naturally beautiful, confidence-boosting results.",
        "faqs": [
            ("Can Dark Lip Neutralization completely remove dark pigmentation?", "The goal is to significantly improve and balance pigmentation. Results vary depending on the client's natural lip color and individual characteristics."),
            ("How many sessions will I need?", "Many clients require multiple sessions to achieve optimal results. Your treatment plan will be customized during your consultation."),
            ("Is the procedure painful?", "Most clients experience minimal discomfort thanks to the use of topical numbing products."),
            ("Can I get Lip Blush after neutralization?", "Yes. Many clients choose to undergo Lip Blush after completing the neutralization process."),
            ("How long do the results last?", "Results can last several years depending on lifestyle, skin characteristics, and maintenance."),
        ]},
    "top-eyeliner": {"cat": "eyeliner", "name": "Top Eyeliner", "price": 350,
        "title": "Top Eyeliner in Wilmington MA & Salem NH | Permanent Eyeliner",
        "h1": "Top Eyeliner in Wilmington, MA & Salem, NH",
        "desc": "Enhance your eyes with Top Eyeliner in Wilmington, MA and Salem, NH. Enjoy long-lasting, smudge-proof eyeliner and beautifully defined eyes every day.",
        "answer": "Top Eyeliner is a permanent makeup procedure that defines the upper lash line with long-lasting pigment — from subtle lash enhancement to a polished eyeliner look.",
        "rich_content": True,
        "cta_heading": "Schedule Your Top Eyeliner Consultation",
        "cta_lead": "Ready to enjoy beautifully defined eyes every day without the hassle of applying eyeliner?",
        "cta_body": "Book your Top Eyeliner consultation with Adriana Beauty Services – Permanent Makeup and discover a customized solution designed to enhance your natural beauty.",
        "faqs": [
            ("Will Top Eyeliner look natural?", "Yes. The treatment can be customized from a subtle lash enhancement to a more defined eyeliner look."),
            ("Is the procedure painful?", "Most clients experience minimal discomfort thanks to topical numbing products used throughout the procedure."),
            ("How long does the appointment take?", "Most sessions take approximately 2 to 3 hours."),
            ("How long is the healing process?", "Initial healing typically occurs within one to two weeks, with complete healing taking several weeks."),
            ("Can I still wear makeup?", "Yes. Once the area has fully healed, you may continue using your regular makeup products if desired."),
        ]},
    "smokey-eyeliner": {"cat": "eyeliner", "name": "Smokey Eyeliner", "price": 400,
        "title": "Smokey Eyeliner in Wilmington MA & Salem NH | Permanent Smokey Eyeliner",
        "h1": "Smokey Eyeliner in Wilmington, MA & Salem, NH",
        "desc": "Achieve beautifully defined eyes with Smokey Eyeliner in Wilmington, MA and Salem, NH. Enjoy a soft, blended eyeliner look with long-lasting, smudge-proof results.",
        "answer": "Smokey Eyeliner combines defined upper-lid liner with soft shading for a blended, makeup-inspired effect that lasts for years with proper care.",
        "rich_content": True,
        "cta_heading": "Schedule Your Smokey Eyeliner Consultation",
        "cta_lead": "Ready to wake up with beautifully defined eyes and a soft, elegant eyeliner effect?",
        "cta_body": "Book your Smokey Eyeliner consultation with Adriana Beauty Services – Permanent Makeup and discover a customized treatment designed to enhance your natural beauty.",
        "faqs": [
            ("What is the difference between Smokey Eyeliner and Top Eyeliner?", "Top Eyeliner creates a defined line along the lash line, while Smokey Eyeliner incorporates soft shading for a blended makeup effect."),
            ("Is Smokey Eyeliner permanent?", "Smokey Eyeliner is considered permanent makeup, although touch-ups may be needed over time to maintain optimal results."),
            ("Does the procedure hurt?", "Most clients report minimal discomfort due to the use of topical numbing products throughout the treatment."),
            ("How long does healing take?", "Initial healing typically occurs within one to two weeks, while complete healing may take several weeks."),
            ("Will the result look too dramatic?", "Not at all. The treatment is fully customized and can be designed to create either a subtle enhancement or a more glamorous look."),
        ]},
    "bottom-eyeliner": {"cat": "eyeliner", "name": "Bottom Eyeliner", "price": 250,
        "title": "Bottom Eyeliner in Wilmington MA & Salem NH | Permanent Lower Eyeliner",
        "h1": "Bottom Eyeliner in Wilmington, MA & Salem, NH",
        "desc": "Enhance your eyes with Bottom Eyeliner in Wilmington, MA and Salem, NH. Enjoy subtle, long-lasting lower lash line definition with permanent makeup.",
        "answer": "Bottom Eyeliner places pigment along the lower lash line for subtle, natural-looking definition that lasts for years with proper care.",
        "rich_content": True,
        "cta_heading": "Schedule Your Bottom Eyeliner Consultation",
        "cta_lead": "Ready to enhance your eyes with subtle, long-lasting definition?",
        "cta_body": "Book your Bottom Eyeliner consultation with Adriana Beauty Services – Permanent Makeup and discover how this elegant treatment can simplify your beauty routine while enhancing your natural features.",
        "faqs": [
            ("Will Bottom Eyeliner look natural?", "Yes. The treatment is designed to create subtle enhancement and can be customized according to your preferences."),
            ("Can I get Bottom Eyeliner without Top Eyeliner?", "Absolutely. Bottom Eyeliner can be performed as a standalone treatment or combined with Top Eyeliner."),
            ("Is the procedure painful?", "Most clients experience minimal discomfort due to the use of topical numbing products."),
            ("How long does healing take?", "Initial healing typically occurs within one to two weeks, with complete healing taking several weeks."),
            ("How long do the results last?", "Results often last several years, depending on individual factors and maintenance."),
        ]},
    "eyeliner-combo": {"cat": "eyeliner", "name": "Eyeliner Combo", "price": 500,
        "title": "Eyeliner Combo in Wilmington MA & Salem NH | Permanent Eyeliner",
        "h1": "Eyeliner Combo in Wilmington, MA & Salem, NH",
        "desc": "Get complete eye definition with an Eyeliner Combo in Wilmington, MA and Salem, NH. Permanent upper and lower eyeliner for beautiful, long-lasting results.",
        "answer": "Eyeliner Combo combines Top and Bottom Eyeliner in one session for complete upper and lower lash line definition that lasts for years.",
        "rich_content": True,
        "cta_heading": "Schedule Your Eyeliner Combo Consultation",
        "cta_lead": "Ready to enjoy beautifully defined eyes every day without the hassle of applying eyeliner?",
        "cta_body": "Book your Eyeliner Combo consultation with Adriana Beauty Services – Permanent Makeup and discover a customized solution that enhances your eyes and simplifies your daily beauty routine.",
        "faqs": [
            ("What is included in an Eyeliner Combo?", "The treatment includes both Top Eyeliner and Bottom Eyeliner for complete eye definition."),
            ("Will the eyeliner look natural?", "Yes. The treatment can be customized from very subtle lash enhancement to a more noticeable eyeliner effect."),
            ("Is the procedure painful?", "Most clients experience minimal discomfort due to the use of professional numbing products."),
            ("How long does healing take?", "Initial healing usually occurs within one to two weeks, while complete healing may take several weeks."),
            ("How long do the results last?", "Results often last several years, depending on skin type, lifestyle, and maintenance."),
        ]},
    "eyebrows-lips-combo": {"cat": "combos", "name": "Brows + Lips Combo", "price": 850,
        "title": "Brows + Lips Combo in Wilmington MA & Salem NH | Permanent Makeup Package",
        "h1": "Brows + Lips Combo in Wilmington, MA & Salem, NH",
        "desc": "Transform your look with a Brows + Lips Combo in Wilmington, MA and Salem, NH. Beautiful brows and enhanced lips with customized permanent makeup treatments.",
        "answer": "Brows + Lips Combo pairs a customized brow treatment with lip enhancement in one package for balanced, long-lasting results that typically last 1 to 3 years.",
        "rich_content": True,
        "cta_heading": "Schedule Your Brows + Lips Combo Consultation",
        "cta_lead": "Ready to simplify your beauty routine and enjoy beautiful brows and naturally enhanced lips every day?",
        "cta_body": "Book your Brows + Lips Combo consultation with Adriana Beauty Services – Permanent Makeup and discover a customized treatment plan designed specifically for you.",
        "faqs": [
            ("Which brow treatment is included?", "Your brow treatment will be selected based on your skin type, goals, and desired results during your consultation."),
            ("Can I combine Lip Blush with any brow procedure?", "Yes. Lip Blush can be paired with virtually any brow enhancement service."),
            ("Is the combo more cost-effective than booking separately?", "Many clients find combo treatments provide excellent value while achieving a complete beauty transformation."),
            ("How long does the overall process take?", "Treatment times vary depending on the selected services and may be performed during the same visit or scheduled separately."),
            ("Will the results look natural?", "Absolutely. Every treatment is customized to enhance your natural features while maintaining a balanced and elegant appearance."),
        ]},
    "yearly-touch-up": {"cat": "touch-ups", "name": "Yearly Touch-Up", "price": 300, "priceNote": "from",
        "title": "Yearly Touch-Up in Wilmington MA & Salem NH | Permanent Makeup Maintenance",
        "h1": "Yearly Touch-Up in Wilmington, MA & Salem, NH",
        "desc": "Maintain beautiful brows, lips, and eyeliner with a Yearly Touch-Up in Wilmington, MA and Salem, NH. Refresh your permanent makeup and keep your results looking their best.",
        "answer": "Yearly Touch-Up refreshes faded permanent makeup pigment on brows, lips, or eyeliner — typically scheduled about 12 months after your original procedure.",
        "rich_content": True,
        "cta_heading": "Schedule Your Yearly Touch-Up Appointment",
        "cta_lead": "Ready to refresh your brows, lips, or eyeliner?",
        "cta_body": "Book your Yearly Touch-Up appointment with Adriana Beauty Services – Permanent Makeup and keep your permanent makeup looking vibrant, beautiful, and professionally maintained all year long.",
        "faqs": [
            ("When should I schedule a Yearly Touch-Up?", "Most clients schedule maintenance approximately 12 months after their original procedure, although timing may vary."),
            ("Do I need a touch-up every year?", "Not necessarily. Some clients may retain pigment longer, while others may benefit from more frequent maintenance."),
            ("Is the touch-up procedure shorter than the original appointment?", "Yes. Touch-up appointments are typically shorter because the shape and design are already established."),
            ("Can I make changes during my touch-up?", "Minor adjustments may be possible depending on your existing permanent makeup and desired outcome."),
            ("How long will the refreshed results last?", "Results vary by treatment and individual factors, but regular maintenance helps maximize longevity."),
        ]},
}

CITIES = {
    "wilmington-ma": {"city": "Wilmington", "region": "MA", "loc": "wilmington"},
    "salem-nh": {"city": "Salem", "region": "NH", "loc": "salem"},
}

FRESHA_BOOK_BASE = "https://www.fresha.com/book-now/adrianas-permanent-makeup-zeaseit5"
FRESHA_ALL_OFFER = f"{FRESHA_BOOK_BASE}/all-offer?share=true&pId=727586"
FRESHA_SERVICE_URLS = {
    "yearly-touch-up": f"{FRESHA_BOOK_BASE}/services?oiid=sv%3A18160395&share=true&pId=727586",
    "flash-sale": f"{FRESHA_BOOK_BASE}/services?oiid=sv%3A19707327&share=true&pId=727586",
}


def fresha_book_url(slug):
    return FRESHA_SERVICE_URLS.get(slug, FRESHA_ALL_OFFER)


def fresha_book_btn(slug, label="Book Now", css_class="btn btn-primary"):
    return (
        f'<a class="{css_class}" href="{fresha_book_url(slug)}" '
        f'target="_blank" rel="noopener noreferrer">{label}</a>'
    )

CATEGORY_ORDER = [
    ("eyebrows", "Eyebrow Permanent Makeup", ["nano-brows", "microblading", "powder-brows", "combination-brows", "nano-combo"]),
    ("lips", "Lip Permanent Makeup", ["lip-blush", "dark-lip-neutralization"]),
    ("eyeliner", "Permanent Eyeliner", ["top-eyeliner", "smokey-eyeliner", "bottom-eyeliner", "eyeliner-combo"]),
    ("combos", "Combo Packages", ["eyebrows-lips-combo"]),
    ("touch-ups", "Touch-ups & Maintenance", ["yearly-touch-up"]),
]

HERO_SLUGS = {"nano-brows", "microblading", "powder-brows", "lip-blush"}


def home_service_card(slug):
    info = SERVICES[slug]
    price = info.get("price")
    price_note = info.get("priceNote", "")
    price_html = ""
    if price:
        prefix = "From " if price_note == "from" else ""
        price_html = f'<p class="price">{prefix}${price}</p>'
    url = f'services/{info["cat"]}/{slug}/'
    thumb = img_tag(service_image_path(slug), info["name"], 0, "card-thumb")
    return f"""<article class="card card-has-img">
      <a href="{url}" class="card-img-link">{thumb}</a>
      <h3><a href="{url}">{info["name"]}</a></h3>
      {price_html}
      <p>{info["answer"]}</p>
    </article>"""


CATEGORY_CARDS = {
    "eyebrows": ("Eyebrows", "nano-brows",
                 "Nano Brows, Microblading, Powder Brows and combination techniques, shaped to your natural features."),
    "lips": ("Lips", "lip-blush",
             "Lip Blush and dark lip neutralization for soft, natural color and definition."),
    "eyeliner": ("Eyeliner", "top-eyeliner",
                 "Top, bottom, smokey and combo eyeliner for definition that lasts."),
    "combos": ("Combos", "eyebrows-lips-combo",
               "Bundle brows and lips in one visit and save on the full transformation."),
    "touch-ups": ("Touch-Ups", "yearly-touch-up",
                  "Yearly color refresh to keep existing permanent makeup looking fresh."),
}


def home_category_card(cat):
    label, img_slug, blurb = CATEGORY_CARDS[cat]
    url = f"services/{cat}/"
    thumb = img_tag(service_image_path(img_slug), f"{label} permanent makeup", 0, "card-thumb")
    return f"""<article class="card card-has-img">
      <a href="{url}" class="card-img-link">{thumb}</a>
      <h3><a href="{url}">{label}</a></h3>
      <p>{blurb}</p>
    </article>"""


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
        f'<a href="{info["cat"]}/{slug}/{c}/">{CITIES[c]["city"]}, {CITIES[c]["region"]}</a>'
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
    base = depth_to_base(3)
    if info.get("price"):
        prefix = "From " if info.get("priceNote") == "from" else "Starting at "
        price_html = f'<p class="pricing-badge">{prefix}${info["price"]} USD</p>'
    else:
        price_html = ""
    faq_html = ""
    if info.get("faqs"):
        items = "".join(
            f'<div class="faq-item"><button type="button" aria-expanded="false">{q}</button><div class="faq-answer"><p>{a}</p></div></div>'
            for q, a in info["faqs"])
        faq_html = f'<section class="section section-alt" id="faq"><div class="container"><h2>Frequently Asked Questions</h2><div class="faq-list">{items}</div></div></section>'

    city_btns = "".join(
        f'<a class="btn btn-secondary" href="{c}/">Book in {CITIES[c]["city"]}, {CITIES[c]["region"]}</a>'
        for c in CITIES)

    sections_fn = RICH_SERVICE_SECTIONS.get(slug)
    if info.get("rich_content") and sections_fn:
        middle = sections_fn(base)
    else:
        middle = f"""<section class="section"><div class="container">
  <h2>How Does {info["name"]} Differ from Similar Services?</h2>
  <p class="direct-answer">Each permanent makeup technique is customized to your features. <a href="{base}services/{info["cat"]}/">Explore all {info["cat"]} services</a> or <a href="{base}payment-plan/">view payment plan options</a>.</p>
</div></section>"""

    cta_html = ""
    if info.get("rich_content") and info.get("cta_heading"):
        cta_lead = f'<p>{info["cta_lead"]}</p>' if info.get("cta_lead") else ""
        cta_html = f"""<section class="section section--cta">
  <div class="container cta-panel">
    <h2>{info["cta_heading"]}</h2>
    {cta_lead}
    <p>{info["cta_body"]}</p>
    <div class="city-buttons">{city_btns}</div>
    {fresha_book_btn(slug)}
  </div>
</section>"""

    svc_img = img_tag(service_image_path(slug), info["name"], 3, "service-hero-img")
    body = f"""
<section class="page-hero page-hero--split"><div class="container hero-grid">
  <div>
  <h1>{info["h1"]}</h1>
  <p class="direct-answer">{info["answer"]}</p>
  {price_html}
  <div class="city-buttons">{city_btns}</div>
  {fresha_book_btn(slug)}
  </div>
  <div class="hero-visual">{svc_img}</div>
</div></section>
{middle}
{faq_html}
{cta_html}
"""
    path = f"services/{info['cat']}/{slug}/index.html"
    bc = [("Home", ""), ("Services", "services/"), (info["cat"].title(), f"services/{info['cat']}/"), (info["name"], "")]
    write(path, shell(info.get("title", info["h1"] + " | Adriana's PMU"), info["desc"], info["h1"], body, 3, breadcrumbs=bc))


def city_combo(slug, info, city_slug):
    c = CITIES[city_slug]
    h1 = f'{info["name"]} in {c["city"]}, {c["region"]}'
    body = f"""
<section class="page-hero"><div class="container">
  <h1>{h1}</h1>
  <p class="direct-answer">{info["answer"]} Book at our {c["city"]}, {c["region"]} studio with Master PMU Artist Adriana Souza Santos.</p>
  <p><strong>Address:</strong> See <a href="{depth_to_base(4)}locations/{city_slug}/">{c["city"]} location</a></p>
  {fresha_book_btn(slug, f'Book in {c["city"]}')}
</div></section>
"""
    path = f"services/{info['cat']}/{slug}/{city_slug}/index.html"
    write(path, shell(h1 + " | Adriana's PMU", f'{info["name"]} in {c["city"]} {c["region"]}. Licensed Master PMU Artist.', h1, body, 4))


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
        f'<li><a href="../../services/{SERVICES[s]["cat"]}/{s}/{city_file}/">{SERVICES[s]["name"]} in {city_file.replace("-", " ").title().replace("Ma", "MA").replace("Nh", "NH")}</a></li>'
        for s in ["nano-brows", "microblading", "powder-brows", "lip-blush"])
    body = f'<section class="page-hero"><div class="container">{tag}<h1>{h1}</h1><p>{street}<br><a href="tel:{phone.replace("(","").replace(")","").replace(" ","").replace("-","")}">{phone}</a></p><p>Serving {area}.</p><ul>{svc_links}</ul></div></section>'
    write(f"locations/{city_file}/index.html", shell(h1, h1, h1, body, 2))

write("locations/index.html", shell(
    "Locations | Wilmington MA & Salem NH",
    "Two permanent makeup studio locations in New England.",
    "Adriana's Permanent Makeup Locations",
    '<section class="page-hero"><div class="container"><h1>Adriana\'s Permanent Makeup Locations: Wilmington MA & Salem NH</h1></div></section>'
    + '<section class="section"><div class="container location-grid">'
    + '<article class="location-card"><h3><a href="wilmington-ma/">Wilmington, MA</a></h3></article>'
    + '<article class="location-card"><h3><a href="salem-nh/">Salem, NH</a></h3></article></div></section>',
    1))

# Academy / Training hub (content from adrianaspmu.com/training/)
ACADEMY_META = (
    "Learn permanent makeup at Adriana's Academy in Peabody, MA. "
    "AAM-certified 100-hour fundamental training, apprenticeship, hands-on models, "
    "and Diamond Certified Trainer."
)
academy_html = academy_body(img_tag, 1)
write("academy/index.html", shell(
    "Training | Adriana's PMU Academy Massachusetts",
    ACADEMY_META,
    "Learn the Art of Permanent Makeup",
    academy_html,
    1,
    body_class="beauty-site academy-page",
))
write("training/index.html", shell(
    "Training - Adriana's PMU Academy",
    ACADEMY_META,
    "Learn the Art of Permanent Makeup",
    academy_body(img_tag, 1, course_href_base="../academy/"),
    1,
    body_class="beauty-site academy-page",
    head_extra='<link rel="canonical" href="https://adrianaspmu.com/academy/">',
))

for course, title, price, desc in [
    ("pmu-100h-fundamental", "100-Hour Fundamental Permanent Makeup Training", "$7,000", "100 hours in-person covering Nano Brows, Microblading, Powder Brows, Lip Blush, and Eyeliner."),
    ("pmu-apprenticeship", "Permanent Makeup Apprenticeship", "$700/month", "Hands-on apprenticeship at Wilmington MA studio."),
    ("vip-masterclass", "VIP Permanent Makeup Masterclass", "Contact for pricing", "Custom advanced training for experienced artists."),
]:
    acad_img = {"pmu-100h-fundamental": "academy/pmu-100h.jpg", "pmu-apprenticeship": "academy/apprenticeship.jpg"}.get(course)
    img_block = f'<div class="hero-visual">{img_tag(acad_img, title, 2, "service-hero-img")}</div>' if acad_img else ""
    write(f"academy/{course}/index.html", shell(title, desc, title,
        f'<section class="page-hero page-hero--split"><div class="container hero-grid"><div><h1>{title}</h1><p class="pricing-badge">{price}</p><p>{desc}</p><a class="btn btn-primary" href="../../contact/">Apply Now</a></div>{img_block}</div></section>', 2))

# Support pages
write("about/index.html", shell(
    "About Adriana Souza Santos | Master PMU Artist",
    "20+ years, 5,000+ procedures, founder of Adriana's PMU and Academy.",
    "About Adriana Souza Santos: Master Permanent Makeup Artist",
    f"""<section class="page-hero page-hero--split"><div class="container hero-grid">
    <div><h1>About Adriana Souza Santos</h1>
    <p class="direct-answer">Master Permanent Makeup Artist with 20+ years of experience and 5,000+ procedures performed. Founder of Adriana's PMU and educator since 2017.</p>
    <p class="fact-layer">Licensed under Town of Wilmington Business Certificate #26-26. Women-owned business. LGBTQ+ friendly.</p></div>
    <div class="hero-visual">{img_tag("about-adriana.jpg", "Adriana Souza Santos — Master Permanent Makeup Artist", 1, "hero-img")}</div>
    </div></section>""", 1))

write("contact/index.html", shell(
    "Contact | Book Permanent Makeup Wilmington MA & Salem NH",
    "Book consultation or contact both studio locations.",
    "Contact Adriana's Permanent Makeup",
    """<section class="page-hero"><div class="container"><h1>Contact Adriana's Permanent Makeup</h1></div></section>
    <section class="section"><div class="container" style="max-width:560px">
    <form id="contact-form">
      <p class="form-note"><span class="req" aria-hidden="true">*</span> Required fields</p>
      <div class="form-group"><label for="name">Name <span class="req" aria-hidden="true">*</span></label><input id="name" name="name" required></div>
      <div class="form-group"><label for="email">Email <span class="req" aria-hidden="true">*</span></label><input id="email" name="email" type="email" required></div>
      <div class="form-group"><label for="phone">Phone <span class="req" aria-hidden="true">*</span></label><input id="phone" name="phone" type="tel" autocomplete="tel" placeholder="(781) 555-0123" required></div>
      <div class="form-group"><label for="location">Preferred location</label>
        <select id="location" name="location"><option>Wilmington, MA</option><option>Salem, NH</option></select></div>
      <div class="form-group"><label for="message">Message</label><textarea id="message" name="message"></textarea></div>
      <button class="btn btn-primary" type="submit">Send Message</button>
      <p class="form-message" hidden role="status"></p>
    </form>
    <p style="margin-top:2rem">Wilmington: <a href="tel:+17818538063">(781) 853-8063</a> · Salem: <a href="tel:+19782237496">(978) 223-7496</a></p>
    </div></section>""", 1))

write("faq/index.html", shell(
    "Permanent Makeup FAQ | Brows, Lips, Eyeliner",
    "Answers to common permanent makeup questions.",
    "Permanent Makeup FAQ",
    """<section class="page-hero"><div class="container"><h1>Permanent Makeup FAQ</h1></div></section>
    <section class="section"><div class="container"><div class="faq-list">
    <div class="faq-item"><button type="button">How much does permanent makeup cost?</button><div class="faq-answer"><p>Nano Brows from $650, Microblading and Powder Brows from $550, Lip Blush from $550. See individual service pages for details.</p></div></div>
    <div class="faq-item"><button type="button">Does insurance cover PMU?</button><div class="faq-answer"><p>Permanent makeup is cosmetic and not covered by insurance.</p></div></div>
    <div class="faq-item"><button type="button">Is permanent makeup safe?</button><div class="faq-answer"><p>Yes, when performed by a licensed Master Artist using sterile single-use needles in a compliant studio.</p></div></div>
    </div></div></section>""", 1))

write("portfolio/index.html", shell("Portfolio | Before & After PMU", "Real client permanent makeup results.", "Permanent Makeup Before & After Results",
    f'<section class="page-hero"><div class="container"><h1>Permanent Makeup Before & After Results</h1>'
    f'<p class="direct-answer">Real Nano Brows, Microblading, Lip Blush, and Eyeliner results from Adriana\'s PMU studios.</p></div></section>'
    f'<section class="section"><div class="container">{portfolio_gallery_html(1, filters=True)}</div></section>', 1))

write("payment-plan/index.html", shell("Payment Plan | PMU Financing MA & NH", "Financing options for permanent makeup.", "Payment Plan for Permanent Makeup",
    '<section class="page-hero"><div class="container"><h1>Payment Plan for Permanent Makeup Services</h1><p>Flexible payment options available. <a href="../contact/">Contact us</a> for details.</p></div></section>', 1))


def flash_sale_body(depth=1):
    base = depth_to_base(depth)
    img = img_tag("flash-sale.jpg", "Holiday Flash Sale — Brows or Lips PMU for $349", depth, "service-hero-img")
    return f"""
<section class="page-hero page-hero--split">
  <div class="container hero-grid">
    <div>
      <h1>Flash Sale $349!</h1>
      <p class="direct-answer">It's the most beautiful time of the year — and our Holiday Flash Sale is here! Get your Brows or Lips PMU for only <strong>$349</strong>, but hurry… spots melt away like snowflakes!</p>
      <p class="pricing-note">*Limited slots available – Book yours before they fill up!</p>
      <a class="btn btn-primary" href="{fresha_book_url("flash-sale")}" target="_blank" rel="noopener noreferrer">Book Now</a>
    </div>
    <div class="hero-visual">{img}</div>
  </div>
</section>
<section class="section">
  <div class="container container--narrow">
    <h2>Permanent Makeup Techniques</h2>
    <p>Permanent Makeup is more than beauty — it's freedom. Imagine waking up every day with brows and lips already enhanced, saving time and boosting your confidence instantly.</p>
    <p>More than 5,000 procedures performed by Master PMU Artist Adriana Souza Santos.</p>
  </div>
</section>
<section class="section section-alt">
  <div class="container">
    <div class="card-grid">
      <article class="card">
        <h3>Eyebrows</h3>
        <p>Nano Brows, Microblading, Powder Brows, and combination techniques.</p>
        <a class="btn btn-secondary" href="{base}services/eyebrows/">Explore Brow Services</a>
      </article>
      <article class="card">
        <h3>Lips</h3>
        <p>Lip Blush and Dark Lip Neutralization for natural, lasting color.</p>
        <a class="btn btn-secondary" href="{base}services/lips/">Explore Lip Services</a>
      </article>
    </div>
  </div>
</section>
<section class="section section--cta">
  <div class="container cta-panel">
    <h2>Ready to book your $349 Flash Sale?</h2>
    <p>Wilmington MA and Salem NH — limited appointments available.</p>
    <a class="btn btn-primary" href="{fresha_book_url("flash-sale")}" target="_blank" rel="noopener noreferrer">Book Now on Fresha</a>
    <p style="margin-top:1rem"><a href="{base}contact/">Contact us</a> with questions.</p>
  </div>
</section>"""


write("flash-sale/index.html", shell(
    "Flash Sale $349 | Brows or Lips PMU | Adriana's PMU",
    "Holiday Flash Sale — get Brows or Lips PMU for only $349. Limited slots at Wilmington MA and Salem NH.",
    "Flash Sale $349",
    flash_sale_body(1),
    1,
    breadcrumbs=[("Home", ""), ("Flash Sale", "flash-sale/")],
))

write("privacy-policy/index.html", shell("Privacy Policy", "Privacy policy.", "Privacy Policy",
    '<section class="section"><div class="container"><h1>Privacy Policy</h1><p>Content to be finalized before publish.</p></div></section>', 1))

write("terms-of-use/index.html", shell("Terms of Use", "Terms of use.", "Terms of Use",
    '<section class="section"><div class="container"><h1>Terms of Use</h1><p>Content to be finalized before publish.</p></div></section>', 1))

write("index.html", shell(
    "Permanent Makeup Studio & Academy | Wilmington MA & Salem NH | Adriana's PMU",
    "Master PMU Artist with 20+ years, 5,000+ procedures. Nano Brows, Microblading, Lip Blush in Wilmington MA & Salem NH. Book consultation.",
    "Permanent Makeup Studio and Academy in Wilmington, MA & Salem, NH",
    home_body(), 0))

def sitemap_meta(rel_path: str) -> tuple[str, str]:
    if rel_path == "index.html":
        return "1.0", "weekly"
    if rel_path.startswith("flash-sale/"):
        return "0.9", "weekly"
    if rel_path in ("services/index.html", "locations/index.html"):
        return "0.9", "monthly"
    if rel_path.endswith("/wilmington-ma/index.html") or rel_path.endswith("/salem-nh/index.html"):
        return "0.85", "monthly"
    if rel_path in ("privacy-policy/index.html", "terms-of-use/index.html"):
        return "0.3", "yearly"
    return "0.8", "monthly"


def write_sitemap():
    pages = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.html"))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in pages:
        priority, changefreq = sitemap_meta(page)
        loc = public_url(page)
        lines.append(
            f"  <url><loc>{loc}</loc>"
            f"<priority>{priority}</priority>"
            f"<changefreq>{changefreq}</changefreq></url>"
        )
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  sitemap.xml")


def write_robots():
    content = f"""# robots.txt for adrianaspmu.com
User-agent: *
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Disallow: /scripts/

# LLM site summary: {SITE_URL}/llms.txt
Sitemap: {SITE_URL}/sitemap.xml
"""
    (ROOT / "robots.txt").write_text(content, encoding="utf-8")
    print("  robots.txt")


def service_price_label(info: dict) -> str:
    price = info.get("price")
    if not price:
        return "custom pricing"
    prefix = "from " if info.get("priceNote") == "from" else ""
    return f"{prefix}${price}"


def write_llms():
    service_lines = []
    for _cat, title, slugs in CATEGORY_ORDER:
        service_lines.append(f"## {title}")
        for slug in slugs:
            info = SERVICES[slug]
            url = public_url(f"services/{info['cat']}/{slug}/index.html")
            summary = info["answer"][:140].rstrip().rstrip(".") + "."
            service_lines.append(
                f"- [{info['name']}]({url}): {summary} ({service_price_label(info)})"
            )
        service_lines.append("")

    content = f"""# Adriana's Permanent Makeup
> Master Permanent Makeup Artist Adriana Souza Santos with 20+ years of experience and 5,000+ procedures performed. PMU studio and academy serving Wilmington, MA and Salem, NH (New England). Site language: English (en-US) only. Book appointments via Fresha: {FRESHA_ALL_OFFER}

## Core Pages
- [Home]({SITE_URL}/): Permanent Makeup Studio and Academy in Wilmington MA & Salem NH
- [About]({SITE_URL}/about/): Master PMU Artist with 20+ years and 5,000+ procedures
- [Services]({SITE_URL}/services/): All permanent makeup services in MA and NH
- [Locations]({SITE_URL}/locations/): Wilmington MA + Salem NH studios
- [Academy]({SITE_URL}/academy/): Permanent Makeup training programs
- [Training]({SITE_URL}/training/): Academy hub (mirror of /academy/)
- [Contact]({SITE_URL}/contact/): Studio contact and consultation
- [FAQ]({SITE_URL}/faq/): Permanent makeup frequently asked questions
- [Portfolio]({SITE_URL}/portfolio/): Before and after PMU results
- [Flash Sale]({SITE_URL}/flash-sale/): Limited-time brows or lips PMU for $349
- [Privacy Policy]({SITE_URL}/privacy-policy/)
- [Terms of Use]({SITE_URL}/terms-of-use/)

{chr(10).join(service_lines)}
## Locations
- [Wilmington MA]({SITE_URL}/locations/wilmington-ma/): 211 Lowell Street, Suite F — (781) 853-8063
- [Salem NH]({SITE_URL}/locations/salem-nh/): 117A Main Street — (978) 223-7496

## Academy
- [100-Hour Fundamental]({SITE_URL}/academy/pmu-100h-fundamental/): $7,000 in-person training
- [Apprenticeship]({SITE_URL}/academy/pmu-apprenticeship/): $700/month hands-on program
- [VIP Masterclass]({SITE_URL}/academy/vip-masterclass/): Advanced training for experienced artists

## Booking
- Fresha (all services): {FRESHA_ALL_OFFER}
- Yearly Touch-Up: {fresha_book_url("yearly-touch-up")}
- Flash Sale ($349): {fresha_book_url("flash-sale")}

## Trust & Credentials
- Licensed: Town of Wilmington Business Certificate #26-26
- Salem NH: Compliant with Body Art Regulations Chapter 433
- 4.9 stars, 174 Google reviews; 1,000+ combined reviews (Google + Fresha)
- Women-owned, LGBTQ+ friendly, wheelchair accessible (Wilmington)
- Email: info@adrianaspmu.com
"""
    (ROOT / "llms.txt").write_text(content, encoding="utf-8")
    print("  llms.txt")


write_sitemap()
write_robots()
write_llms()

print("Done.")
