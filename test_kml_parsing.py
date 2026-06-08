#!/usr/bin/env python3
"""Test script pour déboguer le parsing KML."""

import xml.etree.ElementTree as ET
import sys

kml_file = sys.argv[1] if len(sys.argv) > 1 else "Castle-Superficie-verifiee.kml"

print(f"🔍 Parsing: {kml_file}\n")

tree = ET.parse(kml_file)
root = tree.getroot()

print(f"Root tag: {root.tag}")
print(f"Root attribs: {root.attrib}\n")

# Afficher tous les namespaces trouvés
print("Namespaces dans le document:")
for prefix, uri in root.attrib.items():
    if prefix.startswith('{'):
        print(f"  {prefix}: {uri}")
print()

# Essayer différentes méthodes de recherche
print("=" * 60)
print("TEST 1: Chercher avec namespace explicite")
placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
print(f"✓ Trouvé {len(placemarks)} Placemarks\n")

if placemarks:
    pm = placemarks[0]
    print(f"Premier Placemark tag: {pm.tag}")
    print(f"Premier Placemark children:")
    for child in pm:
        print(f"  - {child.tag}: {child.text[:100] if child.text else '(vide)'}")
    print()

    # Tester l'extraction de la description
    print("=" * 60)
    print("TEST 2: Extraire description")
    desc = pm.find('{http://www.opengis.net/kml/2.2}description')
    if desc is not None and desc.text:
        print(f"✓ Description trouvée (longueur: {len(desc.text)})")
        print(f"Premiers 300 caractères:\n{desc.text[:300]}\n")

        # Tester le parsing
        text = desc.text
        import re

        # Extraire CDATA
        cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', text, re.DOTALL)
        if cdata_match:
            text = cdata_match.group(1)
            print("✓ CDATA extractée")

        # Normaliser les divs
        text_normalized = re.sub(r'</div><div>', '<br>', text)
        print(f"Après normalisation div: {text_normalized[:300]}\n")

        # Supprimer les tags sauf <br>
        text_clean = re.sub(r'<(?!/?br\s*/?)[^>]+>', '', text_normalized)
        print(f"Après suppression tags: {text_clean[:300]}\n")

        # Split sur <br>
        lines = re.split(r'<br\s*/?>', text_clean)
        lines = [line.strip() for line in lines if line.strip()]

        print(f"Lignes extraites: {len(lines)}")
        for i, line in enumerate(lines[:6]):
            print(f"  {i}: {line}")
    else:
        print("✗ Description NOT trouvée!")

    # Tester Polygon/coordinates
    print()
    print("=" * 60)
    print("TEST 3: Extraire Polygon")
    polygon = pm.find('{http://www.opengis.net/kml/2.2}Polygon')
    if polygon is not None:
        print("✓ Polygon trouvé")
        outer = polygon.find('{http://www.opengis.net/kml/2.2}outerBoundaryIs/{http://www.opengis.net/kml/2.2}LinearRing/{http://www.opengis.net/kml/2.2}coordinates')
        if outer is not None and outer.text:
            print(f"✓ Coordinates trouvées: {outer.text[:100]}...")
        else:
            print("✗ Coordinates NOT trouvées!")
    else:
        print("✗ Polygon NOT trouvé!")

else:
    print("✗ AUCUN Placemark trouvé!")
