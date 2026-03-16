#!/usr/bin/env python3
"""
Job Scout - prescreening
Vysledky ulozi do data/vysledky.json
"""
import urllib.request
import json
import os
import re
from datetime import datetime

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
URLS_FILE  = os.path.join(DATA_DIR, "urls.json")
RULES_FILE = os.path.join(DATA_DIR, "pravidla.json")
OUT_FILE   = os.path.join(DATA_DIR, "vysledky.json")
MIN_SKORE  = 5

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
}

def fetch(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    ! {e}")
        return ""

def extrahuj_odkazy(html, base_url, vzor):
    links = []
    origin = re.match(r'^(https?://[^/]+)', base_url)
    origin = origin.group(1) if origin else ""
    for m in re.finditer(r'href=["\']([^"\'#?][^"\']*)["\']', html):
        href = m.group(1)
        if href.startswith("http"):
            full = href
        elif href.startswith("/"):
            full = origin + href
        else:
            continue
        if vzor and vzor.lower() not in full.lower():
            continue
        if full not in links:
            links.append(full)
    return links

def parsuj(html, odkaz):
    text = re.sub(r'<script[\s\S]*?</script>', ' ', html, flags=re.I)
    text = re.sub(r'<style[\s\S]*?</style>', ' ', text, flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&\w+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    nazev = ""
    m = re.search(r'<h1[^>]*>([\s\S]{1,200}?)</h1>', html, re.I)
    if m: nazev = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if not nazev:
        m = re.search(r'og:title[^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m: nazev = m.group(1).strip()
    if not nazev:
        m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
        if m: nazev = re.split(r'[|\-–]', m.group(1))[0].strip()

    firma = ""
    m = re.search(r'hiringOrganization[\s\S]{0,300}?"name"\s*:\s*"([^"]{1,100})"', html, re.I)
    if m: firma = m.group(1)
    if not firma:
        m = re.search(r'og:site_name[^>]*content=["\']([^"\']+)["\']', html, re.I)
        if m: firma = m.group(1).strip()

    lokalita = ""
    m = re.search(r'addressLocality["\':\s]+([^\s"\'}{,<]{2,50})', html, re.I)
    if m: lokalita = m.group(1).strip()

    return {
        "nazev_pozice": nazev[:150],
        "firma":        firma[:100],
        "lokalita":     lokalita[:100],
        "popis":        text[:2000],
        "odkaz":        odkaz,
    }

def prescoring(inzerat, rules):
    haystack = " ".join([
        inzerat["nazev_pozice"],
        inzerat["firma"],
        inzerat["lokalita"],
        inzerat["popis"],
    ]).lower()
    skore, matched = 0, []
    for r in rules:
        if r["pravidlo"].lower() in haystack:
            skore += r.get("vaha", 0)
            matched.append(f"{r['pravidlo']}({'+' if r['vaha']>0 else ''}{r['vaha']})")
    return max(1, min(10, skore)), ", ".join(matched)

def main():
    with open(URLS_FILE,  "r", encoding="utf-8") as f: urls  = json.load(f)
    with open(RULES_FILE, "r", encoding="utf-8") as f: rules = json.load(f)

    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            vysledky = json.load(f)
    else:
        vysledky = []

    existujici = {v["odkaz"] for v in vysledky}
    aktivni    = [u for u in urls if u.get("aktivni")]
    nove       = 0
    preskoceno = 0

    print(f"\n=== Job Scout {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Zdroju: {len(aktivni)}, pravidel: {len(rules)}, existujicich: {len(vysledky)}\n")

    for zdroj in aktivni:
        print(f"[{zdroj['nazev']}]")
        html_vypis = fetch(zdroj["url"])
        if not html_vypis:
            print("  PRESKOCENO\n")
            continue

        odkazy = extrahuj_odkazy(html_vypis, zdroj["url"], zdroj.get("url_vzor", ""))
        print(f"  Odkazu: {len(odkazy)}")

        for odkaz in odkazy:
            if odkaz in existujici:
                continue
            html_detail = fetch(odkaz)
            if not html_detail:
                continue

            inzerat = parsuj(html_detail, odkaz)
            skore, matched = prescoring(inzerat, rules)

            if skore < MIN_SKORE:
                preskoceno += 1
                continue

            vysledky.append({
                "datum":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "zdroj_nazev":    zdroj["nazev"],
                "nazev_pozice":   inzerat["nazev_pozice"],
                "firma":          inzerat["firma"],
                "lokalita":       inzerat["lokalita"],
                "odkaz":          odkaz,
                "prescoring":     skore,
                "match_pravidla": matched,
            })
            existujici.add(odkaz)
            nove += 1
            print(f"  + [{skore}/10] {inzerat['nazev_pozice'][:60]} @ {inzerat['firma'][:30]}")

        print()

    vysledky.sort(key=lambda x: x["prescoring"], reverse=True)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(vysledky, f, ensure_ascii=False, indent=2)

    print(f"=== Hotovo: {nove} novych, {preskoceno} pod skore {MIN_SKORE}, celkem: {len(vysledky)} ===\n")

if __name__ == "__main__":
    main()
