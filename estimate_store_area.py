#!/usr/bin/env python3
"""
Estimation Superficie Commerces — Castle Québec
================================================
Estime la superficie des magasins Castle via Overpass API (OSM) et Microsoft Building Footprints.

Sources (par ordre de priorité) :
  1. Overpass API (OpenStreetMap) — données vérifiées par la communauté
  2. Microsoft Canadian Building Footprints — fallback IA satellite

Utilisation:
    python estimate_store_area.py <fichier_geocoded.csv>

Génère : <fichier>_with_area.csv
"""

import argparse
import csv
import json
import sys
import time
import zipfile
from pathlib import Path

import pyproj
import requests
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

# ── Constantes ────────────────────────────────────────────────────────────────
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
OVERPASS_MAX_ECHECS = 3

RAYONS_TENTATIVE = [50, 100, 200]
DELAI_REQUETE = 1.2

MS_ZIP_URL = (
    "https://ngci.encs.concordia.ca/ckan/dataset/"
    "e0e13165-7c03-4ba8-ba57-c250fc820eb6/resource/"
    "bbf06684-5bfa-41f3-8368-c1f72a50382b/download/quebec.zip"
)
CACHE_DIR = Path.home() / ".cache" / "superficie-commerces"
MS_ZIP_PATH = CACHE_DIR / "quebec.zip"
MS_JSON_PATH = CACHE_DIR / "Quebec.geojson"

GEOD = pyproj.Geod(ellps="WGS84")

# État Overpass
_overpass_idx = 0
_overpass_echecs_suite = 0
_overpass_desactive = False


# ── Géodésie ──────────────────────────────────────────────────────────────────
def aire_geodesique_m2(coords_lon_lat):
    """Calcule l'aire géodésique en m²."""
    lons = [c[0] for c in coords_lon_lat]
    lats = [c[1] for c in coords_lon_lat]
    aire, _ = GEOD.polygon_area_perimeter(lons, lats)
    return abs(aire)


# ── Overpass API ──────────────────────────────────────────────────────────────
def requete_overpass(lat, lon, rayon):
    """Interroge Overpass API avec rotation de miroirs."""
    global _overpass_idx, _overpass_echecs_suite, _overpass_desactive

    if _overpass_desactive:
        return None

    query = f"""
[out:json][timeout:30];
(
  way(around:{rayon},{lat},{lon})[building];
  relation(around:{rayon},{lat},{lon})[building];
);
out geom;
"""

    for tentative in range(len(OVERPASS_URLS)):
        url = OVERPASS_URLS[(_overpass_idx + tentative) % len(OVERPASS_URLS)]
        try:
            resp = requests.post(url, data={"data": query}, timeout=35,
                                headers={"User-Agent": "castle-area-estimator/1.0"})
            resp.raise_for_status()
            _overpass_echecs_suite = 0
            _overpass_idx = (_overpass_idx + tentative) % len(OVERPASS_URLS)
            return resp.json()
        except requests.RequestException:
            continue

    _overpass_echecs_suite += 1
    _overpass_idx = (_overpass_idx + 1) % len(OVERPASS_URLS)

    if _overpass_echecs_suite >= OVERPASS_MAX_ECHECS:
        _overpass_desactive = True
        print(f"\n⚠️  Overpass inaccessible après {OVERPASS_MAX_ECHECS} échecs.",
              file=sys.stderr)

    return None


def meilleur_batiment_osm(lat, lon, elements):
    """Trouve le meilleur bâtiment OSM pour une coordonnée."""
    point_cible = Point(lon, lat)
    meilleur = None
    dist_min = float("inf")

    for el in elements:
        if el.get("type") not in ("way", "relation"):
            continue

        if el["type"] == "way":
            coords = [(g["lon"], g["lat"]) for g in el.get("geometry", []) if "lon" in g]
        else:
            coords = []
            for m in el.get("members", []):
                if m.get("role") == "outer":
                    coords = [(g["lon"], g["lat"]) for g in m.get("geometry", []) if "lon" in g]
                    if coords:
                        break

        if len(coords) < 3:
            continue

        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)

        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda p: p.area)

        if poly.contains(point_cible):
            return {"coords": coords, "tags": el.get("tags", {}), "contient": True}

        dist = poly.exterior.distance(point_cible)
        if dist < dist_min:
            dist_min = dist
            meilleur = {"coords": coords, "tags": el.get("tags", {}), "contient": False}

    return meilleur


