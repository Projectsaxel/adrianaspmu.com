"""Avaliacoes do Google para o site: normaliza e escolhe o que cada pagina mostra.

Usado por scripts/fetch_reviews.py (a cada 3 dias, no GitHub Actions) e pelo
enrich_pages.py (no build). A escolha acontece UMA vez, aqui, e vai pronta no
JSON: o build e o navegador so leem `selection`, entao os dois mostram sempre
as mesmas avaliacoes.

Regras (decididas em 25/09/2026):
- so 5 estrelas, com texto de pelo menos MIN_CHARS caracteres
- a avaliacao tem de citar o servico da pagina (palavras em SERVICES)
- fora as que elogiam quem saiu da equipe (EX_TEAM)
- avaliacao traduzida pelo Google: so a parte em ingles
- nome publicado como "Nicole M." (primeiro nome + inicial)
- nada disto vira schema Review/aggregateRating (self-serving reviews)
"""
import re
from datetime import datetime

MIN_CHARS = 60
PER_PAGE = 3

UNITS = {
    "wilmington": {
        "place_id": "ChIJ-b74NBML44kRxt0IthQA-uc",
        "label": "Wilmington, MA",
        "maps": "https://maps.google.com/?cid=16715673055892397510",
    },
    "salem": {
        "place_id": "ChIJP3ROK2Gr44kRV733kmg5pHM",
        "label": "Salem, NH",
        "maps": "https://maps.google.com/?cid=8332848331847351639",
    },
}

# servico (slug da URL) -> palavras que a avaliacao precisa conter
SERVICES = {
    "nano-brows": [r"\bnano ?brows?\b", r"\bnano\b(?! ?combo)"],
    "nano-combo": [r"\bnano ?combo\b", r"\bcombo brows?\b"],
    "microblading": [r"\bmicrobladi?n?g?\w*\b"],
    "powder-brows": [r"\bpowder\b", r"\bombr[eé]\b", r"\bshading\b"],
    "combination-brows": [r"\bmicroshading\b", r"\bcombination\b", r"\bmicroblading and shading\b"],
    "eyebrows": [r"\bbrows?\b", r"\beyebrows?\b", r"\bmicroblad\w*\b"],
    "lip-blush": [r"\blip ?blush\b", r"\blips?\b", r"\blip (?:tint|micropigmentation)\b"],
    "dark-lip-neutralization": [r"\bneutrali[sz]\w*\b", r"\bdark lips?\b", r"\bdiscolou?ration\b"],
    "lips": [r"\blips?\b", r"\blip blush\b", r"\bneutrali[sz]\w*\b"],
    "eyeliner": [r"\beye ?liner\b", r"\blash line\b"],
    "top-eyeliner": [r"\beye ?liner\b"],
    "bottom-eyeliner": [r"\beye ?liner\b"],
    "smokey-eyeliner": [r"\beye ?liner\b", r"\bsmok\w*\b"],
    "eyeliner-combo": [r"\beye ?liner\b"],
    "eyebrows-lips-combo": [r"\b(?:brows?|eyebrows?)\b.*\blips?\b|\blips?\b.*\b(?:brows?|eyebrows?)\b"],
    "combos": [r"\b(?:brows?|eyebrows?)\b.*\blips?\b|\blips?\b.*\b(?:brows?|eyebrows?)\b"],
    "touch-ups": [r"\btouch[- ]?ups?\b", r"\brefresh\w*\b"],
    "yearly-touch-up": [r"\btouch[- ]?ups?\b", r"\brefresh\w*\b"],
    "_any": [r"."],
}

EX_TEAM = re.compile(r"\b(ludi|stella)\b", re.I)


def short_name(full):
    parts = [p for p in re.split(r"\s+", (full or "").strip()) if p]
    if not parts:
        return "Google reviewer"
    first = parts[0].strip("“”\"'").capitalize()
    if len(parts) == 1:
        return first
    last = re.sub(r"[^A-Za-zÀ-ÿ]", "", parts[-1])
    return f"{first} {last[:1].upper()}." if last else first


def english_text(comment):
    if not comment:
        return ""
    t = comment
    if t.startswith("(Translated by Google)"):
        t = t[len("(Translated by Google)"):]
        t = t.split("(Original)")[0]
    return re.sub(r"\s+", " ", t).strip()


def normalize(unit, raw):
    """Review cru da API do Local Falcon -> registro publicavel."""
    text = english_text(raw.get("comment"))
    date = (raw.get("date_created") or "")[:10]
    try:
        month = datetime.strptime(date, "%Y-%m-%d").strftime("%B %Y")
    except ValueError:
        month = ""
    return {
        "id": raw.get("review_id"),
        "unit": unit,
        "name": short_name(raw.get("reviewer")),
        "rating": int(raw.get("rating") or 0),
        "text": text,
        "date": date,
        "month": month,
        "source": "google",
    }


def publishable(r):
    return r["rating"] == 5 and len(r["text"]) >= MIN_CHARS and not EX_TEAM.search(r["text"])


