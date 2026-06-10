#!/usr/bin/env python3
"""Extraire les informations des points de vente Timbermart."""

import re
import sys
from pathlib import Path

html_file = sys.argv[1] if len(sys.argv) > 1 else "Timbermart.txt"

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern pour trouver les blocs des magasins
# Chercher les patterns comme: <div><strong>NOM</strong></div><p>ADRESSE...
store_pattern = r'<div><strong>(.*?TIMBER MART.*?)</strong></div>\s*<p>(.*?)<br>(.*?)<br>(.*?)<br>(.*?)</p>\s*<p>Téléphone:\s*<strong>(.*?)</strong></p>\s*<p>Heures d\'ouverture:\s*<strong>(.*?)</strong>'

matches = re.finditer(store_pattern, content, re.DOTALL | re.IGNORECASE)

stores = []
for match in matches:
    nom = match.group(1).strip()
    # Extraire adresse, ville, province, code postal
    addr_parts = [match.group(2).strip(), match.group(3).strip(), match.group(4).strip(), match.group(5).strip()]
    adresse = addr_parts[0]
    ville_province_code = " ".join(addr_parts[1:])

    # Parser ville, province, code postal
    # Format: VILLE, PROV, CODE
    parts = ville_province_code.split(',')
    if len(parts) >= 2:
        ville = parts[0].strip()
        prov_code = ",".join(parts[1:]).strip()
        # Extraire code postal (dernier token)
        code_tokens = prov_code.split()
        code_postal = code_tokens[-1] if code_tokens else ""
        province = " ".join(code_tokens[:-1]) if len(code_tokens) > 1 else "QC"
    else:
        ville = ville_province_code
        province = "QC"
        code_postal = ""

    telephone = match.group(6).strip()
    heures = match.group(7).strip()

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
    print(f"    Tél: {store['Téléphone']}")
    print(f"    Heures: {store['Heures d\'ouverture']}\n")

# Exporter en CSV
import csv
output_file = "timbermart_stores.csv"
fieldnames = ['Nom', 'Adresse', 'Ville', 'Province', 'Code postal', 'Téléphone', 'Heures d\'ouverture']

with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(stores)

print(f"✅ Résultats exportés : {output_file}")
