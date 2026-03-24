# Scraper Wikipedia – S&P 500

Ce projet extrait le tableau des **composantes du S&P 500** depuis :

https://en.wikipedia.org/wiki/List_of_S%26P_500_companies

Il repose sur une architecture orientée objet avec des responsabilités bien séparées.

## Architecture du projet

![Diagramme de flux du pipeline de données](data/Architecture_TP1.jpg)

### Structure des fichiers

```
TP1_Wikipedia/
├── modele/
│   ├── __init__.py
│   └── sp500_company.py       # Dataclass SP500Company (modèle de données)
├── utils/
│   ├── __init__.py
│   ├── wikipedia_client.py    # Client HTTP — récupère le HTML de Wikipedia
│   ├── sp500_scraper.py       # Parseur — extrait les entreprises du tableau
│   ├── duckdb_loader.py       # Couche Bronze/Silver/Gold dans DuckDB
│   └── report_generator.py    # Génère le rapport HTML (Plotly)
├── airflow/
│   ├── Dockerfile.airflow     # Image Airflow avec providers-docker
│   ├── docker-compose.yml     # Stack Airflow (webserver + scheduler + postgres)
│   ├── dags/
│   │   └── sp500_dag.py       # DAG quotidien (06:00 UTC) via DockerOperator
│   ├── logs/                  # Logs Airflow (généré automatiquement)
│   └── plugins/
├── data/
│   ├── sp500.duckdb           # Base de données DuckDB (généré automatiquement)
│   ├── report.html            # Rapport HTML interactif (généré automatiquement)
│   └── bronze/
│       └── sp500_raw.json     # Données brutes JSON (généré automatiquement)
├── .github/
│   └── workflows/
│       └── pipeline.yml       # CI/CD GitHub Actions (scraping + rapport + GitHub Pages + GHCR)
├── Dockerfile                 # Image Docker du pipeline principal
├── main.py                    # Point d'entrée principal
└── requirements.txt
```

## Installation

```bash
pip install -r requirements.txt
```

## Exécution

Depuis le dossier `TP1_Wikipedia` :

```bash
python main.py
```

Fichiers de sortie générés dans `data/` :

- `data/sp500.duckdb` — base de données DuckDB contenant la table `sp500_companies`
- `data/report.html` — rapport HTML interactif avec graphiques Plotly

## Colonnes de la table DuckDB

| Colonne | Description |
|---|---|
| `symbol` | Symbole boursier (ex. AAPL) |
| `security` | Nom de l'entreprise |
| `gics_sector` | Secteur GICS |
| `gics_sub_industry` | Sous-secteur GICS |
| `headquarters_location` | Siège social |
| `date_added` | Date d'ajout au S&P 500 |
| `cik` | Identifiant SEC (CIK) |
| `founded` | Année de fondation |
| `scraped_at` | Horodatage de l'extraction (UTC) |

## Orchestration avec Airflow

Le pipeline est orchestré par Apache Airflow via Docker Compose.

### Prérequis

- Docker Desktop en cours d'exécution
- Créer le volume de données partagé (une seule fois) :

```bash
docker volume create sp500-data
```

### Démarrage

```bash
cd airflow

# Première utilisation seulement — initialise la base de données et crée l'utilisateur admin
docker compose up airflow-init

# Démarrer la stack en arrière-plan
docker compose up -d
```

Accéder à l'interface Airflow : http://localhost:8081  
Identifiants : `admin` / `admin`

### DAG

Le DAG `sp500_daily_scrape` s'exécute automatiquement chaque jour à 06:00 UTC.  
Il lance le conteneur Docker du pipeline (`Dockerfile` à la racine) et monte le volume `sp500-data` dans `/app/data`.

Pour déclencher manuellement depuis l'interface, activer le DAG puis cliquer sur **Trigger DAG**.

### Arrêt

```bash
docker compose down
```
