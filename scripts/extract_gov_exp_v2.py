import zipfile
import xml.etree.ElementTree as ET
import csv
import os

base_path = "/home/c-vantis/jd/40_projects/43_human_values_project"
xlsx_file = os.path.join(base_path, "gov_10a_exp__custom_20250909_spreadsheet.xlsx")

def extract_data_from_sheet(file_path, sheet_xml_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        with z.open(sheet_xml_path) as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            data = []
            for row in root.findall('.//ns:row', ns):
                row_data = []
                # Initialize row with empty strings for all potential columns up to a reasonable limit
                row_list = [""] * 100 
                for cell in row.findall('ns:c', ns):
                    # Get column index from 'r' attribute (e.g., "A1", "B2")
                    ref = cell.get('r')
                    col_letter = "".join(filter(str.isalpha, ref))
                    # Simple column letter to index conversion
                    col_idx = 0
                    for char in col_letter:
                        col_idx = col_idx * 26 + (ord(char) - ord('A') + 1)
                    col_idx -= 1
                    
                    v = cell.find('ns:v', ns)
                    t = cell.get('t')
                    if t == 'inlineStr':
                        t_tag = cell.find('.//ns:t', ns)
                        val = t_tag.text if t_tag is not None else ""
                    else:
                        val = v.text if v is not None else ""
                    
                    if col_idx < 100:
                        row_list[col_idx] = val
                data.append(row_list)
            return data

# We know from previous scan it is sheet1.xml or similar. Let's find specifically "Total general government expenditure"
target_sheet = None
with zipfile.ZipFile(xlsx_file, 'r') as z:
    for i in range(1, 90):
        name = f'xl/worksheets/sheet{i}.xml'
        try:
            with z.open(name) as f:
                if b"Total general government expenditure" in f.read():
                    target_sheet = name
                    break
        except KeyError: continue

if not target_sheet:
    print("Could not find Total Expenditure sheet")
    exit(1)

raw_data = extract_data_from_sheet(xlsx_file, target_sheet)

gov_exp_map = {}
year_cols = {}
start_row = 0

for i, row in enumerate(raw_data):
    # Looking for a row that has multiple years
    years_found = {j: val.strip() for j, val in enumerate(row) if val.strip().isdigit() and 2000 <= int(val.strip()) <= 2025}
    if len(years_found) > 5: # Threshold to identify the year header row
        year_cols = years_found
        start_row = i + 1
        break

for row in raw_data[start_row:]:
    country = row[0].strip()
    if not country: continue
    for col_idx, year in year_cols.items():
        if col_idx < len(row):
            val = row[col_idx]
            if val:
                gov_exp_map[(country, year)] = val

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

# The ISO mapping in ESS is ISO-2
iso_map_2_to_3 = {
    'AL': 'ALB', 'AT': 'AUT', 'BE': 'BEL', 'BG': 'BGR', 'CH': 'CHE', 'CY': 'CYP',
    'CZ': 'CZE', 'DE': 'DEU', 'DK': 'DNK', 'EE': 'EST', 'ES': 'ESP', 'FI': 'FIN',
    'FR': 'FRA', 'GB': 'GBR', 'GR': 'GRC', 'HR': 'HRV', 'HU': 'HUN', 'IE': 'IRL',
    'IL': 'ISR', 'IS': 'ISL', 'IT': 'ITA', 'LT': 'LTU', 'LU': 'LUX', 'LV': 'LVA',
    'ME': 'MNE', 'MK': 'MKD', 'NL': 'NLD', 'NO': 'NOR', 'PL': 'POL', 'PT': 'PRT',
    'RO': 'ROU', 'RS': 'SRB', 'RU': 'RUS', 'SE': 'SWE', 'SI': 'SVN', 'SK': 'SVK',
    'TR': 'TUR', 'UA': 'UKR', 'XK': 'XKX',
}

# Reverse mapping for matching Eurostat names
iso3_to_name = {
    'ALB': 'Albania', 'AUT': 'Austria', 'BEL': 'Belgium', 'BGR': 'Bulgaria',
    'CHE': 'Switzerland', 'CYP': 'Cyprus', 'CZE': 'Czechia', 'DEU': 'Germany',
    'DNK': 'Denmark', 'EST': 'Estonia', 'ESP': 'Spain', 'FIN': 'Finland',
    'FRA': 'France', 'GBR': 'United Kingdom', 'GRC': 'Greece', 'HRV': 'Croatia',
    'HUN': 'Hungary', 'IRL': 'Ireland', 'ISR': 'Israel', 'ISL': 'Iceland',
    'ITA': 'Italy', 'LTU': 'Lithuania', 'LUX': 'Luxembourg', 'LVA': 'Latvia',
    'MNE': 'Montenegro', 'MKD': 'North Macedonia', 'NLD': 'Netherlands',
    'NOR': 'Norway', 'POL': 'Poland', 'PRT': 'Portugal', 'ROU': 'Romania',
    'SRB': 'Serbia', 'RUS': 'Russia', 'SWE': 'Sweden', 'SVN': 'Slovenia',
    'SVK': 'Slovakia', 'TUR': 'Turkey', 'UKR': 'Ukraine', 'XKX': 'Kosovo',
}

ess_final = os.path.join(base_path, "merged_ess_macro_final.csv")
ess_complete = os.path.join(base_path, "merged_ess_complete_v3.csv")

with open(ess_final, 'r', encoding='utf-8') as f_in, open(ess_complete, 'w', encoding='utf-8', newline='') as f_out:
    reader = csv.DictReader(f_in)
    fieldnames = reader.fieldnames + ['gov_exp_pct_gdp']
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in reader:
        c3 = iso_map_2_to_3.get(row['cntry'])
        name = iso3_to_name.get(c3)
        row['gov_exp_pct_gdp'] = gov_exp_map.get((name, str(row['year'])), '')
        writer.writerow(row)

print(f"Final merge complete. Saved to {ess_complete}")