# Palavras FORTES: a avaliacao que cita o nome exato do servico vem antes
# da que so cita a regiao ("lips", "brows"). As listas de SERVICES viram o
# nivel fraco quando o servico tem nivel forte aqui.
STRONG = {
    "lip-blush": [r"\blip ?blush\b", r"\blip (?:tint\w*|micropigmentation)\b", r"\blips? (?:tinted|colou?r)\b"],
    "yearly-touch-up": [r"\btouch[- ]?ups?\b"],
    "touch-ups": [r"\btouch[- ]?ups?\b"],
    "nano-brows": [r"\bnano ?brows?\b"],
    "powder-brows": [r"\bpowder brows?\b", r"\bombr[eé]\b"],
    "top-eyeliner": [r"\b(?:top|upper|classic|winged?|cat) (?:eye ?)?liner\b"],
    "bottom-eyeliner": [r"\b(?:bottom|lower) (?:eye ?)?liner\b", r"\bupper and lower\b"],
    "smokey-eyeliner": [r"\bsmok\w* (?:eye ?)?liner\b"],
    "eyeliner-combo": [r"\bupper and lower\b", r"\beyeliner combo\b"],
}
# o que NAO pode aparecer para contar como aquele servico
EXCLUDE = {
    "lip-blush": [r"\bneutrali[sz]\w*\b"],
}


def _tier(r, service):
    """0 = cita o servico pelo nome, 1 = so a regiao, None = nao serve."""
    t = r["text"]
    if any(re.search(p, t, re.I) for p in EXCLUDE.get(service, [])) and not any(
            re.search(p, t, re.I) for p in STRONG.get(service, [])):
        return None
    if any(re.search(p, t, re.I) for p in STRONG.get(service, [])):
        return 0
    if any(re.search(p, t, re.I) for p in SERVICES.get(service, SERVICES["_any"])):
        return 1
    return None


def pick(reviews, service, unit=None, n=PER_PAGE):
    """Cita o servico pelo nome primeiro, depois mais recentes. Pagina de
    cidade: primeiro a propria unidade; se faltar, completa com a outra (o
    card diz de qual unidade e)."""
    ok = []
    for r in reviews:
        if not publishable(r):
            continue
        t = _tier(r, service)
        if t is not None:
            ok.append((t, r))
    ok.sort(key=lambda x: x[1]["date"], reverse=True)
    ok.sort(key=lambda x: x[0])
    ok = [r for _, r in ok]
    if unit:
        own = [r for r in ok if r["unit"] == unit]
        other = [r for r in ok if r["unit"] != unit]
        ok = own + other
    return [r["id"] for r in ok[:n]]


def build(units_raw, updated_iso, fresha_raw=None):
    """units_raw: {"wilmington": {"total":..,"average":..,"reviews":[raw,..]}, ...}"""
    out = {"updated": updated_iso, "units": {}, "reviews": {}, "selection": {}}
    allr = []
    for unit, info in units_raw.items():
        meta = UNITS[unit]
        out["units"][unit] = {
            "label": meta["label"],
            "maps": meta["maps"],
            "rating": round(float(info.get("average") or 0), 1),
            "total": int(info.get("total") or 0),
        }
        for raw in info.get("reviews", []):
            r = normalize(unit, raw)
            if publishable(r):
                out["reviews"][r["id"]] = r
                allr.append(r)
    for service in SERVICES:
        if service == "_any":
            continue
        out["selection"][service] = {
            "all": pick(allr, service),
            "wilmington": pick(allr, service, "wilmington"),
            "salem": pick(allr, service, "salem"),
        }
    out["selection"]["_any"] = {
        "all": pick(allr, "_any"),
        "wilmington": pick(allr, "_any", "wilmington"),
        "salem": pick(allr, "_any", "salem"),
    }
    fr = []
    for unit, html in (fresha_raw or {}).items():
        for r in fresha_reviews(unit, html):
            out["reviews"][r["id"]] = r
            fr.append(r)
    out["selection"]["_home"] = {"all": pick_home([r for r in allr if publishable(r)], fr)}
    return out

# ---------------------------------------------------------------------------
# Fresha (24/10/2026, pedido do Pablo): a home mostra as avaliacoes mais
# recentes do Google E do Fresha num carrossel. O Fresha publica as avaliacoes
# da pagina de cada unidade como JSON-LD (schema.org Review) no proprio HTML:
# autor, data, texto e nota. So entram 5 estrelas, em ingles, com as mesmas
# regras do Google (MIN_CHARS, EX_TEAM).
# ---------------------------------------------------------------------------
FRESHA_URLS = {
    "wilmington": "https://www.fresha.com/a/adrianas-permanent-makeup-wilmington-ma-wilmington-211-lowell-street-jalpqett",
    "salem": "https://www.fresha.com/a/adrianas-permanent-makeup-salem-nh-salem-eua-117a-main-street-w0he16uu",
}
HOME_N = 12

_EN = re.compile(r"\b(the|and|is|was|my|she|her|very|with|to|for|so|i|it|this|of|love|great|amazing)\b", re.I)
_NOT_EN = re.compile(r"\b(que|muy|es|ella|una|el|los|las|muito|ela|uma|não|com|para|excelente|todo|mis|meu|minha)\b", re.I)


