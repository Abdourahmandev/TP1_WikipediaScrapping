from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb

from sp500_company import SP500Company


class DuckDBLoader:
    TABLE_NAME = "sp500_companies"

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def load(self, companies: list[SP500Company]) -> Path:
        destination = Path(self.db_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        scraped_at = datetime.now(timezone.utc)

        with duckdb.connect(str(destination)) as con:
            con.execute(f"""
                CREATE OR REPLACE TABLE {self.TABLE_NAME} (
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
                (
                    c.symbol,
                    c.security,
                    c.gics_sector,
                    c.gics_sub_industry,
                    c.headquarters_location,
                    c.date_added,
                    c.cik,
                    c.founded,
                    scraped_at,
                )
                for c in companies
            ]

            con.executemany(
                f"INSERT INTO {self.TABLE_NAME} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )

        return destination
