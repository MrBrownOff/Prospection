#!/usr/bin/env python3
"""
Géocodage des magasins Castle québécois
========================================
Ajoute les coordonnées GPS à chaque magasin.

Utilisation :
    python geocode_castle_stores.py castle_stores_quebec.csv

Génère : castle_stores_quebec_geocoded.csv
"""

import csv
import time
import sys
from pathlib import Path

def geocode_with_nominatim(address, city, province="Quebec", country="Canada"):
    """Géocode une adresse avec OpenStreetMap Nominatim (gratuit, pas de clé API)."""
    try:
        from geopy.geocoders import Nominatim
    except ImportError:
        print("❌ Geopy non installé. Installe-le avec :")
        print("   pip install geopy")
        return None, None

    try:
        # Construire l'adresse complète
        full_address = f"{address}, {city}, {province}, {country}"

        # Créer le géocodeur
        geolocator = Nominatim(user_agent="castle_store_geocoder")

        # Géocoder
        location = geolocator.geocode(full_address, timeout=10)

        if location:
            return location.latitude, location.longitude
        else:
            return None, None

    except Exception as e:
        print(f"    ⚠️  Erreur géocodage : {str(e)[:50]}")
        return None, None

def main():
    if len(sys.argv) < 2:
        print("Usage: python geocode_castle_stores.py <input_csv>")
        print("Example: python geocode_castle_stores.py castle_stores_quebec.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = input_file.replace('.csv', '_geocoded.csv')

    print(f"\n📍 Géocodage des magasins Castle\n")

    if not Path(input_file).exists():
        print(f"❌ Fichier non trouvé : {input_file}")
        sys.exit(1)

    # Lire le CSV
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"📊 {len(rows)} magasins à géocoder\n")

    # Géocoder chaque magasin
    for i, row in enumerate(rows, 1):
        nom = row.get('Nom', '').strip()
        adresse = row.get('Adresse', '').strip()
        ville = row.get('Ville', '').strip()
        code_postal = row.get('Code postal', '').strip()

        print(f"[{i}/{len(rows)}] 🔍 {nom[:40]:<40} ({ville})", end=" ", flush=True)

        # Géocoder
        lat, lng = geocode_with_nominatim(
            f"{adresse}, {code_postal}",
            ville,
            province="Quebec",
            country="Canada"
        )

        if lat and lng:
            row['Latitude'] = round(lat, 6)
            row['Longitude'] = round(lng, 6)
            print(f"✅ ({lat:.4f}, {lng:.4f})")
        else:
            row['Latitude'] = ''
            row['Longitude'] = ''
            print(f"❌")

        # Rate limiting : 1 requête par seconde pour respecter Nominatim
        if i < len(rows):
            time.sleep(1.1)

    # Écrire le CSV géocodé
    fieldnames = list(rows[0].keys()) if rows else []
    if 'Latitude' not in fieldnames:
        fieldnames.extend(['Latitude', 'Longitude'])

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Résumé
    geocoded_count = sum(1 for row in rows if row.get('Latitude'))
    print(f"\n{'='*60}")
    print(f"✅ Géocodage terminé")
    print(f"   Magasins géocodés : {geocoded_count}/{len(rows)}")
    print(f"   Fichier : {output_file}\n")

if __name__ == '__main__':
    main()
