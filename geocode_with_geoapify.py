#!/usr/bin/env python3
"""
Géocodage Timbermart avec Geoapify (gratuit, 3000 requêtes/mois)
Beaucoup plus précis que Nominatim pour les petites villes du Québec
"""

import csv
import sys
import time
from pathlib import Path

def geocode_with_geoapify(address, city, api_key, province="QC", country="Canada"):
    """Géocode une adresse avec Geoapify"""
    try:
        import requests
    except ImportError:
        print("❌ Requests non installé. Installe-le avec : pip install requests")
        return None, None

    try:
        full_address = f"{address}, {city}, {province}, {country}"

        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            "text": full_address,
            "apiKey": api_key,
            "limit": 1,
        }

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("features") and len(data["features"]) > 0:
            coords = data["features"][0]["geometry"]["coordinates"]
            lon, lat = coords[0], coords[1]
            return lat, lon
        else:
            return None, None

    except Exception as e:
        print(f"    ⚠️  Erreur géocodage : {str(e)[:50]}")
        return None, None


def main():
    if len(sys.argv) < 3:
        print("Usage: python geocode_with_geoapify.py <input.csv> <api_key>")
        print("\nObtiens ta clé API gratuite sur : https://myprojects.geoapify.com/")
        print("Exemple: python geocode_with_geoapify.py timbermart_fixed.csv abc123xyz")
        sys.exit(1)

    input_file = sys.argv[1]
    api_key = sys.argv[2]
    output_file = input_file.replace('.csv', '_geocoded.csv')

    print(f"\n🗺️  Géocodage Geoapify\n")

    if not Path(input_file).exists():
        print(f"❌ Fichier non trouvé : {input_file}")
        sys.exit(1)

    # Lire le CSV (détection d'encodage)
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    rows = None

    for enc in encodings:
        try:
            with open(input_file, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            print(f"✓ CSV lu avec {enc}\n")
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if rows is None:
        print(f"❌ Impossible de lire {input_file}")
        sys.exit(1)

    print(f"📊 Géocodage de {len(rows)} magasins avec Geoapify\n")
    print(f"⏱️  Rate limit: ~3000/mois = ~100/jour (pause de 0.5s entre requêtes)\n")

    geocoded = 0
    failed = 0

    # Géocoder chaque magasin
    for i, row in enumerate(rows, 1):
        nom = row.get('Nom', '').strip()
        adresse = row.get('Adresse', '').strip()
        ville = row.get('Ville', '').strip()

        print(f"[{i:>2}/{len(rows)}] 🔍 {nom[:40]:<40} ({ville})", end=" ", flush=True)

        # Géocoder
        lat, lng = geocode_with_geoapify(adresse, ville, api_key)

        if lat and lng:
            row['Latitude'] = round(lat, 6)
            row['Longitude'] = round(lng, 6)
            print(f"✅ ({lat:.4f}, {lng:.4f})")
            geocoded += 1
        else:
            row['Latitude'] = ''
            row['Longitude'] = ''
            print(f"❌")
            failed += 1

        # Rate limiting : 0.5 sec pour rester bien sous les limites
        if i < len(rows):
            time.sleep(0.5)

    # Écrire le CSV géocodé
    fieldnames = list(rows[0].keys()) if rows else []
    if 'Latitude' not in fieldnames:
        fieldnames.extend(['Latitude', 'Longitude'])

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Résumé
    print(f"\n{'='*60}")
    print(f"✅ Géocodage terminé")
    print(f"   ✓  Réussis : {geocoded}/{len(rows)}")
    print(f"   ✗  Échoués : {failed}/{len(rows)}")
    print(f"   Fichier : {output_file}\n")

    if geocoded == len(rows):
        print(f"🎉 Tous les magasins géocodés ! Prêt pour l'étape suivante :")
        print(f"   python csv_to_kml.py {output_file}")


if __name__ == '__main__':
    main()
