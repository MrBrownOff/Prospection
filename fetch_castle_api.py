#!/usr/bin/env python3
"""
Castle API Data Fetcher — À exécuter chez toi
===============================================
Récupère les données de l'API Castle et les sauvegarde en JSON.

Utilisation :
    python fetch_castle_api.py

Génère : castle_api_data.json
"""

import requests
import json
from pathlib import Path

CASTLE_API_URL = "https://castle.ca/api/retailers/list/"

def fetch_api_data():
    """Récupère les données depuis l'API Castle."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        print("⏳ Appel de l'API Castle...")
        response = requests.post(CASTLE_API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur : {e}")
        return None

def main():
    print("\n🔄 Téléchargement des données Castle...\n")

    data = fetch_api_data()
    if not data:
        print("❌ Impossible de récupérer les données")
        return False

    # Sauvegarder en JSON
    output_file = "castle_api_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Données sauvegardées : {output_file}")

    # Résumé
    retailers = data.get('retailers', [])
    print(f"📊 {len(retailers)} magasins téléchargés")

    return True

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
