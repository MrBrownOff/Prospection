"""
Castle API Finder — Détecte et utilise l'API directement
=========================================================
Script pour trouver et utiliser l'endpoint API du store locator Castle.

Utilisation :
    python castle_api_finder.py

Analyse le HTML de la page pour détecter les appels API et les utiliser directement.
"""

import requests
import re
import json

# HTML que l'utilisateur a fourni
HTML_SAMPLE = """..."""  # Will be read from stdin or file

def extract_api_endpoints(html):
    """Cherche les appels API dans le HTML et les scripts."""
    endpoints = []

    # Chercher les URLs d'API dans les attributs data-*
    api_urls = re.findall(r'data-api=["\']([^"\']+)["\']', html)
    endpoints.extend(api_urls)

    # Chercher les appels fetch() ou XMLHttpRequest
    fetch_calls = re.findall(r'fetch\(["\']([^"\']+)["\']', html)
    endpoints.extend(fetch_calls)

    # Chercher les appels jQuery.ajax
    ajax_calls = re.findall(r'(?:url|action)["\']?:\s*["\']([^"\']+)["\']', html)
    endpoints.extend(ajax_calls)

    # Chercher les patterns d'API courantes
    api_patterns = re.findall(r'https?://[^\s"\'<>]+/(?:api|rest|v\d+)[^\s"\'<>]*', html)
    endpoints.extend(api_patterns)

    return list(set(endpoints))

def test_endpoints(endpoints):
    """Teste les endpoints trouvés pour voir lesquels retournent des données."""
    print(f"\n🔍 Test de {len(endpoints)} endpoints trouvés:\n")

    for endpoint in endpoints[:10]:  # Limiter à 10 pour éviter les spam
        try:
            print(f"   📡 {endpoint[:60]}...", end=" ")
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, (list, dict)) and len(str(data)) > 100:
                        print(f"✅ (JSON, {len(str(data))} chars)")
                        return endpoint, data
                except:
                    if len(response.text) > 100:
                        print(f"✅ (HTML/Text, {len(response.text)} chars)")
                        return endpoint, response.text
            else:
                print(f"❌ ({response.status_code})")
        except Exception as e:
            print(f"❌ ({str(e)[:20]})")

    return None, None

def main():
    print("\n🔎 Castle API Finder\n")
    print("Étapes :")
    print("1. Ouvre https://castle.ca/fr/locator/ dans ton navigateur")
    print("2. Ouvre les outils de développement (F12)")
    print("3. Va à l'onglet 'Network'")
    print("4. Recharge la page (Ctrl+R)")
    print("5. Cherche les requêtes vers '/api/', '/rest/', ou des URLs avec 'location' ou 'store'")
    print("6. Copie le chemin de la requête (ex: /api/locations/)")
    print("\nOu, fournis directement le HTML paginé avec les magasins...\n")

    # Instructions avancées
    print("💡 Autre approche :")
    print("Depuis les outils dev, tu peux lancer :")
    print('   fetch("/api/locations").then(r => r.json()).then(d => console.log(d))')
    print("et copier la réponse JSON pour construire les données.")

if __name__ == '__main__':
    main()
