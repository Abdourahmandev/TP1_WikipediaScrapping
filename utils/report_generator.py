from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

US_STATE_ABBR: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}


def _extract_first_year(value: str) -> int | None:
    match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", str(value))
    return int(match.group(1)) if match else None


def _extract_location(value: str) -> str:
    parts = [p.strip() for p in str(value).split(",")]
    return parts[-1] if parts else value


class ReportGenerator:
    def generate(self, db_path: str, output_path: str) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        con = duckdb.connect(db_path, read_only=True)
        df = con.execute("SELECT * FROM sp500_companies").fetchdf()
        scraped_at = con.execute("SELECT MAX(scraped_at) FROM sp500_companies").fetchone()[0]
        con.close()

        # --- Préparation des données ---
        df["founded_year"] = df["founded"].apply(_extract_first_year)
        df["added_year"] = df["date_added"].apply(_extract_first_year)
        df["location_last"] = df["headquarters_location"].apply(_extract_location)
        df["decade"] = df["founded_year"].apply(
            lambda y: f"{(int(y) // 10) * 10}s" if pd.notna(y) else None
        )

        total = len(df)
        n_sectors = df["gics_sector"].nunique()
        scraped_str = scraped_at.strftime("%Y-%m-%d %H:%M UTC") if scraped_at else "N/A"

        # --- Figure 1 : Entreprises par secteur ---
        sect = (
            df.groupby("gics_sector").size().reset_index(name="count")
            .sort_values("count")
        )
        fig1 = px.bar(
            sect, x="count", y="gics_sector", orientation="h",
            title="Entreprises par secteur GICS",
            labels={"count": "Nombre d'entreprises", "gics_sector": "Secteur"},
            color="count", color_continuous_scale="Blues",
        )
        fig1.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 2 : Top 10 sous-secteurs ---
        sub = (
            df.groupby("gics_sub_industry").size().reset_index(name="count")
            .sort_values("count", ascending=False).head(10).sort_values("count")
        )
        fig2 = px.bar(
            sub, x="count", y="gics_sub_industry", orientation="h",
            title="Top 10 sous-secteurs GICS",
            labels={"count": "Nombre d'entreprises", "gics_sub_industry": "Sous-secteur"},
            color="count", color_continuous_scale="Teal",
        )
        fig2.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 3 : Top 15 états US ---
        us_df = df[df["location_last"].isin(US_STATE_ABBR)].copy()
        state_counts = (
            us_df.groupby("location_last").size().reset_index(name="count")
            .sort_values("count", ascending=False).head(15).sort_values("count")
        )
        fig3 = px.bar(
            state_counts, x="count", y="location_last", orientation="h",
            title="Top 15 états US par nombre d'entreprises",
            labels={"count": "Nombre d'entreprises", "location_last": "État"},
            color="count", color_continuous_scale="Oranges",
        )
        fig3.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 4 : Carte choroplèthe ---
        state_all = us_df.groupby("location_last").size().reset_index(name="count")
        state_all["code"] = state_all["location_last"].map(US_STATE_ABBR)
        fig4 = go.Figure(go.Choropleth(
            locations=state_all["code"],
            z=state_all["count"],
            locationmode="USA-states",
            colorscale="Blues",
            colorbar_title="Entreprises",
        ))
        fig4.update_layout(
            title="Répartition géographique — États-Unis",
            geo_scope="usa",
            margin=dict(l=10, r=10, t=40, b=10),
        )

        # --- Figure 5 : Ajouts par année ---
        added = (
            df.dropna(subset=["added_year"])
            .groupby("added_year").size().reset_index(name="count")
        )
        added["added_year"] = added["added_year"].astype(int)
        fig5 = px.bar(
            added, x="added_year", y="count",
            title="Ajouts au S&P 500 par année",
            labels={"added_year": "Année", "count": "Nombre d'ajouts"},
            color="count", color_continuous_scale="Purples",
        )
        fig5.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 6 : Fondations par décennie ---
        decade_df = (
            df.dropna(subset=["decade"])
            .groupby("decade").size().reset_index(name="count")
            .sort_values("decade")
        )
        fig6 = px.bar(
            decade_df, x="decade", y="count",
            title="Fondations par décennie",
            labels={"decade": "Décennie", "count": "Nombre d'entreprises"},
            color="count", color_continuous_scale="Greens",
        )
        fig6.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 7 : Année moyenne de fondation par secteur ---
        avg_founded = (
            df.dropna(subset=["founded_year"])
            .groupby("gics_sector")["founded_year"].mean().reset_index()
        )
        avg_founded.columns = ["gics_sector", "avg_year"]
        avg_founded["avg_year"] = avg_founded["avg_year"].round(0).astype(int)
        avg_founded = avg_founded.sort_values("avg_year")
        fig7 = px.bar(
            avg_founded, x="avg_year", y="gics_sector", orientation="h",
            title="Année de fondation moyenne par secteur",
            labels={"avg_year": "Année moyenne", "gics_sector": "Secteur"},
            color="avg_year", color_continuous_scale="RdYlGn",
        )
        fig7.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Tableau 1 : 10 entreprises les plus anciennes ---
        oldest = (
            df.dropna(subset=["founded_year"]).nsmallest(10, "founded_year")
            [["symbol", "security", "gics_sector", "founded_year"]].copy()
        )
        oldest["founded_year"] = oldest["founded_year"].astype(int)
        fig8 = go.Figure(go.Table(
            header=dict(
                values=["Symbole", "Entreprise", "Secteur", "Fondée"],
                fill_color="#1a3c5e", font=dict(color="white", size=12), height=32,
            ),
            cells=dict(
                values=[oldest[c].tolist() for c in oldest.columns],
                fill_color="#f0f4f8", height=28,
            ),
        ))
        fig8.update_layout(title="10 entreprises les plus anciennes", margin=dict(l=10, r=10, t=40, b=10))

        # --- Tableau 2 : 10 ajouts les plus récents ---
        recent = (
            df.sort_values("date_added", ascending=False).head(10)
            [["symbol", "security", "gics_sector", "date_added"]]
        )
        fig9 = go.Figure(go.Table(
            header=dict(
                values=["Symbole", "Entreprise", "Secteur", "Ajouté le"],
                fill_color="#2a6e3f", font=dict(color="white", size=12), height=32,
            ),
            cells=dict(
                values=[recent[c].tolist() for c in recent.columns],
                fill_color="#f0f8f0", height=28,
            ),
        ))
        fig9.update_layout(title="10 ajouts les plus récents", margin=dict(l=10, r=10, t=40, b=10))

        # --- Assemblage HTML ---
        def _div(fig: go.Figure) -> str:
            return fig.to_html(full_html=False, include_plotlyjs=False)

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rapport S&amp;P 500</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; background: #f5f7fa; margin: 0; color: #333; }}
    header {{ background: #1a3c5e; color: white; padding: 24px 40px; }}
    header h1 {{ margin: 0; font-size: 1.8rem; }}
    header p {{ margin: 6px 0 0; opacity: 0.75; font-size: 0.9rem; }}
    .container {{ max-width: 1300px; margin: 0 auto; padding: 28px 20px; }}
    .kpi-row {{ display: flex; gap: 20px; margin-bottom: 32px; flex-wrap: wrap; }}
    .kpi-card {{
      background: white; border-radius: 10px; padding: 22px 36px; flex: 1;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08); text-align: center; min-width: 160px;
    }}
    .kpi-card .value {{ font-size: 2.6rem; font-weight: bold; color: #1a3c5e; }}
    .kpi-card .label {{ font-size: 0.9rem; color: #777; margin-top: 6px; }}
    .section-title {{
      font-size: 1.15rem; font-weight: bold; color: #1a3c5e;
      margin: 36px 0 14px; border-left: 4px solid #1a3c5e; padding-left: 12px;
    }}
    .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
    .chart-card {{
      background: white; border-radius: 10px; padding: 16px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }}
    .chart-card-full {{
      background: white; border-radius: 10px; padding: 16px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 20px;
    }}
    footer {{ text-align: center; padding: 24px; font-size: 0.8rem; color: #aaa; }}
    @media (max-width: 768px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<header>
  <h1>Rapport S&amp;P 500 — Composantes</h1>
  <p>Source : Wikipedia &nbsp;|&nbsp; Dernière extraction : {scraped_str}</p>
</header>
<div class="container">

  <div class="section-title">Métriques clés</div>
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="value">{total}</div>
      <div class="label">Entreprises</div>
    </div>
    <div class="kpi-card">
      <div class="value">{n_sectors}</div>
      <div class="label">Secteurs GICS</div>
    </div>
  </div>

  <div class="section-title">Distribution sectorielle</div>
  <div class="chart-grid">
    <div class="chart-card">{_div(fig1)}</div>
    <div class="chart-card">{_div(fig2)}</div>
  </div>

  <div class="section-title">Géographie</div>
  <div class="chart-grid">
    <div class="chart-card">{_div(fig3)}</div>
    <div class="chart-card">{_div(fig4)}</div>
  </div>

  <div class="section-title">Analyse temporelle</div>
  <div class="chart-card-full">{_div(fig5)}</div>
  <div class="chart-grid">
    <div class="chart-card">{_div(fig6)}</div>
    <div class="chart-card">{_div(fig7)}</div>
  </div>

  <div class="section-title">Tableaux</div>
  <div class="chart-grid">
    <div class="chart-card">{_div(fig8)}</div>
    <div class="chart-card">{_div(fig9)}</div>
  </div>

</div>
<footer>Généré automatiquement le {generated_at}</footer>
</body>
</html>"""

        destination.write_text(html, encoding="utf-8")
        return destination
