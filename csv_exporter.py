from __future__ import annotations

import csv
from pathlib import Path

from sp500_company import SP500Company


class CSVExporter:
    def export(self, companies: list[SP500Company], output_path: str) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "symbol",
            "security",
            "gics_sector",
            "gics_sub_industry",
            "headquarters_location",
            "date_added",
            "cik",
            "founded",
        ]

        with destination.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for company in companies:
                writer.writerow(company.to_dict())

        return destination
