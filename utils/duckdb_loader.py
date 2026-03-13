from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from modele.sp500_company import SP500Company

# Mapping état US complet (nom → code 2 lettres)
_US_STATES: list[tuple[str, str]] = [
    ("Alabama", "AL"), ("Alaska", "AK"), ("Arizona", "AZ"), ("Arkansas", "AR"),
    ("California", "CA"), ("Colorado", "CO"), ("Connecticut", "CT"), ("Delaware", "DE"),
    ("Florida", "FL"), ("Georgia", "GA"), ("Hawaii", "HI"), ("Idaho", "ID"),
    ("Illinois", "IL"), ("Indiana", "IN"), ("Iowa", "IA"), ("Kansas", "KS"),
    ("Kentucky", "KY"), ("Louisiana", "LA"), ("Maine", "ME"), ("Maryland", "MD"),
    ("Massachusetts", "MA"), ("Michigan", "MI"), ("Minnesota", "MN"), ("Mississippi", "MS"),
    ("Missouri", "MO"), ("Montana", "MT"), ("Nebraska", "NE"), ("Nevada", "NV"),
    ("New Hampshire", "NH"), ("New Jersey", "NJ"), ("New Mexico", "NM"), ("New York", "NY"),
    ("North Carolina", "NC"), ("North Dakota", "ND"), ("Ohio", "OH"), ("Oklahoma", "OK"),
    ("Oregon", "OR"), ("Pennsylvania", "PA"), ("Rhode Island", "RI"), ("South Carolina", "SC"),
    ("South Dakota", "SD"), ("Tennessee", "TN"), ("Texas", "TX"), ("Utah", "UT"),
    ("Vermont", "VT"), ("Virginia", "VA"), ("Washington", "WA"), ("West Virginia", "WV"),
    ("Wisconsin", "WI"), ("Wyoming", "WY"), ("District of Columbia", "DC"),
]


