#!/usr/bin/env python3
"""Nettoyer le CSV Timbermart malformé"""

import csv
import sys
import re
from pathlib import Path

def fix_csv(input_path, output_path=None):
    """Répare le CSV avec délimiteurs mixtes et données cassées"""

    if output_path is None:
        output_path = Path(input_path).stem + "_fixed.csv"

    print(f"📖 Lecture {input_path}...")

    # Lire le fichier brut (les délimiteurs sont mélangés)
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    if not lines:
        print("❌ Fichier vide")
        return

    # Parser chaque ligne manuellement
    rows = []
    header = None

    for i, line in enumerate(lines, 1):
        line = line.rstrip('\n\r')
        if not line.strip():
            continue

        # Ligne d'en-tête
        if i == 1:
            # Split sur ; puis sur ,
            parts = line.split(';')
            header = parts[:-1]  # Tout sauf la dernière partie qui contient "Latitude,Longitude"
            lat_lon = parts[-1] if len(parts) > 1 else ""
            if ',' in lat_lon:
                header.extend(lat_lon.split(','))
            header = [h.strip() for h in header]
            continue

        # Lignes de données
        # Split sur ;
        parts = line.split(';')

        # Récupérer les 6 premiers champs (Nom à Heures)
        if len(parts) < 6:
            print(f"⚠️  Ligne {i} : données insuffisantes, ignorée")
            continue

        nom = parts[0].strip()
        adresse = parts[1].strip()
        ville = parts[2].strip()
        province = parts[3].strip()
        code_postal = parts[4].strip()
        heures = parts[5].strip()

        # Les coordonnées sont dans la dernière partie (après la dernière ,)
        remaining = ";".join(parts[6:])
        coords = remaining.split(',')

        if len(coords) >= 2:
            try:
                lat = float(coords[-2].strip())
                lon = float(coords[-1].strip())
            except (ValueError, IndexError):
                print(f"⚠️  Ligne {i} ({nom}) : coords invalides, ignorée")
                continue
        else:
            print(f"⚠️  Ligne {i} ({nom}) : coords manquantes, ignorée")
            continue

        # Vérifier que c'est pas tout les mêmes coords (erreur de geocoding)
        if abs(lat - 52.476089) < 0.0001 and abs(lon - (-71.825867)) < 0.0001:
            print(f"⚠️  Ligne {i} ({nom}) : coords par défaut détectées (geocoding échoué)")
            # On les garde mais on notera l'erreur

        row = {
            'Nom': nom,
            'Adresse': adresse,
            'Ville': ville,
            'Province': province,
            'Code postal': code_postal,
            'Heures d\'ouverture': heures,
            'Latitude': lat,
            'Longitude': lon
        }
        rows.append(row)

    print(f"✓ {len(rows)} magasins extraits\n")

    # Écrire le CSV nettoyé
    fieldnames = ['Nom', 'Adresse', 'Ville', 'Province', 'Code postal', 'Heures d\'ouverture', 'Latitude', 'Longitude']

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ CSV nettoyé → {output_path}\n")
    print(f"⚠️  ATTENTION : {len([r for r in rows if abs(r['Latitude'] - 52.476089) < 0.0001])} magasins ont les coords par défaut")
    print(f"   → Il faut re-geocoder avec : python geocode_timbermart_stores.py {output_path}")

    return output_path

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_timbermart_csv.py <input.csv> [output.csv]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    fix_csv(input_path, output_path)
