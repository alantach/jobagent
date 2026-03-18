#!/usr/bin/env python3
"""
Vypise obsah stazene.json - co bylo stazeno, kdy a s jakym vysledkem
Spust: python stazene_info.py
"""
import json
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STAZENE  = os.path.join(BASE_DIR, "data", "stazene.json")

if not os.path.exists(STAZENE):
    print("stazene.json neexistuje - spust nejdrive scout.py")
    exit()

with open(STAZENE, "r", encoding="utf-8") as f:
    stazene = json.load(f)

print(f"\n=== Stazene inzeraty: {len(stazene)} ===\n")

# Seskup podle zdroje
podle_zdroje = Counter(v["zdroj"] for v in stazene.values())
print("Podle zdroje:")
for zdroj, pocet in sorted(podle_zdroje.items(), key=lambda x: -x[1]):
    print(f"  {pocet:4d}  {zdroj}")

# Seskup podle vysledku
print("\nPodleho vysledku:")
podle_vysledku = Counter(v["vysledek"] for v in stazene.values())
for vysledek, pocet in sorted(podle_vysledku.items(), key=lambda x: -x[1]):
    print(f"  {pocet:4d}  {vysledek}")

# Posledni stazene
print("\nPosledni stazene (10):")
serazene = sorted(stazene.items(), key=lambda x: x[1]["datum"], reverse=True)
for id_inz, info in serazene[:10]:
    print(f"  [{info['vysledek']:10s}] {info['datum']} | {info['zdroj'][:25]} | {id_inz[:40]}")

print()
