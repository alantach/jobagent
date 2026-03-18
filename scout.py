#!/usr/bin/env python3
"""
Job Scout - prescreening
Konfigurace: data/urls.json, data/pravidla.json
Vysledky:    data/vysledky.json
Backup HTML: data/backup/
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
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
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
    url_re = re.compile(vzor, re.I) if vzor else None
    for m in re.finditer(r'href=["\']([^"\'#?][^"\']*)["\']', html):
        href = m.group(1)
        if href.startswith("http"):
            full = href
        elif href.startswith("/"):
            full = origin + href
        else:
            continue
        if url_re:
            match = url_re.search(full)
            if not match:
                continue
            id_inzeratu = match.group(1) if match.lastindex else ""
        else:
            id_inzeratu = ""
        if not any(l["url"] == full for l in links):
            links.append({"url": full, "id": id_inzeratu})
    return links

def parsuj(html):
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
        "popis":        text[:3000],
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
            skore += r["vaha"]
            matched.append(f"{r['pravidlo']}({'+' if r['vaha']>0 else ''}{r['vaha']})")
    return max(1, min(10, skore)), ", ".join(matched)

def uloz_html(html, inzerat, odkaz):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r'[^a-zA-Z0-9]', '_', inzerat["nazev_pozice"][:40])
    path = os.path.join(BACKUP_DIR, f"skore{inzerat['prescoring']}_{safe}_{ts}.html")
    liska = (
        f'<div style="position:fixed;top:0;left:0;right:0;background:#0f3460;'
        f'color:#00D4AA;padding:8px 16px;font-family:sans-serif;font-size:13px;z-index:9999">'
        f'<b>{inzerat["nazev_pozice"]}</b> &nbsp;|&nbsp; '
        f'Skore: <b>{inzerat["prescoring"]}/10</b> &nbsp;|&nbsp; '
        f'{inzerat["match_pravidla"]} &nbsp;|&nbsp; '
        f'<a href="{odkaz}" style="color:#fff" target="_blank">Otevrit original</a>'
        f'</div><div style="margin-top:44px">'
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(liska + html + "</div>")
    return os.path.basename(path)

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(URLS_FILE,  "r", encoding="utf-8") as f: urls  = json.load(f)
    with open(RULES_FILE, "r", encoding="utf-8") as f: rules = json.load(f)

    vysledky = []
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            vysledky = json.load(f)
    existujici = {v["odkaz"] for v in vysledky}

    aktivni = [z for z in urls if z.get("aktivni")]
    nove, preskoceno = 0, 0
    good_urls, bad_urls = [], []

    print(f"\n=== Job Scout {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Zdroju: {len(aktivni)}, pravidel: {len(rules)}, existujicich: {len(vysledky)}\n")

    for zdroj in aktivni:
        print(f"[{zdroj['nazev']}]")
        html_vypis = fetch(zdroj["url"])
        if not html_vypis:
            print("  PRESKOCENO\n")
            bad_urls.append({"nazev": zdroj["nazev"], "url": zdroj["url"], "duvod": "chyba stazeni"})
            continue

        odkazy = extrahuj_odkazy(html_vypis, zdroj["url"], zdroj.get("url_vzor", ""))
        print(f"  Nalezeno odkazu: {len(odkazy)}")
        if odkazy:
            good_urls.append({"nazev": zdroj["nazev"], "url": zdroj["url"], "odkazu": len(odkazy)})
        else:
            bad_urls.append({"nazev": zdroj["nazev"], "url": zdroj["url"], "duvod": "zadne odkazy nenalezeny"})

        for link in odkazy:
            odkaz      = link["url"]
            id_inzeratu = link["id"]

            if odkaz in existujici:
                continue

            html_detail = fetch(odkaz)
            if not html_detail:
                continue

            inzerat = parsuj(html_detail)
            skore, matched = prescoring(inzerat, rules)
            inzerat["prescoring"]     = skore
            inzerat["match_pravidla"] = matched

            if skore < MIN_SKORE:
                preskoceno += 1
                continue

            html_soubor = uloz_html(html_detail, inzerat, odkaz)

            vysledky.append({
                "datum":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "zdroj_nazev":    zdroj["nazev"],
                "nazev_pozice":   inzerat["nazev_pozice"],
                "firma":          inzerat["firma"],
                "lokalita":       inzerat["lokalita"],
                "odkaz":          odkaz,
                "id_inzeratu":    id_inzeratu,
                "prescoring":     skore,
                "match_pravidla": matched,
                "popis":          inzerat["popis"],
                "html_soubor":    html_soubor,
            })
            existujici.add(odkaz)
            nove += 1

            print(f"  + [{skore}/10] {inzerat['nazev_pozice'][:60]} @ {inzerat['firma'][:30]}")
            if matched:
                print(f"         {matched}")

        print()

    vysledky.sort(key=lambda x: x["prescoring"], reverse=True)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(vysledky, f, ensure_ascii=False, indent=2)

    # Zapis souhrn URL
    os.makedirs(BACKUP_DIR, exist_ok=True)
    with open(os.path.join(BACKUP_DIR, "_goodurl.json"), "w", encoding="utf-8") as f:
        json.dump(good_urls, f, ensure_ascii=False, indent=2)
    with open(os.path.join(BACKUP_DIR, "_badurl.json"), "w", encoding="utf-8") as f:
        json.dump(bad_urls, f, ensure_ascii=False, indent=2)

    print(f"Funkci zdroju:    {len(good_urls)} (viz backup/_goodurl.json)")
    print(f"Nefunkcni zdroju: {len(bad_urls)} (viz backup/_badurl.json)")
    print(f"=== Hotovo: {nove} novych, {preskoceno} pod skore {MIN_SKORE}, celkem: {len(vysledky)} ===\n")

if __name__ == "__main__":
    main()
