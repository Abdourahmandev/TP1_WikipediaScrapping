from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import plotly.express as px
import plotly.graph_objects as go


class ReportGenerator:
    def generate(self, db_path: str, output_path: str) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        con = duckdb.connect(db_path, read_only=True)

        # --- KPIs depuis gold.kpi (1 ligne scalaire) ---
        kpi = con.execute("SELECT * FROM gold.kpi").fetchone()
        total, n_sectors, n_sub_industries, last_scraped_at, oldest_founded, newest_founded = kpi
        scraped_str = last_scraped_at.strftime("%Y-%m-%d %H:%M UTC") if last_scraped_at else "N/A"

        # --- Figure 1 : Entreprises par secteur ---
        rows = con.execute(
            "SELECT gics_sector, n FROM gold.by_sector ORDER BY n ASC"
        ).fetchall()
        fig1 = px.bar(
            {"sector": [r[0] for r in rows], "n": [r[1] for r in rows]},
            x="n", y="sector", orientation="h",
            title="Entreprises par secteur GICS",
            labels={"n": "Nombre d'entreprises", "sector": "Secteur"},
            color="n", color_continuous_scale="Blues",
        )
        fig1.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 2 : Top 10 sous-secteurs ---
        rows = con.execute(
            "SELECT gics_sub_industry, n FROM gold.by_sub_industry ORDER BY n ASC LIMIT 10"
        ).fetchall()
        fig2 = px.bar(
            {"sub": [r[0] for r in rows], "n": [r[1] for r in rows]},
            x="n", y="sub", orientation="h",
            title="Top 10 sous-secteurs GICS",
            labels={"n": "Nombre d'entreprises", "sub": "Sous-secteur"},
            color="n", color_continuous_scale="Teal",
        )
        fig2.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 3 : Top 15 états US ---
        rows = con.execute(
            "SELECT state_name, n FROM gold.by_state ORDER BY n ASC LIMIT 15"
        ).fetchall()
        fig3 = px.bar(
            {"state": [r[0] for r in rows], "n": [r[1] for r in rows]},
            x="n", y="state", orientation="h",
            title="Top 15 états US par nombre d'entreprises",
            labels={"n": "Nombre d'entreprises", "state": "État"},
            color="n", color_continuous_scale="Oranges",
        )
        fig3.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 4 : Carte choroplèthe ---
        rows = con.execute(
            "SELECT state_code, n FROM gold.by_state"
        ).fetchall()
        fig4 = go.Figure(go.Choropleth(
            locations=[r[0] for r in rows],
            z=[r[1] for r in rows],
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
        rows = con.execute(
            "SELECT added_year, n FROM gold.by_added_year ORDER BY added_year ASC"
        ).fetchall()
        fig5 = px.bar(
            {"year": [r[0] for r in rows], "n": [r[1] for r in rows]},
            x="year", y="n",
            title="Ajouts au S&P 500 par année",
            labels={"year": "Année", "n": "Nombre d'ajouts"},
            color="n", color_continuous_scale="Purples",
        )
        fig5.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 6 : Fondations par décennie ---
        rows = con.execute(
            "SELECT decade_label, n FROM gold.by_founded_decade ORDER BY decade_label ASC"
        ).fetchall()
        fig6 = px.bar(
            {"decade": [r[0] for r in rows], "n": [r[1] for r in rows]},
            x="decade", y="n",
            title="Fondations par décennie",
            labels={"decade": "Décennie", "n": "Nombre d'entreprises"},
            color="n", color_continuous_scale="Greens",
        )
        fig6.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Figure 7 : Année moyenne de fondation par secteur ---
        rows = con.execute(
            "SELECT gics_sector, avg_founded_year FROM gold.by_sector"
            " WHERE avg_founded_year IS NOT NULL ORDER BY avg_founded_year ASC"
        ).fetchall()
        fig7 = px.bar(
            {"sector": [r[0] for r in rows], "avg_year": [r[1] for r in rows]},
            x="avg_year", y="sector", orientation="h",
            title="Année de fondation moyenne par secteur",
            labels={"avg_year": "Année moyenne", "sector": "Secteur"},
            color="avg_year", color_continuous_scale="RdYlGn",
        )
        fig7.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=40, b=10))

        # --- Tableau 1 : 10 entreprises les plus anciennes ---
        rows = con.execute("""
            SELECT symbol, security, gics_sector, founded_year
            FROM gold.companies_enriched
            WHERE founded_year IS NOT NULL
            ORDER BY founded_year ASC
            LIMIT 10
        """).fetchall()
        fig8 = go.Figure(go.Table(
            header=dict(
                values=["Symbole", "Entreprise", "Secteur", "Fondée"],
                fill_color="#1a3c5e", font=dict(color="white", size=12), height=32,
            ),
            cells=dict(
                values=[[r[i] for r in rows] for i in range(4)],
                fill_color="#f0f4f8", height=28,
            ),
        ))
        fig8.update_layout(title="10 entreprises les plus anciennes", margin=dict(l=10, r=10, t=40, b=10))

        # --- Tableau 2 : 10 ajouts les plus récents ---
        rows = con.execute("""
            SELECT symbol, security, gics_sector, date_added
            FROM silver.sp500_companies
            ORDER BY date_added DESC
            LIMIT 10
        """).fetchall()
        fig9 = go.Figure(go.Table(
            header=dict(
                values=["Symbole", "Entreprise", "Secteur", "Ajouté le"],
                fill_color="#2a6e3f", font=dict(color="white", size=12), height=32,
            ),
            cells=dict(
                values=[[r[i] for r in rows] for i in range(4)],
                fill_color="#f0f8f0", height=28,
            ),
        ))
        fig9.update_layout(title="10 ajouts les plus récents", margin=dict(l=10, r=10, t=40, b=10))

        con.close()

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
