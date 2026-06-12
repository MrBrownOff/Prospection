#!/usr/bin/env python3
"""
Exporter données Timbermart vers Excel
======================================
Combine les données du CSV geocodé avec les superficies du KML validé
"""

import csv
import xml.etree.ElementTree as ET
import pandas as pd
import sys
import re
from pathlib import Path

def read_geocoded_csv(csv_path):
    """Lit le CSV geocodé avec les informations des magasins"""
    stores = {}

    def safe_get_strip(d, key, default=''):
        """Safely get and strip a value"""
        val = d.get(key, default)
        return val.strip() if val else default

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # Détecter le délimiteur
            first_line = f.readline()
            delimiter = ';' if first_line.count(';') > first_line.count(',') else ','
            f.seek(0)

            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                if row and any(row.values()):
                    nom = safe_get_strip(row, 'Nom')
                    if nom:
                        stores[nom] = {
                            'Nom': nom,
                            'Adresse': safe_get_strip(row, 'Adresse'),
                            'Ville': safe_get_strip(row, 'Ville'),
                            'Province': safe_get_strip(row, 'Province'),
                            'Code postal': safe_get_strip(row, 'Code postal'),
                            'Téléphone': safe_get_strip(row, 'Tlphone') or safe_get_strip(row, 'Téléphone'),
                            'Heures': safe_get_strip(row, "Heures d'ouverture") or safe_get_strip(row, 'Heures'),
                            'Latitude': None,
                            'Longitude': None,
                            'Superficie_m2': None,
                            'Superficie_pi2': None,
                            'Source': None,
                            'Notes': None,
                        }

                        # Parser les coordonnées
                        try:
                            lat_str = safe_get_strip(row, 'Latitude')
                            lon_str = safe_get_strip(row, 'Longitude')

                            if lat_str and lon_str:
                                lat = float(lat_str)
                                lon = float(lon_str)
                                # Vérifier que ce ne sont pas les coords par défaut
                                if not (abs(lat - 52.476089) < 0.0001 and abs(lon - (-71.825867)) < 0.0001):
                                    stores[nom]['Latitude'] = lat
                                    stores[nom]['Longitude'] = lon
                        except (ValueError, KeyError):
                            pass

    except Exception as e:
        print(f"❌ Erreur lecture CSV: {e}")
        return None

    print(f"✓ {len(stores)} magasins lus du CSV")
    return stores