def chercher_osm(lat, lon):
    """Cherche la superficie dans OpenStreetMap."""
    for rayon in RAYONS_TENTATIVE:
        data = requete_overpass(lat, lon, rayon)
        if data is None:
            continue

        elements = data.get("elements", [])
        if not elements:
            continue

        bat = meilleur_batiment_osm(lat, lon, elements)
        if bat is None or not bat["contient"]:
            continue

        aire = aire_geodesique_m2(bat["coords"])
        if aire < 10:
            continue

        niveaux = int(bat["tags"].get("building:levels", 1))
        return {
            "superficie_m2": round(aire * niveaux),
            "superficie_pi2": round(aire * niveaux * 10.7639),
            "source": "OSM",
            "note": f"OSM | {niveaux} niveaux" if niveaux > 1 else "OSM",
        }

    return None


# ── Microsoft Building Footprints ──────────────────────────────────────────────
class MSFootprints:
    def __init__(self):
        self._polygones = []
        self._coords_list = []
        self._tree = None
        self._charge = False

    def _telecharger(self):
        """Télécharge et extrait les données Microsoft."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        if not MS_ZIP_PATH.exists():
            print(f"\n📥 Téléchargement Microsoft Building Footprints Québec (~300 MB)...\n")
            try:
                with requests.get(MS_ZIP_URL, stream=True, timeout=300,
                                 headers={"User-Agent": "castle-area-estimator/1.0"}) as r:
                    r.raise_for_status()
                    total = int(r.headers.get("content-length", 0))
                    downloaded = 0
                    with open(MS_ZIP_PATH, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                pct = downloaded / total * 100
                                mb = downloaded // 1024 // 1024
                                print(f"\r   {pct:5.1f}% ({mb} MB)", end="", flush=True)
                print("\n")
            except requests.RequestException as e:
                print(f"❌ Erreur : {e}", file=sys.stderr)
                return False

        if not MS_JSON_PATH.exists():
            print("📦 Extraction GeoJSON...")
            with zipfile.ZipFile(MS_ZIP_PATH, "r") as zf:
                geojson_names = [n for n in zf.namelist() if n.lower().endswith(".geojson")]
                if not geojson_names:
                    print("❌ Aucun .geojson dans le ZIP.", file=sys.stderr)
                    return False
                zf.extract(geojson_names[0], CACHE_DIR)
                extracted = CACHE_DIR / geojson_names[0]
                if extracted != MS_JSON_PATH:
                    extracted.rename(MS_JSON_PATH)

        return True

    def charger(self):
        """Charge l'index spatial."""
        if self._charge:
            return True

        if not self._telecharger():
            return False

        print("🗺️  Chargement index spatial Microsoft (1-2 min)...")
        try:
            with open(MS_JSON_PATH, encoding="utf-8") as f:
                data = json.load(f)

            polys, coords_list = [], []
            for feat in data.get("features", []):
                geom = feat.get("geometry", {})
                gtype = geom.get("type", "")
                rings = []

                if gtype == "Polygon":
                    rings = [geom["coordinates"][0]]
                elif gtype == "MultiPolygon":
                    rings = [p[0] for p in geom["coordinates"]]

                for ring in rings:
                    if len(ring) >= 3:
                        coords = [(c[0], c[1]) for c in ring]
                        poly = Polygon(coords)
                        if not poly.is_valid:
                            poly = poly.buffer(0)
                        if poly.geom_type == "MultiPolygon":
                            poly = max(poly.geoms, key=lambda p: p.area)
                        polys.append(poly)
                        coords_list.append(coords)

            self._polygones = polys
            self._coords_list = coords_list
            self._tree = STRtree(polys)
            self._charge = True
            print(f"   ✓ {len(polys):,} polygones indexés\n")
            return True

        except Exception as e:
            print(f"❌ Erreur chargement : {e}", file=sys.stderr)
            return False

    def chercher_batiment(self, lat, lon, rayons=(30, 60, 120)):
        """Cherche un bâtiment : containment d'abord, sinon le plus proche/plus gros."""
        if not self._charge:
            return None

        point_cible = Point(lon, lat)

        for rayon_m in rayons:
            delta = rayon_m / 111_000
            buffer = point_cible.buffer(delta)

            candidats = self._tree.query(buffer, predicate="intersects")

            # Vérifier si candidats est vide (gérer les arrays NumPy)
            if candidats is None or (hasattr(candidats, '__len__') and len(candidats) == 0):
                continue

            # Priorité 1 : polygone contenant le point
            for idx in candidats:
                if self._polygones[idx].contains(point_cible):
                    coords = self._coords_list[idx]
                    if aire_geodesique_m2(coords) >= 10:
                        return {"coords": coords, "contient": True, "distance_m": 0}

            # Priorité 2 : bâtiment le plus proche, en favorisant les gros
            # (le géocodage tombe souvent dans la rue devant le magasin)
            meilleur = None
            meilleur_score = None
            for idx in candidats:
                poly = self._polygones[idx]
                coords = self._coords_list[idx]
                aire = aire_geodesique_m2(coords)
                if aire < 40:  # ignorer cabanons et petites annexes
                    continue
                dist_m = poly.distance(point_cible) * 111_000
                # Score : distance pénalisée, taille bonifiée (plafonnée)
                score = dist_m - min(aire, 2000) / 100
                if meilleur_score is None or score < meilleur_score:
                    meilleur_score = score
                    meilleur = {"coords": coords, "contient": False,
                                "distance_m": round(dist_m)}

            if meilleur:
                return meilleur

        return None


