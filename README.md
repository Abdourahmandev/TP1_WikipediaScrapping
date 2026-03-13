# S&P 500 Wikipedia Scraper

This project scrapes the **S&P 500 component stocks** table from:

https://en.wikipedia.org/wiki/List_of_S%26P_500_companies

It uses an object-oriented design with separate responsibilities:

- `wikipedia_client.py`: HTTP client for fetching page HTML
- `sp500_scraper.py`: parser that extracts companies from the Wikipedia table
- `sp500_company.py`: data model (`SP500Company`)
- `csv_exporter.py`: writes the scraped data to CSV
- `main.py`: orchestration entry point

## Install

```bash
pip install requests beautifulsoup4
```

## Run

From the `TP1_Wikipedia` folder:

```bash
python main.py
```

Default output file:

- `sp500_companies.csv`

## CSV columns

- `symbol`
- `security`
- `gics_sector`
- `gics_sub_industry`
- `headquarters_location`
- `date_added`
- `cik`
- `founded`
