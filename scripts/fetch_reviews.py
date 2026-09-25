#!/usr/bin/env python3
"""Busca as avaliacoes do Google das duas unidades e grava data/reviews.json.

Roda a cada 3 dias pelo .github/workflows/reviews.yml. Fonte: API do Local
Falcon (POST /v2/gbp/reviews/), que le as avaliacoes AO VIVO no Google Business
Profile das fichas conectadas na conta do Local Falcon. Precisa da variavel de
ambiente LOCALFALCON_API_KEY (secret do repositorio no GitHub).

Uso:
    LOCALFALCON_API_KEY=... python3 scripts/fetch_reviews.py [saida.json]
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reviews_lib import UNITS, build  # noqa: E402

API = "https://api.localfalcon.com/v2/gbp/reviews/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fetch_unit(key, place_id):
    reviews, token, total, average = [], None, 0, 0
    for _ in range(20):                       # 20 paginas x 50 = 1.000 avaliacoes
        body = {"api_key": key, "place_id": place_id, "limit": "50"}
        if token:
            body["next_token"] = token
        req = urllib.request.Request(API, data=urllib.parse.urlencode(body).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        if not d.get("success"):
            raise RuntimeError(f"Local Falcon: {d.get('message') or d.get('code')}")
        loc = d["data"]["locations"][0]
        if loc.get("error"):
            raise RuntimeError(f"Local Falcon ({place_id}): {loc.get('message')}")
        total, average = loc.get("total_reviews", 0), loc.get("average_rating", 0)
        reviews += loc.get("reviews", [])
        token = loc.get("next_token")
        if not token:
            break
        time.sleep(1)
    return {"total": total, "average": average, "reviews": reviews}


def main():
    key = os.environ.get("LOCALFALCON_API_KEY", "").strip()
    if not key:
        print("fetch_reviews: LOCALFALCON_API_KEY ausente; nada foi alterado.")
        return 0
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "reviews.json")
    units_raw = {u: fetch_unit(key, m["place_id"]) for u, m in UNITS.items()}
    data = build(units_raw, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    # trava de seguranca: se a API vier vazia, nao apaga o que o site ja mostra
    if sum(len(v["reviews"]) for v in units_raw.values()) == 0:
        raise RuntimeError("Local Falcon devolveu 0 avaliacoes; arquivo mantido.")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    u = data["units"]
    print(f"fetch_reviews: {len(data['reviews'])} publicaveis | "
          + " | ".join(f"{k} {v['rating']} ({v['total']})" for k, v in u.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
