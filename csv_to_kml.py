#!/usr/bin/env python3
"""Convertir un CSV de magasins en KML pour superficie_commerces.py"""

import csv
import sys
from pathlib import Path

def csv_to_kml(csv_path, kml_path=None):
    """Convertit CSV → KML avec structure attendue par superficie_commerces.py"""

    if kml_path is None:
        kml_path = Path(csv_path).stem + ".kml"

    # Lire CSV (détection d'encodage)
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    rows = None

    for enc in encodings:
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            print(f"✓ CSV lu avec {enc}")
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if rows is None:
        print(f"❌ Impossible de lire {csv_path}")
        sys.exit(1)

    # Afficher les colonnes trouvées
    if rows:
        colonnes = list(rows[0].keys())
        print(f"Colonnes détectées : {colonnes}\n")

    # Mapper les colonnes (flexible)
    col_nom = col_adresse = col_ville = col_lat = col_lon = None

    for col in rows[0].keys():
        col_lower = col.lower().strip()
        if 'nom' in col_lower:
            col_nom = col
        elif 'adresse' in col_lower:
            col_adresse = col
        elif 'ville' in col_lower:
            col_ville = col
        elif 'latitude' in col_lower or 'lat' in col_lower:
            col_lat = col
        elif 'longitude' in col_lower or 'lon' in col_lower:
            col_lon = col

    print(f"Mappé : Nom={col_nom}, Adresse={col_adresse}, Ville={col_ville}, Lat={col_lat}, Lon={col_lon}\n")

    # Générer KML
    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        '<name>Timbermart Stores</name>',
        '<description>Magasins Timbermart Québec</description>',
    ]

    count = 0
    for row in rows:
        nom = (row.get(col_nom) or '').strip() if col_nom else ''
        adresse = (row.get(col_adresse) or '').strip() if col_adresse else ''
        ville = (row.get(col_ville) or '').strip() if col_ville else ''

        try:
            lat = float(row.get(col_lat, 0)) if col_lat else 0
            lon = float(row.get(col_lon, 0)) if col_lon else 0
        except (ValueError, TypeError):
            print(f"⚠️  {nom} — coords invalides, ignoré")
            continue

        if not nom or not lat or not lon:
            print(f"⚠️  {nom} — données incomplètes (nom={nom}, lat={lat}, lon={lon}), ignoré")
            continue

        # Placemark KML
        kml_lines.extend([
            '<Placemark>',
            f'<name>{nom}</name>',
            f'<Point><coordinates>{lon},{lat},0</coordinates></Point>',
            '<ExtendedData>',
            f'<Data name="Adresse"><value>{adresse}</value></Data>',
            f'<Data name="Ville"><value>{ville}</value></Data>',
            '</ExtendedData>',
            '</Placemark>',
        ])
        count += 1

    kml_lines.extend(['</Document>', '</kml>'])

    # Écrire KML
    with open(kml_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(kml_lines))

    print(f"✅ KML généré : {kml_path} ({count}/{len(rows)} magasins)")
    return kml_path

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python csv_to_kml.py <input.csv> [output.kml]")
        sys.exit(1)

    csv_path = sys.argv[1]
    kml_path = sys.argv[2] if len(sys.argv) > 2 else None
    csv_to_kml(csv_path, kml_path)