def is_english(text):
    return len(_EN.findall(text)) > 2 * len(_NOT_EN.findall(text))


def fresha_reviews(unit, html):
    """HTML da pagina da unidade no Fresha -> registros publicaveis."""
    import hashlib
    import json as _json
    out = []
    for blob in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = _json.loads(blob)
        except ValueError:
            continue
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, dict):
                if x.get("@type") == "Review" and x.get("reviewBody"):
                    text = re.sub(r"\s+", " ", x["reviewBody"]).strip()
                    date = (x.get("datePublished") or "")[:10]
                    try:
                        month = datetime.strptime(date, "%Y-%m-%d").strftime("%B %Y")
                    except ValueError:
                        month = ""
                    name = ((x.get("author") or {}).get("name") or "").strip()
                    out.append({
                        "id": "fresha-" + hashlib.sha1((name + date + text).encode()).hexdigest()[:16],
                        "unit": unit,
                        "name": short_name(name) if name else "Fresha client",
                        "rating": int(float((x.get("reviewRating") or {}).get("ratingValue") or 0)),
                        "text": text,
                        "date": date,
                        "month": month,
                        "source": "fresha",
                    })
                else:
                    stack.extend(x.values())
    return [r for r in out if publishable(r) and is_english(r["text"])]


def _key(r):
    return re.sub(r"[^a-z]", "", r["text"].lower())[:40]


def pick_home(google, fresha, n=HOME_N):
    """As mais recentes de cada fonte, metade e metade, intercaladas por data.
    Sem repetir a mesma avaliacao publicada nas duas fontes."""
    seen, g, f = set(), [], []
    for src, dst in ((sorted(google, key=lambda r: r["date"], reverse=True), g),
                     (sorted(fresha, key=lambda r: r["date"], reverse=True), f)):
        for r in src:
            if _key(r) in seen:
                continue
            seen.add(_key(r))
            dst.append(r)
    # a mesma cliente costuma avaliar nas duas com textos diferentes:
    # mesmo nome com ate 7 dias de diferenca conta como a mesma avaliacao
    def _d(x):
        try:
            return datetime.strptime(x, "%Y-%m-%d")
        except ValueError:
            return None
    gd = [(r["name"], _d(r["date"])) for r in g]
    f = [r for r in f if not any(nm == r["name"] and dt and _d(r["date"]) and abs((dt - _d(r["date"])).days) <= 7
                                for nm, dt in gd)]
    # Rachel (24/10): sempre alternado, um do Google e um do Fresha, 6 de cada.
    # Comeca pela fonte da avaliacao mais recente. Se uma fonte tiver menos
    # de n/2, a outra completa no fim.
    half = n // 2
    g, f = g[:half], f[:half]
    ordem = [g, f] if (g and (not f or g[0]["date"] >= f[0]["date"])) else [f, g]
    out = []
    for i in range(half):
        for fonte in ordem:
            if i < len(fonte):
                out.append(fonte[i])
    return [r["id"] for r in out[:n]]



# Card da home no formato da "caixinha" do Google (pedido do Pablo, 24/10):
# avatar colorido com a inicial, nome e data em cima, o simbolo da origem no
# canto, estrelas amarelas. O main.js monta exatamente o mesmo HTML.
AVATAR = ["#1a73e8", "#e8710a", "#188038", "#d93025", "#9334e6", "#12b5cb", "#c5221f", "#b06000"]
G_SVG = ('<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>'
         '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>'
         '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>'
         '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>')


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def home_card_html(r, units, clone=False):
    name = r.get("name") or "Client"
    color = AVATAR[sum(map(ord, name)) % len(AVATAR)]
    try:
        nice = datetime.strptime(r.get("date", ""), "%Y-%m-%d").strftime("%b %d, %Y").replace(" 0", " ")
    except ValueError:
        nice = r.get("month", "")
    src = r.get("source", "google")
    badge = (f'<span class="rv-src rv-src--google" title="Google review">{G_SVG}</span>' if src == "google"
             else '<span class="rv-src rv-src--fresha" title="Fresha review">fresha</span>')
    where = (units.get(r.get("unit"), {}) or {}).get("label", "")
    hid = ' aria-hidden="true"' if clone else ""
    return (f'<figure class="rv-card" data-source="{src}"{hid}>'
            f'<div class="rv-head"><span class="rv-avatar" style="background:{color}">{_esc(name[:1].upper())}</span>'
            f'<span class="rv-who"><strong>{_esc(name)}</strong><time datetime="{_esc(r.get("date", ""))}">{_esc(nice)}</time></span>{badge}</div>'
            f'<p class="rv-stars" aria-label="5 out of 5 stars">&#9733;&#9733;&#9733;&#9733;&#9733;</p>'
            f'<blockquote><p>{_esc(r.get("text", ""))}</p></blockquote>'
            f'<figcaption>{"Google" if src == "google" else "Fresha"} review &middot; {_esc(where)}</figcaption></figure>')
