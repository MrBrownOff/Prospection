"""
Scraper Castle Store Locator — Magasins québécois
===================================================
Script pour extraire les magasins québécois du store locator Castle.

Utilisation :
    Option 1 — Depuis un fichier HTML local :
        python scraper_castle_locator.py --file castle_locator.html

    Option 2 — Web scraping direct (si accès réseau disponible) :
        python scraper_castle_locator.py --url https://castle.ca/fr/locator/

    Option 3 — Depuis le HTML en stdin :
        cat castle_locator.html | python scraper_castle_locator.py --stdin

Fonctionnalités :
    - Extrait : nom, adresse, ville, code postal, heures d'ouverture
    - Filtre seulement les magasins québécois
    - Exporte en CSV
"""

import sys
import argparse
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
import json
import re

# ── CONFIG ───────────────────────────────────────────────────────────────────
OUTPUT_CSV    = "castle_stores_quebec.csv"

# Codes postaux québécois (première lettre)
QC_POSTAL_CODES = {'G', 'H', 'J', 'K', 'L', 'P', 'Q', 'R'}

# ── SCRAPER ──────────────────────────────────────────────────────────────────
def fetch_page(url):
    """Récupère le contenu HTML de la page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'fr-CA,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://castle.ca/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors du téléchargement : {e}")
        return None

def parse_postal_code(postal_string):
    """Extrait et normalise le code postal (ex: 'G0R 1M0' → 'G0R 1M0')."""
    if not postal_string:
        return None
    # Format: G0R 1M0 ou G0R1M0
    match = re.search(r'[A-Z]\d[A-Z]\s?\d[A-Z]\d', postal_string.upper())
    return match.group(0) if match else None

def is_quebec_store(postal_code):
    """Vérifie si le code postal est québécois."""
    if not postal_code:
        return False
    return postal_code[0] in QC_POSTAL_CODES

def parse_hours(dl_element):
    """Extrait les heures d'ouverture depuis un élément <dl>."""
    if not dl_element:
        return {}

    hours = {}
    dts = dl_element.find_all('dt')
    dds = dl_element.find_all('dd')

    for dt, dd in zip(dts, dds):
        day = dt.get_text(strip=True)
        time = dd.get_text(strip=True)
        hours[day] = time

    return hours

