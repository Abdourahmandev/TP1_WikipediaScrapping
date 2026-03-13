# Scraper Wikipedia – S&P 500

Ce projet extrait le tableau des **composantes du S&P 500** depuis :

https://en.wikipedia.org/wiki/List_of_S%26P_500_companies

Il repose sur une architecture orientée objet avec des responsabilités bien séparées :

- `wikipedia_client.py` : client HTTP pour récupérer le contenu HTML de la page
- `sp500_scraper.py` : parseur qui extrait les entreprises depuis le tableau Wikipedia
- `sp500_company.py` : modèle de données (`SP500Company`)
- `duckdb_loader.py` : insère les données dans une table DuckDB
- `csv_exporter.py` : exporte les données vers un fichier CSV (usage secondaire)
- `main.py` : point d'entrée principal

## Installation

```bash
pip install -r requirements.txt
```

## Exécution

Depuis le dossier `TP1_Wikipedia` :

```bash
python main.py
```

Fichier de sortie par défaut :

- `sp500.duckdb` — base de données DuckDB contenant la table `sp500_companies`

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
