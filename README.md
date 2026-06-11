# Little Project on Human Values

> Exploring what people across Europe value - and why it differs.

An interactive data dashboard built with Python and Plotly Dash, visualising [Schwartz basic human values](https://scholar.google.com/citations?view_op=view_citation&hl=en&user=7gi3pqoAAAAJ&citation_for_view=7gi3pqoAAAAJ:d1gkVwhDpl0C) across the 30 countries of the **European Social Survey Round 11 (2023)** - from the national level down to regions and social groups.

**[→ Live demo](https://little-project-on-human-values.onrender.com)**

---

## What it shows

The Schwartz model proposes that 10 basic human values - arranged in a circular structure - are universal across cultures. Neighbouring values reinforce each other; opposing values compete. The dashboard explores how value profiles differ across countries, within countries, and in relation to macro-level societal indicators - all based on the newest available ESS round.

| Tab | What you see |
|-----|-------------|
| **About** | Hero overview, theory background, data & methods documentation, honest limitations |
| **Country Profile** | Radar chart of one country's value profile (weighted Δ-scores), country facts card, and 12 structural indicators |
| **Country Deep Dive** | Regional choropleths for Germany (NUTS-1) and Switzerland (NUTS-2), regional correlates from Eurostat (GDP, unemployment, education, age, density), and social gradients (age, education, urbanisation, gender, religiosity, East/West Germany, Swiss language regions) |
| **Correlations** | FDR-corrected correlation heatmap (19 predictors × 4 dimensions), click-through scatter plots with OLS fit and 95 % CI, plus multilevel models (random country intercepts, ICC) that separate composition from context |
| **Value Space** | Countries projected into 2D by profile similarity (PCA + K-Means) with silhouette-based cluster validation |

---

## Methodology

- **Full PVQ-21**: all 21 portrait items with the standard ESS item-to-value mapping
- **Reverse-coding**: items recoded (7 − x) so higher = stronger endorsement
- **Person-centring (ipsatisation)**: scores centred at each respondent's own mean, following Schwartz's recommended procedure; respondents with < 16 valid items excluded
- **Survey weights**: all aggregates use the ESS analysis weight (`anweight`)
- **Multiple-comparison control**: heatmap stars reflect Benjamini-Hochberg FDR-adjusted q-values across all 76 simultaneous tests
- **Honest small-N handling**: regions with < 50 respondents are greyed out; regional correlations are labelled exploratory
- **Multilevel models**: statsmodels MixedLM with random country intercepts quantifies how much variance actually sits between countries (7-18 %)

---

## Tech stack

- **Python 3.12** - pandas, numpy, scipy, scikit-learn, statsmodels (precompute only)
- **Plotly Dash 4 + dash-mantine-components** - interactive charts and UI
- **Eurostat API + GISCO** - regional indicators and NUTS boundaries
- **Gunicorn / Render.com** - deployment

---

## Running locally

```bash
git clone https://github.com/christopher-vantis/human-values-project.git
cd human-values-project/dashboard

pip install -r requirements.txt
python app.py
```

Open [http://localhost:8050](http://localhost:8050) in your browser. The app runs entirely from the small precomputed datasets in `dashboard/precomputed/` - no raw data needed.

> **Regenerating the precomputed data** (requires the raw ESS11 CSV under `data/raw/ess/ESS11/`):
>
> ```bash
> python dashboard/export_precomputed.py   # country / regional / gradient aggregates
> python dashboard/build_regional.py       # GISCO GeoJSON + Eurostat regional indicators
> python dashboard/build_mlm.py            # multilevel model results
> ```

---

## Data sources

| Data | Source |
|------|--------|
| Value survey (PVQ-21) | [European Social Survey](https://www.europeansocialsurvey.org), Round 11 (2023) |
| Liberal Democracy Index | [V-Dem Project](https://v-dem.net), Country-Year Dataset v15 |
| Gini Index | [World Bank WDI](https://data.worldbank.org/indicator/SI.POV.GINI) + [Eurostat EU-SILC](https://ec.europa.eu/eurostat) |
| Unemployment | [World Bank WDI](https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS) (SL.UEM.TOTL.ZS) |
| GDP per Capita (PPP) | [World Bank WDI](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD) (NY.GDP.PCAP.PP.KD) |
| Government Expenditure | [Eurostat COFOG](https://ec.europa.eu/eurostat) (gov_10a_exp) |
| Regional indicators | [Eurostat](https://ec.europa.eu/eurostat) (nama_10r_2gdp, lfst_r_lfu3rt, edat_lfse_04, demo_r_pjanind2, demo_r_d3dens) |
| NUTS boundaries | [Eurostat GISCO](https://gisco-services.ec.europa.eu), NUTS 2021 |
| Structural indicators | Eurostat, EIGE, Transparency International, World Happiness Report, OECD, World Bank (documented in-app) |

**ESS data note:** Raw ESS microdata files are not included in this repository in accordance with the [ESS terms of use](https://www.europeansocialsurvey.org/data/conditions_of_use.html). The `precomputed/` folder contains only anonymised, aggregated derivatives.

---

## Project structure

```
dashboard/
  app.py               # Entry point: data loading, app init, all callbacks
  layouts.py           # Static layout objects and pure UI helpers
  data_pipeline.py     # ESS11 scoring, weighted aggregation, PCA/clustering
  theme.py             # Design tokens + shared Plotly template
  export_precomputed.py
  build_regional.py    # GISCO GeoJSON + Eurostat regional indicators
  build_mlm.py         # Multilevel (MixedLM) precompute
  build_indicators.py  # 12 structural indicators from external APIs
  build_gov_exp.py     # COFOG government expenditure dataset
  figures/
    radar.py           # Schwartz radar chart
    choropleth.py      # Regional choropleth + regional scatter
    gradients.py       # Social-gradient lollipop panel
    scatter.py         # Correlation heatmap + scatter (BH-FDR)
    value_space.py     # PCA value space with radar glyphs
  precomputed/         # Aggregated CSVs/GeoJSON/JSON deployed to the server
  assets/style.css     # Design system (mirrors theme.py tokens)
tests/
  test_statistics.py   # Statistical correctness suite (pytest)
```

---

## Theoretical background

- Schwartz, S. H. (1992). Universals in the content and structure of values. *Advances in Experimental Social Psychology, 25*, 1-65.
- Schwartz, S. H. (2012). An overview of the Schwartz theory of basic values. *Online Readings in Psychology and Culture, 2*(1).
- Schwartz, S. H., & Bardi, A. (2001). Value hierarchies across cultures. *Journal of Cross-Cultural Psychology, 32*(3), 268-290.
- Davidov, E., Schmidt, P., & Schwartz, S. H. (2008). Bringing values back in: The adequacy of the European Social Survey to measure values in 20 countries. *Public Opinion Quarterly, 72*(3), 420-445.

---

## License

[MIT](LICENSE)