def extract_stores(html):
    """Parse le HTML et extrait les informations des magasins."""
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    stores = []

    # Chercher tous les conteneurs de détails
    details_containers = soup.find_all('div', class_='details')

    print(f"🔍 {len(details_containers)} conteneurs trouvés")

    for container in details_containers:
        try:
            # Structure : <div class="details">
            #              <div> (premier enfant)
            #                <h5>Nom</h5>
            #                <div>Adresse lines</div>
            #              </div>
            #              <div class="hours">Heures</div>
            #            </div>

            # Chercher le h5 (nom du magasin)
            h5 = container.find('h5')
            store_name = h5.get_text(strip=True) if h5 else None
            if not store_name:
                continue

            # Chercher l'adresse (div qui n'est pas 'hours')
            # Parcourir les enfants directs du container
            info_divs = [d for d in container.find_all('div', recursive=False)
                         if not d.get('class') or 'hours' not in d.get('class', [])]

            address_lines = []
            for info_div in info_divs:
                # Si la div contient le h5, c'est celle-ci qui contient aussi l'adresse
                if info_div.find('h5'):
                    # Trouver la div qui contient l'adresse (autre que celle avec h5)
                    addr_divs = info_div.find_all('div')
                    for addr_div in addr_divs:
                        if addr_div.find('h5'):  # C'est la div parente, pas celle-ci
                            continue
                        # Extraire le texte en respectant les BR
                        lines = []
                        for item in addr_div.children:
                            if isinstance(item, str):
                                text = item.strip()
                                if text:
                                    lines.append(text)
                            elif item.name == 'br':
                                # BR = nouvelle ligne
                                pass
                            else:
                                text = item.get_text(strip=True)
                                if text:
                                    lines.append(text)
                        # Extraire les lignes d'adresse avec BR
                        for br in addr_div.find_all('br'):
                            br.replace_with('|BR|')
                        full_text = addr_div.get_text(strip=True)
                        address_lines = [line.strip() for line in full_text.split('|BR|') if line.strip()]
                        break
                    break

            street = address_lines[0] if len(address_lines) > 0 else None
            city_prov = address_lines[1] if len(address_lines) > 1 else None
            postal = address_lines[2] if len(address_lines) > 2 else None

            # Parser ville et province
            city = None
            province = None
            if city_prov:
                parts = city_prov.split(',')
                city = parts[0].strip()
                province = parts[1].strip() if len(parts) > 1 else None

            # Normaliser le code postal
            postal_clean = parse_postal_code(postal) if postal else None

            # Vérifier si c'est québécois
            if not is_quebec_store(postal_clean):
                print(f"  ⏭️  {store_name} ({province}, {postal_clean}) — hors Québec")
                continue

            # Extraire les heures d'ouverture
            hours_div = container.find('div', class_='hours')
            hours = {}
            if hours_div:
                dl = hours_div.find('dl')
                hours = parse_hours(dl)

            # Créer un objet magasin
            store = {
                'Nom': store_name,
                'Adresse': street,
                'Ville': city,
                'Province': province,
                'Code postal': postal_clean,
                'Lundi': hours.get('Monday - Friday', ''),
                'Samedi': hours.get('Saturday', ''),
                'Dimanche': hours.get('Sunday', ''),
            }

            stores.append(store)
            print(f"  ✅ {store_name} | {city}, {postal_clean}")

        except Exception as e:
            print(f"  ⚠️  Erreur lors du parsing d'un magasin : {e}")
            import traceback
            traceback.print_exc()
            continue

    return stores

# ── ARGUMENTS ───────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description='Scraper Castle Store Locator — Magasins québécois',
        epilog='Exemples:\n'
               '  python scraper_castle_locator.py --file locator.html\n'
               '  python scraper_castle_locator.py --url https://castle.ca/fr/locator/',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--file', help='Lire depuis un fichier HTML local')
    parser.add_argument('--url', help='Scraper depuis une URL')
    parser.add_argument('--stdin', action='store_true', help='Lire depuis stdin')
    return parser.parse_args()

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    html = None

    if args.stdin:
        print("\n📥 Lecture depuis stdin...\n")
        html = sys.stdin.read()
    elif args.file:
        print(f"\n📂 Lecture du fichier {args.file}...\n")
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                html = f.read()
        except FileNotFoundError:
            print(f"❌ Fichier non trouvé : {args.file}")
            sys.exit(1)
    elif args.url:
        print(f"\n🌐 Scraping {args.url}...\n")
        html = fetch_page(args.url)
    else:
        # Par défaut, chercher un fichier local
        default_file = "castle_locator.html"
        if Path(default_file).exists():
            print(f"\n📂 Utilisation du fichier local {default_file}...\n")
            with open(default_file, 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            print("ℹ️  Aucune source spécifiée. Utilisation :")
            print("   python scraper_castle_locator.py --file castle_locator.html")
            print("   ou")
            print("   python scraper_castle_locator.py --url https://castle.ca/fr/locator/")
            sys.exit(1)

    if not html:
        sys.exit(1)

    # Parser les magasins
    stores = extract_stores(html)

    if not stores:
        print("\n❌ Aucun magasin trouvé")
        sys.exit(1)

    # Créer un DataFrame
    df = pd.DataFrame(stores)

    # Résumé
    print(f"\n{'='*60}")
    print(f"✅ Scraping terminé")
    print(f"   Magasins québécois trouvés : {len(df)}")
    print(f"\n📊 Résumé par ville :")
    for ville, count in df['Ville'].value_counts().items():
        print(f"   {ville} : {count}")

    # Export CSV
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n💾 CSV exporté : {OUTPUT_CSV}")
    print(f"   Colonnes : {', '.join(df.columns)}")

if __name__ == '__main__':
    main()