class DuckDBLoader:

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    # ── couche Bronze ────────────────────────────────────────────────────────

    def _write_bronze(self, companies: list[SP500Company], bronze_dir: Path) -> None:
        """Écrit le JSON brut des données scrapées (sans transformation)."""
        bronze_dir.mkdir(parents=True, exist_ok=True)
        raw = [c.to_dict() for c in companies]
        (bronze_dir / "sp500_raw.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ── couche Silver ────────────────────────────────────────────────────────

    def _create_silver(self, con: duckdb.DuckDBPyConnection,
                       companies: list[SP500Company], scraped_at: datetime) -> None:
        con.execute("CREATE SCHEMA IF NOT EXISTS silver")

        # Table de référence des États US
        con.execute("""
            CREATE OR REPLACE TABLE silver.us_states (
                state_name VARCHAR,
                state_code VARCHAR
            )
        """)
        con.executemany(
            "INSERT INTO silver.us_states VALUES (?, ?)",
            list(_US_STATES),
        )

        # Données brutes des entreprises S&P 500
        con.execute("""
            CREATE OR REPLACE TABLE silver.sp500_companies (
                symbol                VARCHAR,
                security              VARCHAR,
                gics_sector           VARCHAR,
                gics_sub_industry     VARCHAR,
                headquarters_location VARCHAR,
                date_added            VARCHAR,
                cik                   VARCHAR,
                founded               VARCHAR,
                scraped_at            TIMESTAMP
            )
        """)
        rows = [
            (c.symbol, c.security, c.gics_sector, c.gics_sub_industry,
             c.headquarters_location, c.date_added, c.cik, c.founded, scraped_at)
            for c in companies
        ]
        con.executemany("INSERT INTO silver.sp500_companies VALUES (?,?,?,?,?,?,?,?,?)", rows)

    # ── couche Gold ──────────────────────────────────────────────────────────

    def _create_gold(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("CREATE SCHEMA IF NOT EXISTS gold")
        # Nettoyage de l'ancienne table dans le schema par défaut (migration)
        con.execute("DROP TABLE IF EXISTS main.sp500_companies")

        # Table enrichie : colonnes dérivées calculées via SQL
        # Note : DuckDB utilise RE2 -- pas de \b, le groupe 1 capture la 1re année valide
        # CTE pour pouvoir réutiliser founded_year dans decade_label sans le recalculer
        con.execute("""
            CREATE OR REPLACE TABLE gold.companies_enriched AS
            WITH base AS (
                SELECT
                    symbol, security, gics_sector, gics_sub_industry,
                    headquarters_location, date_added, cik, founded, scraped_at,
                    TRY_CAST(
                        regexp_extract(founded, '(1[0-9]{3}|20[0-9]{2})', 1)
                    AS INTEGER) AS founded_year,
                    TRY_CAST(
                        regexp_extract(date_added, '(1[0-9]{3}|20[0-9]{2})', 1)
                    AS INTEGER) AS added_year,
                    TRIM(list_last(string_split(headquarters_location, ','))) AS state
                FROM silver.sp500_companies
            )
            SELECT
                *,
                CASE
                    WHEN founded_year IS NOT NULL
                    THEN CONCAT(CAST((founded_year // 10) * 10 AS VARCHAR), 's')
                    ELSE NULL
                END AS decade_label
            FROM base
        """)

        # KPI scalaires (1 ligne)
        con.execute("""
            CREATE OR REPLACE TABLE gold.kpi AS
            SELECT
                COUNT(*)                        AS total_companies,
                COUNT(DISTINCT gics_sector)     AS n_sectors,
                COUNT(DISTINCT gics_sub_industry) AS n_sub_industries,
                MAX(scraped_at)                 AS last_scraped_at,
                MIN(founded_year)               AS oldest_founded,
                MAX(founded_year)               AS newest_founded
            FROM gold.companies_enriched
        """)

        # Agrégat par secteur
        con.execute("""
            CREATE OR REPLACE TABLE gold.by_sector AS
            SELECT
                gics_sector,
                COUNT(*)                        AS n,
                CAST(ROUND(AVG(founded_year), 0) AS INTEGER) AS avg_founded_year
            FROM gold.companies_enriched
            GROUP BY gics_sector
            ORDER BY n ASC
        """)

        # Agrégat par sous-secteur (décroissant)
        con.execute("""
            CREATE OR REPLACE TABLE gold.by_sub_industry AS
            SELECT
                gics_sub_industry,
                COUNT(*) AS n
            FROM gold.companies_enriched
            GROUP BY gics_sub_industry
            ORDER BY n DESC
        """)

        # Agrégat géographique (JOIN avec la table de référence)
        con.execute("""
            CREATE OR REPLACE TABLE gold.by_state AS
            SELECT
                u.state_name,
                u.state_code,
                COUNT(*) AS n
            FROM gold.companies_enriched e
            JOIN silver.us_states u ON e.state = u.state_name
            GROUP BY u.state_name, u.state_code
            ORDER BY n DESC
        """)

        # Agrégat par année d'ajout
        con.execute("""
            CREATE OR REPLACE TABLE gold.by_added_year AS
            SELECT
                added_year,
                COUNT(*) AS n
            FROM gold.companies_enriched
            WHERE added_year IS NOT NULL
            GROUP BY added_year
            ORDER BY added_year ASC
        """)

        # Agrégat par décennie de fondation
        con.execute("""
            CREATE OR REPLACE TABLE gold.by_founded_decade AS
            SELECT
                decade_label,
                COUNT(*) AS n
            FROM gold.companies_enriched
            WHERE decade_label IS NOT NULL
            GROUP BY decade_label
            ORDER BY decade_label ASC
        """)

    # ── point d'entrée ───────────────────────────────────────────────────────

    def load(self, companies: list[SP500Company]) -> Path:
        destination = Path(self.db_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Bronze : JSON brut dans data/bronze/
        bronze_dir = destination.parent / "bronze"
        self._write_bronze(companies, bronze_dir)

        scraped_at = datetime.now(timezone.utc)

        with duckdb.connect(str(destination)) as con:
            self._create_silver(con, companies, scraped_at)
            self._create_gold(con)

        return destination
