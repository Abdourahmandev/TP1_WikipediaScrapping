from __future__ import annotations

from pathlib import Path

from duckdb_loader import DuckDBLoader
from report_generator import ReportGenerator
from sp500_scraper import SP500Scraper


def run(db_path: str | None = None, report_path: str | None = None) -> str:
	target_db = db_path or str(Path(__file__).with_name("sp500.duckdb"))
	target_report = report_path or str(Path(__file__).with_name("report.html"))

	scraper = SP500Scraper()
	companies = scraper.scrape_companies()

	loader = DuckDBLoader(target_db)
	loader.load(companies)

	generator = ReportGenerator()
	destination = generator.generate(target_db, target_report)

	return f"Done: {len(companies)} companies — rapport généré : {destination}"


if __name__ == "__main__":
	print(run())
