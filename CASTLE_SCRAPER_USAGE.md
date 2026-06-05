# Castle Store Locator Scraper — Guide d'utilisation

Extraction automatisée des magasins québécois depuis le store locator Castle.

## 🚀 Utilisation rapide

### Option 1 : API directe (recommandée)

**Sur ta machine locale :**
```bash
python fetch_castle_api.py
```

Cela génère `castle_api_data.json` avec tous les magasins Castle.

Puis copie ce fichier dans l'environnement cloud et :
```bash
python scraper_castle_locator.py --api-json castle_api_data.json
```

**Résultat :** `castle_stores_quebec.csv`

---

## 📋 Détails techniques

### API Castle
Le site Castle utilise ces endpoints API :
- `POST /api/retailers/list/` — Récupère tous les magasins
- Structure des données : `{status, retailers[]}`

Chaque magasin contient :
```json
{
  "id": 1,
  "name": "Castle Montreal",
  "address": {
    "address": "1234 Boulevard",
    "city": "Montreal",
    "province": "Quebec",
    "postal-code": "H2X 1Y0"
  },
  "contact": {
    "phone": "(514) 555-0200",
    "email": "info@castle.ca"
  },
  "hours": {
    "monday-friday": {"type": "Monday - Friday", "display": "7:00 am - 6:00 pm"},
    "saturday": {"type": "Saturday", "display": "8:00 am - 5:00 pm"},
    "sunday": {"type": "Sunday", "display": "10:00 am - 4:00 pm"}
  }
}
```

### Filtrage
- ✅ Filtre automatiquement les magasins québécois
- ✅ Codes postaux QC : G, H, J, K, L, P, Q, R (première lettre)
- ✅ Extraction : nom, adresse, ville, code postal, heures, téléphone, email

---

## 🔧 Options du scraper

```bash
# Depuis fichier JSON API
python scraper_castle_locator.py --api-json castle_api_data.json

# Depuis fichier HTML rendu
python scraper_castle_locator.py --file castle_locator.html

# Avec navigateur (JavaScript)
python scraper_castle_locator.py --browser

# Depuis stdin (pipe)
curl https://castle.ca/fr/locator/ | python scraper_castle_locator.py --stdin
```

---

## 📊 Données extraites

Le CSV contient ces colonnes :
| Colonne | Description |
|---------|-------------|
| Nom | Nom du magasin |
| Adresse | Rue/adresse |
| Ville | Ville |
| Province | Province (toujours Québec) |
| Code postal | Code postal normalisé |
| Lundi | Heures lundi-vendredi |
| Samedi | Heures samedi |
| Dimanche | Heures dimanche |
| Téléphone | Numéro de téléphone |
| Email | Adresse email |

---

## 🔍 Dépannage

### L'API retourne 403 Forbidden
→ C'est normal dans les environnements cloud restreints
→ Solution : Exécute `fetch_castle_api.py` sur ta machine locale

### Pas de fichier JSON
→ Exécute d'abord : `python fetch_castle_api.py`
→ Puis copie `castle_api_data.json` dans cet environnement

### Aucun magasin trouvé
→ Vérifie que le JSON contient au moins des magasins québécois (G0R, H2X, etc)
→ Vérifiez la structure du JSON correspond au format attendu

---

## 📝 Exemple de test

```bash
# Test avec données d'exemple
python scraper_castle_locator.py --api-json castle_api_sample.json

# Vérifie le résultat
cat castle_stores_quebec.csv
```

---

## 🎯 Workflow complet

1. **Sur ta machine** (accès réseau complet) :
   ```bash
   python fetch_castle_api.py
   # Génère : castle_api_data.json
   ```

2. **Copie le fichier** vers l'environnement cloud

3. **Dans l'environnement cloud** :
   ```bash
   python scraper_castle_locator.py --api-json castle_api_data.json
   # Génère : castle_stores_quebec.csv
   ```

4. **Utilise le CSV** pour prospection, analyse, enrichissement

---

## 💡 Notes

- ✅ Filtre automatiquement pour Québec seulement
- ✅ Normalise les codes postaux (ex: G0R1M0 → G0R 1M0)
- ✅ Éxporte en CSV UTF-8 avec BOM (Excel-compatible)
- ⚠️ Les restrictions réseau du cloud empêchent l'API directe → fallback sur JSON local
- 🔄 Le scraper supporte HTML/JSON pour flexibilité

---

## 🔗 Fichiers du projet

- `scraper_castle_locator.py` — Scraper principal
- `fetch_castle_api.py` — Helper pour télécharger l'API
- `castle_api_sample.json` — Données d'exemple pour test
- `castle_stores_quebec.csv` — Résultat d'extraction
