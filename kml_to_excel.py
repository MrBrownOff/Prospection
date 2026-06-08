#!/usr/bin/env python3
"""
Convertir KML avec superficies en Excel
========================================
Parse le KML Google Earth avec les superficies et exporte en Excel.

Usage:
    python kml_to_excel.py CastleSuperficieverifiee.kml
"""

import xml.etree.ElementTree as ET
import re
import pandas as pd
import sys
from pathlib import Path

def parse_kml(kml_file):
    """Parse le KML et extrait les données des magasins."""
    tree = ET.parse(kml_file)
    root = tree.getroot()

    # Namespaces
    ns = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2'
    }

    stores = []

    # Trouver tous les Placemarks
    for placemark in root.findall('.//kml:Placemark', ns):
        store = {}

        # Nom
        name_el = placemark.find('kml:name', ns)
        store['Nom'] = name_el.text.strip() if name_el is not None else ''

        # Description (contient adresse, ville, code postal)
        desc_el = placemark.find('kml:description', ns)
        if desc_el is not None and desc_el.text:
            # Nettoyer le HTML
            text = desc_el.text
            # Enlever les balises HTML
            text = re.sub('<[^>]+>', '', text)
            text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
            lines = [line.strip() for line in text.split('<br>') if line.strip()]
            lines = [line for line in text.split('\n') if line.strip() and 'td' not in line and 'colspan' not in line]

            if len(lines) >= 4:
                store['Adresse'] = lines[0].strip()
                store['Ville'] = lines[1].strip()
                store['Province'] = lines[2].strip() if len(lines) > 2 else 'Quebec'
                store['Code postal'] = lines[3].strip() if len(lines) > 3 else ''
            else:
                store['Adresse'] = ''
                store['Ville'] = ''
                store['Province'] = 'Quebec'
                store['Code postal'] = ''
        else:
            store['Adresse'] = ''
            store['Ville'] = ''
            store['Province'] = 'Quebec'
            store['Code postal'] = ''

        # Coordonnées (LookAt)
        lookat = placemark.find('kml:LookAt', ns)
        if lookat is not None:
            lat_el = lookat.find('kml:latitude', ns)
            lon_el = lookat.find('kml:longitude', ns)
            store['Latitude'] = float(lat_el.text) if lat_el is not None else None
            store['Longitude'] = float(lon_el.text) if lon_el is not None else None
        else:
            store['Latitude'] = None
            store['Longitude'] = None

        stores.append(store)

    return stores

def main():
    if len(sys.argv) < 2:
        print("Usage: python kml_to_excel.py <kml_file>")
        sys.exit(1)

    kml_file = sys.argv[1]

    if not Path(kml_file).exists():
        print(f"❌ Fichier non trouvé : {kml_file}")
        sys.exit(1)

    print(f"\n📂 Parsing KML : {kml_file}")

    # Parser le KML
    stores = parse_kml(kml_file)

    print(f"✅ {len(stores)} magasins trouvés\n")

    # Créer DataFrame
    df = pd.DataFrame(stores)

    # Reordonner les colonnes
    columns = ['Nom', 'Adresse', 'Ville', 'Province', 'Code postal', 'Latitude', 'Longitude']
    df = df[columns]

    # Exporter en Excel
    output_file = Path(kml_file).stem + '.xlsx'
    df.to_excel(output_file, index=False, sheet_name='Magasins')

    print(f"✅ Excel créé : {output_file}")
    print(f"📊 {len(df)} lignes × {len(df.columns)} colonnes\n")

if __name__ == '__main__':
    main()
