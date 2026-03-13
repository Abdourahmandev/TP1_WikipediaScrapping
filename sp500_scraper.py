from __future__ import annotations

from bs4 import BeautifulSoup

from sp500_company import SP500Company
from wikipedia_client import WikipediaClient


class SP500Scraper:
    URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    def __init__(self, client: WikipediaClient | None = None) -> None:
        self.client = client or WikipediaClient()

    def scrape_companies(self) -> list[SP500Company]:
        html = self.client.fetch_html(self.URL)
        soup = BeautifulSoup(html, "html.parser")

        table = self._find_component_table(soup)
        rows = table.select("tbody tr")

        companies: list[SP500Company] = []
        for row in rows[1:]:
            cells = [cell.get_text(strip=True) for cell in row.select("td")]
            if len(cells) < 8:
                continue

            companies.append(
                SP500Company(
                    symbol=cells[0],
                    security=cells[1],
                    gics_sector=cells[2],
                    gics_sub_industry=cells[3],
                    headquarters_location=cells[4],
                    date_added=cells[5],
                    cik=cells[6],
                    founded=cells[7],
                )
            )

        return companies

    @staticmethod
    def _find_component_table(soup: BeautifulSoup):
        # This is the first wikitable in the article and contains current S&P 500 components.
        table = soup.select_one("table.wikitable")
        if table is None:
            raise ValueError("Could not find the S&P 500 components table on Wikipedia.")
        return table