# ── Traitement principal ──────────────────────────────────────────────────────
def estimer_superficie(lat, lon, ms):
    """Estime la superficie d'un magasin."""
    # 1. OSM
    res_osm = chercher_osm(lat, lon)
    if res_osm:
        return res_osm

    # 2. Microsoft
    if ms.charger():
        bat = ms.chercher_batiment(lat, lon, rayons=RAYONS_TENTATIVE)
        if bat:
            aire = aire_geodesique_m2(bat["coords"])
            if aire >= 10:
                if bat["contient"]:
                    note = "Microsoft (polygone contient le point)"
                else:
                    note = f"Microsoft (bâtiment le plus proche, ~{bat['distance_m']} m — à vérifier)"
                return {
                    "superficie_m2": round(aire),
                    "superficie_pi2": round(aire * 10.7639),
                    "source": "MS-Footprints",
                    "note": note,
                }

    return {"superficie_m2": None, "superficie_pi2": None, "source": "non_trouve", "note": ""}


def main():
    parser = argparse.ArgumentParser(description="Estime la superficie des magasins Castle")
    parser.add_argument("csv", help="Fichier CSV avec colonnes Latitude, Longitude")
    parser.add_argument("--rayons", type=int, nargs='+', default=[50, 100, 200],
                       help="Rayons de recherche en mètres (défaut: 50 100 200)")
    args = parser.parse_args()

    global RAYONS_TENTATIVE
    if args.rayons:
        RAYONS_TENTATIVE = args.rayons

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ Fichier non trouvé : {csv_path}", file=sys.stderr)
        sys.exit(1)

    # Détecter délimiteur
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        delimiter = ';' if ';' in first_line else ','

    # Lire le CSV
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)

    print(f"\n📍 Estimation superficie de {len(rows)} magasins\n")

    ms = MSFootprints()
    resultats = []

    for i, row in enumerate(rows, 1):
        nom = row.get('Nom', '').strip()
        ville = row.get('Ville', '').strip()
        lat = float(row.get('Latitude', 0))
        lon = float(row.get('Longitude', 0))

        print(f"[{i:>2}/{len(rows)}] {nom[:40]:<40} ({ville})", end=" ", flush=True)

        res = estimer_superficie(lat, lon, ms)

        row['Superficie_m2'] = res.get('superficie_m2', '')
        row['Superficie_pi2'] = res.get('superficie_pi2', '')
        row['Superficie_source'] = res.get('source', '')
        row['Superficie_note'] = res.get('note', '')

        resultats.append(row)

        if res.get('superficie_m2'):
            print(f"✅ {res['superficie_m2']:>6,} m²  ({res['source']})")
        else:
            print(f"❌ ({res['source']})")

        time.sleep(DELAI_REQUETE)

    # Exporter
    output_file = csv_path.stem + "_with_area.csv"
    fieldnames = list(rows[0].keys()) if rows else []
    fieldnames = [f for f in fieldnames if f]  # Supprimer None

    for new_field in ['Superficie_m2', 'Superficie_pi2', 'Superficie_source', 'Superficie_note']:
        if new_field not in fieldnames:
            fieldnames.append(new_field)

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(resultats)

    # Résumé
    superficies = [r['Superficie_m2'] for r in resultats if r.get('Superficie_m2')]
    print(f"\n✅ Résultats exportés : {output_file}\n")
    if superficies:
        print(f"📊 Superficie :")
        print(f"   Min : {min(superficies):>7,.0f} m²")
        print(f"   Max : {max(superficies):>7,.0f} m²")
        print(f"   Moy : {sum(superficies)/len(superficies):>7,.0f} m²\n")


if __name__ == '__main__':
    main()
