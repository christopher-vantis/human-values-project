# Little Project on Human Values

> Exploring what people across Europe value — and why it differs.

An interactive data dashboard built with Python and Plotly Dash, visualising [Schwartz basic human values](https://scholar.google.com/citations?view_op=view_citation&hl=en&user=7gi3pqoAAAAJ&citation_for_view=7gi3pqoAAAAJ:d1gkVwhDpl0C) across 14 European countries using data from the European Social Survey (ESS), Rounds 1–11 (2002–2023).

**[→ Live demo](https://little-project-on-human-values.onrender.com)**

---

## What it shows

The Schwartz model proposes that 10 basic human values — arranged in a circular structure — are universal across cultures. Neighbouring values reinforce each other; opposing values compete. The dashboard explores how these value profiles differ across countries, over time, and in relation to macro-level societal indicators.

| Tab | What you see |
|-----|-------------|
| **About** | Theory background, dataset documentation, and how to read the charts |
| **Country Profile** | Radar chart of one country's value profile for a selected ESS round |
| **Correlations** | Scatter plots: country-level predictors vs. Schwartz higher-order dimensions, with OLS regression and 95 % CI bands |
| **Value Space** | PCA projection of all 14 countries into 2D by value similarity, with K-Means clustering |
| **Individual Profiles** | Parallel coordinates: 1 200 sampled ESS respondents coloured by dominant value dimension |
| **Parallel Coordinates** | Country × round lines across Schwartz dimensions and macro indicators |

---

## Tech stack

- **Python 3.12** — pandas, numpy, scipy, scikit-learn
- **Plotly Dash 2.18** — interactive charts and layout
- **Gunicorn** — WSGI server for deployment
- **Render.com** — hosting

---

## Running locally

```bash
# Clone the repository
git clone https://github.com/christopher-vantis/human-values-project.git
cd human-values-project/dashboard

# Install dependencies
pip install -r requirements.txt

# Run the app (uses precomputed datasets — no raw data needed)
python app.py
```

Open [http://localhost:8050](http://localhost:8050) in your browser.

> **Note for developers with raw ESS data:** If you have the original ESS CSV files and external macro datasets, place them under `data/raw/` and run `python export_precomputed.py` to regenerate the derived datasets.

---

## Data sources

| Data | Source |
|------|--------|
| Value survey (PVQ-21) | [European Social Survey](https://www.europeansocialsurvey.org), Rounds 1–11, 2002–2023 |
| Liberal Democracy Index | [V-Dem Project](https://v-dem.net), Country-Year Dataset v15 |
| Gini Index | [World Bank WDI](https://data.worldbank.org/indicator/SI.POV.GINI) (SI.POV.GINI); gaps filled from [Eurostat EU-SILC](https://ec.europa.eu/eurostat) |
| Unemployment | [World Bank WDI](https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS) (SL.UEM.TOTL.ZS) |
| GDP per Capita (PPP) | [World Bank WDI](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD) (NY.GDP.PCAP.PP.KD) |
| Government Expenditure | [Eurostat COFOG](https://ec.europa.eu/eurostat/statistics-explained/index.php/Government_expenditure_by_function_%E2%80%93_COFOG) |

**ESS data note:** The raw ESS microdata files are not included in this repository in accordance with the [ESS terms of use](https://www.europeansocialsurvey.org/data/conditions_of_use.html). The `precomputed/` folder contains only anonymised, aggregated derivatives.

---

## Theoretical background

- Schwartz, S. H. (1992). Universals in the content and structure of values. *Advances in Experimental Social Psychology, 25*, 1–65.
- Schwartz, S. H. (2012). An overview of the Schwartz theory of basic values. *Online Readings in Psychology and Culture, 2*(1).

---

## License

[MIT](LICENSE)
