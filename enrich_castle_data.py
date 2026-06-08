#!/usr/bin/env python3
"""
Enrichissement des magasins Castle avec API
=============================================
Ajoute les heures, téléphone, email depuis l'API Castle.

Utilisation :
    python enrich_castle_data.py castle_stores_quebec_geocoded.csv castle_api_data.json

Génère : castle_stores_quebec_enriched.csv
"""

import csv
import json
import sys
from pathlib import Path

def load_api_data(api_file):
    """Charge les données de l'API Castle."""
    try:
        with open(api_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture API : {e}")
        return None

def match_store(store_name, city, retailers):
    """Trouve le magasin correspondant dans l'API."""
    # Retailers est un dict avec IDs comme clés
    if isinstance(retailers, dict):
        retailers_list = list(retailers.values())
    else:
        retailers_list = retailers

    for retailer in retailers_list:
        api_name = retailer.get('name', '').upper()
        api_city = retailer.get('address', {}).get('city', '').upper()

        if api_name in store_name.upper() or store_name.upper() in api_name:
            if api_city == city.upper() or city.upper() in api_city:
                return retailer

    return None

def extract_hours(hours_data):
    """Extrait les heures d'ouverture."""
    if not isinstance(hours_data, dict):
        return ''

    hours = []
    if isinstance(hours_data, dict):
        for hour_id, hour_info in hours_data.items():
            if isinstance(hour_info, dict):
                day_type = hour_info.get('type', '')
                display = hour_info.get('display', '')
                if display and display != '12:00 am - 12:00 am':
                    hours.append(f"{day_type}: {display}")

    return ' | '.join(hours[:3])  # Limiter à 3 lignes

def main():
    if len(sys.argv) < 3:
        print("Usage: python enrich_castle_data.py <stores_csv> <api_json>")
        print("Example: python enrich_castle_data.py castle_stores_quebec_geocoded.csv castle_api_data.json")
        sys.exit(1)

    stores_file = sys.argv[1]
    api_file = sys.argv[2]
    output_file = stores_file.replace('.csv', '_enriched.csv')

    print(f"\n🔄 Enrichissement des données\n")

    # Charger l'API
    if not Path(api_file).exists():
        print(f"❌ Fichier API non trouvé : {api_file}")
        sys.exit(1)

    api_data = load_api_data(api_file)
    if not api_data:
        sys.exit(1)

    retailers = api_data.get('retailers', {})
    print(f"📡 {len(retailers)} magasins dans l'API\n")

    # Lire le CSV
    with open(stores_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"🏪 Enrichissement de {len(rows)} magasins...\n")

    # Enrichir chaque magasin
    for i, row in enumerate(rows, 1):
        nom = row.get('Nom', '').strip()
        ville = row.get('Ville', '').strip()

        print(f"[{i}/{len(rows)}] {nom[:40]:<40}", end=" ", flush=True)

        # Chercher dans l'API
        retailer = match_store(nom, ville, retailers)

        if retailer:
            contact = retailer.get('contact', {})
            row['Téléphone'] = contact.get('phone', '') or ''
            row['Email'] = contact.get('email', '') or ''

            hours = retailer.get('hours', {})
            row['Heures'] = extract_hours(hours)

            print("✅")
        else:
            row['Téléphone'] = ''
            row['Email'] = ''
            row['Heures'] = ''
            print("⚠️")

    # Écrire le CSV enrichi
    fieldnames = list(rows[0].keys()) if rows else []
    if 'Téléphone' not in fieldnames:
        fieldnames.extend(['Téléphone', 'Email', 'Heures'])

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    enriched_count = sum(1 for row in rows if row.get('Téléphone'))
    print(f"\n{'='*60}")
    print(f"✅ Enrichissement terminé")
    print(f"   Magasins enrichis : {enriched_count}/{len(rows)}")
    print(f"   Fichier : {output_file}\n")

if __name__ == '__main__':
    main()
