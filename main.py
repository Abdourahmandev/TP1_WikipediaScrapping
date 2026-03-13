from __future__ import annotations

from pathlib import Path

from duckdb_loader import DuckDBLoader
from sp500_scraper import SP500Scraper


def run(db_path: str | None = None) -> str:
	target_db = db_path or str(Path(__file__).with_name("sp500.duckdb"))

	scraper = SP500Scraper()
	companies = scraper.scrape_companies()

	loader = DuckDBLoader(target_db)
	destination = loader.load(companies)

	return f"Load complete: {len(companies)} companies inserted into {destination}"


if __name__ == "__main__":
	print(run())
