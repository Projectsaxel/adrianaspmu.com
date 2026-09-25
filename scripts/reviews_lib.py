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


def build(units_raw, updated_iso):
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
    return out