def parse_kml_footprints(kml_path, stores):
    """Parse le KML Google Earth et extrait les superficies"""
    try:
        tree = ET.parse(kml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Erreur parsing KML: {e}")
        return

    ns = {'kml': 'http://www.opengis.net/kml/2.2', 'gx': 'http://www.google.com/kml/ext/2.2'}

    matched = 0
    for placemark in root.findall('.//kml:Placemark', ns):
        # Récupérer le nom
        name_el = placemark.find('kml:name', ns)
        if name_el is None or name_el.text is None:
            continue

        name = name_el.text.strip()

        # Chercher un magasin correspondant (matching exact ou fuzzy)
        best_match = None
        for store_name in stores.keys():
            if store_name.lower() == name.lower():
                best_match = store_name
                break

        # Si pas de match exact, chercher par similarité
        if best_match is None:
            for store_name in stores.keys():
                # Chercher un match partiel si le KML name contient le début du store name
                if store_name.lower() in name.lower() or name.lower() in store_name.lower():
                    best_match = store_name
                    break

        if best_match is None:
            # Essayer de chercher par première partie du nom
            name_parts = name.split()
            if len(name_parts) > 0:
                for store_name in stores.keys():
                    if name_parts[0].lower() in store_name.lower():
                        best_match = store_name
                        break

        if best_match is None:
            continue

        matched += 1
        store = stores[best_match]

        # Récupérer la description pour l'aire et les notes
        desc_el = placemark.find('kml:description', ns)
        if desc_el is not None and desc_el.text:
            desc = desc_el.text

            # Parser "XXX m² (YYY pi²)"
            area_match = re.search(r'(\d+[\s,]*\d*)\s*m²\s*\((\d+[\s,]*\d*)\s*pi²\)', desc)
            if area_match:
                m2_str = area_match.group(1).replace(' ', '').replace(',', '')
                pi2_str = area_match.group(2).replace(' ', '').replace(',', '')
                try:
                    store['Superficie_m2'] = int(float(m2_str))
                    store['Superficie_pi2'] = int(float(pi2_str))
                except ValueError:
                    pass

            # Extraire la source (OSM ou MS-Footprints)
            if 'Source: OSM' in desc:
                store['Source'] = 'OSM'
            elif 'Source: MS-Footprints' in desc:
                store['Source'] = 'MS-Footprints'

            # Extraire les notes
            store['Notes'] = desc

        # Récupérer les coordonnées du LookAt si pas déjà présentes
        if store['Latitude'] is None:
            lookat = placemark.find('kml:LookAt', ns)
            if lookat is not None:
                lat_el = lookat.find('kml:latitude', ns)
                lon_el = lookat.find('kml:longitude', ns)
                if lat_el is not None and lon_el is not None:
                    try:
                        store['Latitude'] = float(lat_el.text)
                        store['Longitude'] = float(lon_el.text)
                    except ValueError:
                        pass

    print(f"✓ {matched} magasins appairés avec le KML")

def main():
    if len(sys.argv) < 2:
        print("Usage: python timbermart_to_excel.py <geocoded.csv> [footprints.kml]")
        print("\nExemple:")
        print("  python timbermart_to_excel.py timbermart_stores_quebec_geocoded.csv Timber_Mart_Footprints.kml")
        sys.exit(1)

    csv_path = sys.argv[1]
    kml_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(csv_path).exists():
        print(f"❌ Fichier CSV non trouvé: {csv_path}")
        sys.exit(1)

    print(f"\n📊 Export Timbermart vers Excel\n")

    # Lire le CSV
    stores = read_geocoded_csv(csv_path)
    if stores is None:
        sys.exit(1)

    # Parser le KML si présent
    if kml_path and Path(kml_path).exists():
        print(f"Parsing KML: {kml_path}")
        parse_kml_footprints(kml_path, stores)

    # Créer le DataFrame
    data = list(stores.values())
    df = pd.DataFrame(data)

    # Reordonner les colonnes
    columns = ['Nom', 'Adresse', 'Ville', 'Province', 'Code postal', 'Téléphone', 'Heures',
               'Latitude', 'Longitude', 'Superficie_m2', 'Superficie_pi2', 'Source', 'Notes']
    df = df[[col for col in columns if col in df.columns]]

    # Renommer les colonnes pour l'affichage
    df = df.rename(columns={
        'Superficie_m2': 'Superficie (m²)',
        'Superficie_pi2': 'Superficie (pi²)',
    })

    # Exporter en Excel
    output_file = Path(csv_path).stem + '.xlsx'
    df.to_excel(output_file, index=False, sheet_name='Timbermart')

    print(f"\n✅ Excel créé: {output_file}")
    print(f"📊 {len(df)} magasins × {len(df.columns)} colonnes")

    # Résumé
    superficies = df['Superficie (m²)'].dropna()
    if len(superficies) > 0:
        print(f"\n📐 Superficies:")
        print(f"   Avec superficie: {len(superficies)}/{len(df)}")
        print(f"   Min: {superficies.min():>8.0f} m² ({superficies.min() * 10.7639:>8.0f} pi²)")
        print(f"   Max: {superficies.max():>8.0f} m² ({superficies.max() * 10.7639:>8.0f} pi²)")
        print(f"   Moy: {superficies.mean():>8.0f} m² ({superficies.mean() * 10.7639:>8.0f} pi²)")

    sources = df['Source'].value_counts()
    if len(sources) > 0:
        print(f"\n📍 Sources:")
        for source, count in sources.items():
            if pd.notna(source):
                print(f"   {source}: {count}")

    print()

if __name__ == '__main__':
    main()
