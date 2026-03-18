#!/usr/bin/env python3
"""
Prescoring modul - sdilena logika pro scout.py i rescore.py
Skore = soucet vah matchujicich pravidel, oriznuty na -50 az +50
"""

def vypocitej(inzerat, rules):
    haystack = " ".join([
        inzerat.get("nazev_pozice", ""),
        inzerat.get("firma", ""),
        inzerat.get("lokalita", ""),
        inzerat.get("popis", ""),
    ]).lower()

    skore = 0
    matched = []
    for r in rules:
        if r["pravidlo"].lower() in haystack:
            skore += r["vaha"]
            matched.append(f"{r['pravidlo']}({'+' if r['vaha'] > 0 else ''}{r['vaha']})")

    return max(-50, min(50, skore)), ", ".join(matched)
