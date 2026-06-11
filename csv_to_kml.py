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

    # Générer KML
    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        '<name>Timbermart Stores</name>',
        '<description>Magasins Timbermart Québec</description>',
    ]

    for row in rows:
        nom = (row.get('Nom') or '').strip()
        adresse = (row.get('Adresse') or '').strip()
        ville = (row.get('Ville') or '').strip()

        try:
            lat = float(row.get('Latitude', 0))
            lon = float(row.get('Longitude', 0))
        except (ValueError, TypeError):
            print(f"⚠️  {nom} — coords invalides, ignoré")
            continue

        if not nom or not lat or not lon:
            print(f"⚠️  Données incomplètes, ignoré")
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

    kml_lines.extend(['</Document>', '</kml>'])

    # Écrire KML
    with open(kml_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(kml_lines))

    print(f"✅ KML généré : {kml_path} ({len(rows)} magasins)")
    return kml_path

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python csv_to_kml.py <input.csv> [output.kml]")
        sys.exit(1)

    csv_path = sys.argv[1]
    kml_path = sys.argv[2] if len(sys.argv) > 2 else None
    csv_to_kml(csv_path, kml_path)
