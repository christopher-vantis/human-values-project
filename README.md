# Little Project on Human Values

> Exploring what people across Europe value - and why it differs.

An interactive data dashboard built with Python and Plotly Dash, visualising [Schwartz basic human values](https://scholar.google.com/citations?view_op=view_citation&hl=en&user=7gi3pqoAAAAJ&citation_for_view=7gi3pqoAAAAJ:d1gkVwhDpl0C) across 39 European countries using data from the European Social Survey (ESS), Rounds 1–11 (2002–2023).

**[→ Live demo](https://little-project-on-human-values.onrender.com)**

---

## What it shows

The Schwartz model proposes that 10 basic human values - arranged in a circular structure - are universal across cultures. Neighbouring values reinforce each other; opposing values compete. The dashboard explores how these value profiles differ across countries, over time, and in relation to macro-level societal indicators.

| Tab | What you see |
|-----|-------------|
| **About** | Theory background, dataset documentation, data source coverage, and methodological limitations |
| **Country Profile** | Radar chart of one country's Schwartz value profile for a selected ESS round, plus a country facts card and 12 structural indicators (democracy, inequality, health, education, gender equality, and more) |
| **Correlations** | Correlation heatmap overview across all predictors and Schwartz dimensions; click any cell to drill into a scatter plot with OLS regression line and 95 % CI band |
| **Value Space** | Countries projected into 2D by profile similarity (PCA + K-Means), switchable across value profiles, macro indicators, and government spending dimensions |
| **Parallel Coordinates** | 1 200 sampled ESS respondents coloured by dominant Schwartz dimension across 11 attitude axes; filter by dragging on any axis |

Each tab has a dedicated **Info** button in the sidebar with notes on the analytical approach and units of analysis.

---

## Tech stack

- **Python 3.12** - pandas, numpy, scipy, scikit-learn
- **Plotly Dash 2.18** - interactive charts and layout
- **Gunicorn** - WSGI server for deployment
- **Render.com** - hosting

---

## Running locally

```bash
# Clone the repository
git clone https://github.com/christopher-vantis/human-values-project.git
cd human-values-project/dashboard

# Install dependencies
pip install -r requirements.txt

# Run the app (uses precomputed datasets - no raw data needed)
python app.py
```

Open [http://localhost:8050](http://localhost:8050) in your browser.

> **Note for developers with raw ESS data:** If you have the original ESS CSV files and external macro datasets, place them under `data/raw/` and run `python dashboard/export_precomputed.py` from the project root to regenerate the derived datasets.

---

## Data sources

| Data | Source |
|------|--------|
| Value survey (PVQ-21) | [European Social Survey](https://www.europeansocialsurvey.org), Rounds 1–11, 2002–2023 |
| Liberal Democracy Index | [V-Dem Project](https://v-dem.net), Country-Year Dataset v15 |
| Gini Index | [World Bank WDI](https://data.worldbank.org/indicator/SI.POV.GINI) (SI.POV.GINI) + [Eurostat EU-SILC](https://ec.europa.eu/eurostat) |
| Unemployment | [World Bank WDI](https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS) (SL.UEM.TOTL.ZS) |
| GDP per Capita (PPP) | [World Bank WDI](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD) (NY.GDP.PCAP.PP.KD) |
| GDP per Capita (PPS) | [Eurostat](https://ec.europa.eu/eurostat) (tec00114) |
| Government Expenditure | [Eurostat COFOG](https://ec.europa.eu/eurostat) (gov_10a_exp) + World Bank (health, education, defence for non-EU) |
| Healthy Life Years | [Eurostat](https://ec.europa.eu/eurostat) (hlth_hlye) |
| Tertiary Education Attainment | [Eurostat](https://ec.europa.eu/eurostat) (edat_lfse_03) |
| Gender Equality Index | [EIGE](https://eige.europa.eu/gender-equality-index), EU27 member states |
| Trade Union Density | [OECD](https://stats.oecd.org) Labour Statistics |
| Corruption Perceptions Index | [Transparency International](https://www.transparency.org/en/cpi) |
| World Happiness Score | [World Happiness Report](https://worldhappiness.report) (Cantril Ladder) via Our World in Data |

**ESS data note:** Raw ESS microdata files are not included in this repository in accordance with the [ESS terms of use](https://www.europeansocialsurvey.org/data/conditions_of_use.html). The `precomputed/` folder contains only anonymised, aggregated derivatives.

---

## Project structure

```
dashboard/
  app.py              # Entry point: data loading, app init, all callbacks
  layouts.py          # Static layout objects and pure UI helpers
  data_pipeline.py    # Data loading, aggregation, PCA/clustering
  build_indicators.py # Fetch 12 structural indicators from external APIs
  build_gov_exp.py    # Build government expenditure dataset (Eurostat + World Bank)
  export_precomputed.py
  figures/
    radar.py          # Schwartz radar charts
    scatter.py        # Correlation scatter + heatmap
    parallel.py       # Parallel coordinates
    value_space.py    # PCA value space with radar glyphs
  precomputed/        # Cached CSVs deployed to server (no raw data needed)
  assets/style.css
```

---

## Theoretical background

- Schwartz, S. H. (1992). Universals in the content and structure of values. *Advances in Experimental Social Psychology, 25*, 1–65.
- Schwartz, S. H. (2012). An overview of the Schwartz theory of basic values. *Online Readings in Psychology and Culture, 2*(1).

---

## License

[MIT](LICENSE)
