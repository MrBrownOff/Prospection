#!/usr/bin/env python3
"""Extraire les informations Timbermart avec BeautifulSoup."""

import sys
import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("BeautifulSoup non installé. Installation: pip install beautifulsoup4")
    sys.exit(1)

html_file = sys.argv[1] if len(sys.argv) > 1 else "Timbermart.txt"

with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

stores = []

# Chercher tous les blocs "current-store--info"
store_blocks = soup.find_all('div', class_='current-store--info')

for block in store_blocks:
    # Extraire le nom
    name_elem = block.find('strong', class_='current-store--name')
    if not name_elem:
        # Fallback: chercher le premier strong
        name_elem = block.find('strong')

    if not name_elem:
        continue

    nom = name_elem.get_text(strip=True)

    # Extraire l'adresse complète (les paragraphes)
    paragraphs = block.find_all('p')

    adresse = ""
    ville = ""
    province = ""
    code_postal = ""
    telephone = ""
    heures = ""

    # Première ou deuxième <p> contient l'adresse
    if len(paragraphs) > 0:
        # La première p contient l'adresse sur plusieurs lignes
        addr_p = paragraphs[0]
        lines = [line.strip() for line in addr_p.get_text().split('\n') if line.strip()]

        if len(lines) >= 1:
            adresse = lines[0]
        if len(lines) >= 2:
            # Deuxième ligne: ville, province, code
            city_line = lines[1]
            # Parser: VILLE, QC CODE
            match = re.match(r'(.*?),\s*([A-Z]{2})\s*([A-Z0-9\s]+)', city_line)
            if match:
                ville = match.group(1).strip()
                province = match.group(2).strip()
                code_postal = match.group(3).strip()
            else:
                ville = city_line

    # Chercher Téléphone et Heures d'ouverture dans les <p> suivants
    for p in paragraphs[1:]:
        text = p.get_text(strip=True)
        if 'Téléphone' in text:
            # Extraire le numéro
            tel_match = re.search(r'[\d\-\(\)\s]+', text)
            if tel_match:
                telephone = tel_match.group().strip()
        if 'Heures' in text or 'heure' in text.lower():
            # Extraire les heures
            heures_match = re.search(r'(\d+[hH:]\d+.*?\d+[hH:]\d+)', text)
            if heures_match:
                heures = heures_match.group(1).strip()

    if nom and adresse:
        stores.append({
            'Nom': nom,
            'Adresse': adresse,
            'Ville': ville,
            'Province': province,
            'Code postal': code_postal,
            'Téléphone': telephone,
            'Heures d\'ouverture': heures
        })

print(f"\n✅ {len(stores)} magasins trouvés\n")
for i, store in enumerate(stores, 1):
    print(f"[{i}] {store['Nom']}")
    print(f"    {store['Adresse']}")
    print(f"    {store['Ville']}, {store['Province']} {store['Code postal']}")
    if store['Téléphone']:
        print(f"    Tél: {store['Téléphone']}")
    if store['Heures d\'ouverture']:
        print(f"    Heures: {store['Heures d\'ouverture']}")
    print()

# Exporter en CSV
output_file = "timbermart_stores.csv"
fieldnames = ['Nom', 'Adresse', 'Ville', 'Province', 'Code postal', 'Téléphone', 'Heures d\'ouverture']

with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(stores)

print(f"✅ Résultats exportés : {output_file}\n")
