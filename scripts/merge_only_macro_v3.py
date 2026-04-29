import zipfile
import xml.etree.ElementTree as ET
import csv
import os

raw_macro_path = "/home/c-vantis/jd/40_projects/43_human_values_project/data/raw/makro"
target_dir = "/home/c-vantis/jd/40_projects/43_human_values_project/macro_data_merged"

# ISO mapping
name_to_iso = {
    'Albania': 'ALB', 'Austria': 'AUT', 'Belgium': 'BEL', 'Bulgaria': 'BGR',
    'Switzerland': 'CHE', 'Cyprus': 'CYP', 'Czechia': 'CZE', 'Czech Republic': 'CZE',
    'Germany': 'DEU', 'Denmark': 'DNK', 'Estonia': 'EST', 'Spain': 'ESP',
    'Finland': 'FIN', 'France': 'FRA', 'United Kingdom': 'GBR', 'Greece': 'GRC',
    'Croatia': 'HRV', 'Hungary': 'HUN', 'Ireland': 'IRL', 'Israel': 'ISR',
    'Iceland': 'ISL', 'Italy': 'ITA', 'Lithuania': 'LTU', 'Luxembourg': 'LUX',
    'Latvia': 'LVA', 'Montenegro': 'MNE', 'North Macedonia': 'MKD',
    'Netherlands': 'NLD', 'Norway': 'NOR', 'Poland': 'POL', 'Portugal': 'PRT',
    'Romania': 'ROU', 'Serbia': 'SRB', 'Russia': 'RUS', 'Sweden': 'SWE',
    'Slovenia': 'SVN', 'Slovakia': 'SVK', 'Turkey': 'TUR', 'Turkiye': 'TUR',
    'Ukraine': 'UKR', 'Kosovo': 'XKX',
}
target_iso3 = set(name_to_iso.values())

def parse_xlsx_simple(file_path):
    data = []
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            strings = []
            try:
                with z.open('xl/sharedStrings.xml') as f:
                    tree = ET.parse(f)
                    for si in tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                        t = si.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                        strings.append(t.text if t is not None else "")
            except: pass

            with z.open('xl/worksheets/sheet1.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for row in root.findall('.//ns:row', ns):
                    row_list = [""] * 100
                    for cell in row.findall('ns:c', ns):
                        ref = cell.get('r')
                        col_letter = "".join(filter(str.isalpha, ref))
                        col_idx = 0
                        for char in col_letter: col_idx = col_idx * 26 + (ord(char) - ord('A') + 1)
                        col_idx -= 1
                        v = cell.find('ns:v', ns)
                        t = cell.get('t')
                        val = v.text if v is not None else ""
                        if t == 's' and val:
                            try: val = strings[int(val)]
                            except: val = ""
                        elif t == 'inlineStr':
                            t_tag = cell.find('.//ns:t', ns)
                            val = t_tag.text if t_tag is not None else ""
                        if col_idx < 100: row_list[col_idx] = val
                    data.append(row_list)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    return data

def extract_from_rows(rows, indicator_keyword=None):
    results = {}
    year_cols = {}
    start_row = 0
    for i, row in enumerate(rows):
        y_found = {j: val.strip() for j, val in enumerate(row) if val and str(val).strip().isdigit() and 1990 <= int(str(val).strip()) <= 2025}
        if len(y_found) > 5:
            year_cols = y_found
            start_row = i + 1
            break
    if not year_cols: return results
    for row in rows[start_row:]:
        if not row[0]: continue
        country = str(row[0]).strip()
        iso = name_to_iso.get(country)
        if not iso: continue
        if indicator_keyword and indicator_keyword not in str(row): continue
        for col_idx, year in year_cols.items():
            if col_idx < len(row) and row[col_idx]:
                results[(iso, year)] = row[col_idx]
    return results

combined = {}

# 1. V-Dem
vdem_file = os.path.join(raw_macro_path, "V-Dem-CY-FullOthers-v15_csv/V-Dem-CY-Full+Others-v15.csv")
with open(vdem_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        iso = row['country_text_id']
        yr = row['year']
        if iso in target_iso3:
            combined.setdefault((iso, yr), {})['v2x_libdem'] = row['v2x_libdem']

# 2. Inflation
infl_file = os.path.join(raw_macro_path, "inflation.csv")
with open(infl_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        iso = row['REF_AREA']
        yr = row['TIME_PERIOD']
        if iso in target_iso3:
            combined.setdefault((iso, yr), {})['inflation'] = row['OBS_VALUE']

# 3. Excels
gdp_rows = parse_xlsx_simple(os.path.join(raw_macro_path, "GDP_consumption.xlsx"))
gdp_data = extract_from_rows(gdp_rows, "Gross domestic product")
cons_data = extract_from_rows(gdp_rows, "Actual individual consumption")
gini_data = extract_from_rows(parse_xlsx_simple(os.path.join(raw_macro_path, "gini_index.xlsx")))
unemp_data = extract_from_rows(parse_xlsx_simple(os.path.join(raw_macro_path, "unemployment.xlsx")))

for (iso, yr), val in gdp_data.items(): combined.setdefault((iso, yr), {})['gdp_per_capita'] = val
for (iso, yr), val in cons_data.items(): combined.setdefault((iso, yr), {})['consumption_per_capita'] = val
for (iso, yr), val in gini_data.items(): combined.setdefault((iso, yr), {})['gini_index'] = val
for (iso, yr), val in unemp_data.items(): combined.setdefault((iso, yr), {})['unemployment_rate'] = val

output_file = os.path.join(target_dir, "macro_merged_data.csv")
fields = ['country', 'year', 'v2x_libdem', 'inflation', 'gdp_per_capita', 'consumption_per_capita', 'gini_index', 'unemployment_rate']
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for (iso, yr) in sorted(combined.keys()):
        row = {'country': iso, 'year': yr}
        row.update(combined[(iso, yr)])
        writer.writerow(row)

print(f"Macro merge complete. Saved to {output_file}")
