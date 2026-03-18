#!/usr/bin/env python3
"""
Spolecny modul pro prescoring - pouziva scout.py i rescore.py
"""

def vypocitej(inzerat, rules):
    """
    Vypocita prescoring inzeratu podle pravidel.
    inzerat: dict s klici nazev_pozice, firma, lokalita, popis
    rules:   list dictu s klici pravidlo a vaha
    Vraci:  (skore int 1-10, matched str)
    """
    haystack = " ".join([
        inzerat.get("nazev_pozice", ""),
        inzerat.get("firma", ""),
        inzerat.get("lokalita", ""),
        inzerat.get("popis", ""),
    ]).lower()
    skore, matched = 0, []
    for r in rules:
        if r["pravidlo"].lower() in haystack:
            skore += r["vaha"]
            matched.append(f"{r['pravidlo']}({'+' if r['vaha']>0 else ''}{r['vaha']})")
    return max(1, min(10, skore)), ", ".join(matched)
