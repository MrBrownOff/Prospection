"""
Script pour ajouter les codes postaux au fichier Timbermart.
Utilise Nominatim (OpenStreetMap, gratuit) via les coordonnées GPS.

Usage:
    pip install pandas openpyxl requests
    python get_postal_codes.py
"""

import pandas as pd
import requests
import time

INPUT_FILE = "46f65194-timbermart_avec_superficie_verifiee.xlsx"
OUTPUT_FILE = "timbermart_avec_code_postal.xlsx"

df = pd.read_excel(INPUT_FILE)
print(f"Fichier chargé : {len(df)} lignes")

postal_codes = []
headers = {"User-Agent": "PostalCodeExtractor/1.0 (votre@email.com)"}

for i, row in df.iterrows():
    lat, lon = row["lat"], row["lon"]
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
            headers=headers,
            timeout=10,
        )
        data = resp.json()
        postcode = data.get("address", {}).get("postcode", "")
        postal_codes.append(postcode)
        print(f"[{i+1}/{len(df)}] {row['nom'][:35]:35s} → {postcode or 'N/A'}")
    except Exception as e:
        postal_codes.append("")
        print(f"[{i+1}/{len(df)}] ERREUR : {e}")
    time.sleep(1.2)  # Respecter la limite Nominatim : 1 req/sec

# Insérer la colonne après 'adresse'
df.insert(df.columns.get_loc("adresse") + 1, "Code Postal", postal_codes)
df.to_excel(OUTPUT_FILE, index=False)
print(f"\nFichier sauvegardé : {OUTPUT_FILE}")
print(f"Codes postaux trouvés : {sum(1 for p in postal_codes if p)} / {len(postal_codes)}")
