#!/usr/bin/env python3
"""
Rescore - prepocita prescoring nad existujicimi vysledky.json
Pouziva aktualni pravidla.json - bez stahovani.
Spust: python rescore.py
"""
import json
import os
import prescoring as ps

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
RULES_FILE = os.path.join(DATA_DIR, "pravidla.json")
OUT_FILE   = os.path.join(DATA_DIR, "vysledky.json")
MIN_SKORE  = 5


def main():
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        rules = json.load(f)
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        vysledky = json.load(f)

    print(f"\n=== Rescore ===")
    print(f"Pravidel: {len(rules)}, zaznamu: {len(vysledky)}\n")

    zmeneno = 0
    odfilterovano = 0
    nove_vysledky = []

    for z in vysledky:
        stare_skore = z.get("prescoring", 0)
        nove_skore, matched = ps.vypocitej(z, rules)
        z["prescoring"]     = nove_skore
        z["match_pravidla"] = matched

        if nove_skore < MIN_SKORE:
            print(f"  - [{stare_skore} -> {nove_skore}] {z['nazev_pozice'][:60]} (odfilterovano)")
            odfilterovano += 1
            continue

        if nove_skore != stare_skore:
            print(f"  ~ [{stare_skore} -> {nove_skore}] {z['nazev_pozice'][:60]}")
            zmeneno += 1

        nove_vysledky.append(z)

    nove_vysledky.sort(key=lambda x: x["prescoring"], reverse=True)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(nove_vysledky, f, ensure_ascii=False, indent=2)

    print(f"\nZmeneno skore: {zmeneno}")
    print(f"Odfilterovano (pod {MIN_SKORE}): {odfilterovano}")
    print(f"Zbyvajicich zaznamu: {len(nove_vysledky)}")
    print(f"=== Hotovo ===\n")

if __name__ == "__main__":
    main()
