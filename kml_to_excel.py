#!/usr/bin/env python3
"""
Convertir KML avec superficies en Excel
========================================
Parse le KML Google Earth avec les superficies et exporte en Excel.
Calcule la superficie à partir des polygones.

Usage:
    python kml_to_excel.py Castle-Superficie-verifiee.kml
"""

import xml.etree.ElementTree as ET
import re
import pandas as pd
import sys
from pathlib import Path
import pyproj

# Géodésie
GEOD = pyproj.Geod(ellps="WGS84")

def aire_geodesique_m2(coords_lon_lat):
    """Calcule l'aire géodésique en m²."""
    if len(coords_lon_lat) < 3:
        return None
    lons = [c[0] for c in coords_lon_lat]
    lats = [c[1] for c in coords_lon_lat]
    aire, _ = GEOD.polygon_area_perimeter(lons, lats)
    return abs(aire)

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
            text = desc_el.text
            # Extraire le contenu CDATA si présent
            cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', text, re.DOTALL)
            if cdata_match:
                text = cdata_match.group(1)

            # Debug : afficher le texte brut pour les 2 premiers magasins
            if len(stores) < 2:
                print(f"\n[DEBUG {len(stores)}] Texte brut:\n{text[:500]}\n")

            # Split sur <br> pour obtenir les lignes
            lines = text.split('<br>')

            # Debug : afficher les lignes brutes
            if len(stores) < 2:
                print(f"[DEBUG] Lignes après split: {lines[:6]}\n")

            # Nettoyer chaque ligne : supprimer les tags HTML et whitespace
            lines = [re.sub('<[^>]+>', '', line).strip() for line in lines]
            lines = [line for line in lines if line]  # Supprimer les lignes vides

            # Debug : afficher les lignes nettoyées
            if len(stores) < 2:
                print(f"[DEBUG] Lignes nettoyées: {lines}\n")

            if len(lines) >= 4:
                store['Adresse'] = lines[0]
                store['Ville'] = lines[1]
                store['Province'] = lines[2]
                store['Code postal'] = lines[3]
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

        # Superficies depuis les polygones
        superficie_m2 = None

        # Chercher Polygon
        polygon = placemark.find('kml:Polygon', ns)
        if polygon is not None:
            outer = polygon.find('kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', ns)
            if outer is not None and outer.text:
                coords_text = outer.text.strip()
                coords = []
                for coord in coords_text.split():
                    parts = coord.split(',')
                    if len(parts) >= 2:
                        coords.append((float(parts[0]), float(parts[1])))

                if len(coords) >= 3:
                    superficie_m2 = aire_geodesique_m2(coords)

        # LineString (fallback)
        if superficie_m2 is None:
            linestring = placemark.find('kml:LineString', ns)
            if linestring is not None:
                coords_el = linestring.find('kml:coordinates', ns)
                if coords_el is not None and coords_el.text:
                    coords_text = coords_el.text.strip()
                    coords = []
                    for coord in coords_text.split():
                        parts = coord.split(',')
                        if len(parts) >= 2:
                            coords.append((float(parts[0]), float(parts[1])))

                    if len(coords) >= 3:
                        superficie_m2 = aire_geodesique_m2(coords)

        # Convertir en pi²
        store['Superficie (m²)'] = round(superficie_m2) if superficie_m2 else None
        store['Superficie (pi²)'] = round(superficie_m2 * 10.7639) if superficie_m2 else None

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
    columns = ['Nom', 'Adresse', 'Ville', 'Province', 'Code postal', 'Latitude', 'Longitude', 'Superficie (m²)', 'Superficie (pi²)']
    df = df[[col for col in columns if col in df.columns]]

    # Exporter en Excel
    output_file = Path(kml_file).stem + '.xlsx'
    df.to_excel(output_file, index=False, sheet_name='Magasins')

    print(f"✅ Excel créé : {output_file}")
    print(f"📊 {len(df)} lignes × {len(df.columns)} colonnes")

    # Résumé superficies
    superficies = df['Superficie (m²)'].dropna()
    if len(superficies) > 0:
        print(f"\n📐 Superficies :")
        print(f"   Min : {superficies.min():>8,.0f} m²  ({superficies.min() * 10.7639:>8,.0f} pi²)")
        print(f"   Max : {superficies.max():>8,.0f} m²  ({superficies.max() * 10.7639:>8,.0f} pi²)")
        print(f"   Moy : {superficies.mean():>8,.0f} m²  ({superficies.mean() * 10.7639:>8,.0f} pi²)")
        print(f"\n   Magasins avec superficie : {len(superficies)}/{len(df)}\n")

if __name__ == '__main__':
    main()
