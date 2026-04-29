import zipfile

import xml.etree.ElementTree as ET
import csv
import os

base_path = "/home/c-vantis/jd/40_projects/43_human_values_project"
xlsx_file = os.path.join(base_path, "gov_10a_exp__custom_20250909_spreadsheet.xlsx")

def get_strings(z):
    try:
        with z.open('xl/sharedStrings.xml') as f:
            tree = ET.parse(f)
            return [si.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t').text if si.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') is not None else "" for si in tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si')]
    except: return []

def parse_sheet(z, sheet_name, strings):
    with z.open(sheet_name) as f:
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        data = []
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
        return data

# Mappings based on the 7-interval discovery
target_sheets = {
    'xl/worksheets/sheet21.xml': 'exp_defence',
    'xl/worksheets/sheet56.xml': 'exp_health',
    'xl/worksheets/sheet70.xml': 'exp_education',
    'xl/worksheets/sheet77.xml': 'exp_social'
}

results = {} # (key, country, year) -> value

with zipfile.ZipFile(xlsx_file, 'r') as z:
    strings = get_strings(z)
    for sheet_path, key in target_sheets.items():
        print(f"Extracting {key} from {sheet_path}...")
        content = parse_sheet(z, sheet_path, strings)
        
        # Find years
        year_cols = {}
        start_row = 0
        for r_idx, row in enumerate(content):
            y_found = {j: val.strip() for j, val in enumerate(row) if val and str(val).strip().isdigit() and 2000 <= int(str(val).strip()) <= 2025}
            if len(y_found) > 5:
                year_cols = y_found
                start_row = r_idx + 1
                break
        
        if year_cols:
            for row in content[start_row:]:
                if not row[0]: continue
                country = str(row[0]).strip()
                for col_idx, year in year_cols.items():
                    if col_idx < len(row) and row[col_idx]:
                        results[(key, country, year)] = row[col_idx]

# Final Merge
name_map = {
    'ALB':'Albania', 'AUT':'Austria', 'BEL':'Belgium', 'BGR':'Bulgaria',
    'CHE':'Switzerland', 'CYP':'Cyprus', 'CZE':'Czechia', 'DEU':'Germany',
    'DNK':'Denmark', 'EST':'Estonia', 'ESP':'Spain', 'FIN':'Finland',
    'FRA':'France', 'GBR':'United Kingdom', 'GRC':'Greece', 'HRV':'Croatia',
    'HUN':'Hungary', 'IRL':'Ireland', 'ISR':'Israel', 'ISL':'Iceland',
    'ITA':'Italy', 'LTU':'Lithuania', 'LUX':'Luxembourg', 'LVA':'Latvia',
    'MNE':'Montenegro', 'MKD':'North Macedonia', 'NLD':'Netherlands',
    'NOR':'Norway', 'POL':'Poland', 'PRT':'Portugal', 'ROU':'Romania',
    'SRB':'Serbia', 'RUS':'Russia', 'SWE':'Sweden', 'SVN':'Slovenia',
    'SVK':'Slovakia', 'TUR':'Turkey', 'UKR':'Ukraine', 'XKX':'Kosovo',
}
iso2_to_3 = {
    'AL':'ALB', 'AT':'AUT', 'BE':'BEL', 'BG':'BGR', 'CH':'CHE', 'CY':'CYP',
    'CZ':'CZE', 'DE':'DEU', 'DK':'DNK', 'EE':'EST', 'ES':'ESP', 'FI':'FIN',
    'FR':'FRA', 'GB':'GBR', 'GR':'GRC', 'HR':'HRV', 'HU':'HUN', 'IE':'IRL',
    'IL':'ISR', 'IS':'ISL', 'IT':'ITA', 'LT':'LTU', 'LU':'LUX', 'LV':'LVA',
    'ME':'MNE', 'MK':'MKD', 'NL':'NLD', 'NO':'NOR', 'PL':'POL', 'PT':'PRT',
    'RO':'ROU', 'RS':'SRB', 'RU':'RUS', 'SE':'SWE', 'SI':'SVN', 'SK':'SVK',
    'TR':'TUR', 'UA':'UKR', 'XK':'XKX',
}

ess_v3 = os.path.join(base_path, "merged_ess_complete_v3.csv")
ess_final = os.path.join(base_path, "merged_ess_complete_final.csv")

with open(ess_v3, 'r', encoding='utf-8') as f_in, open(ess_final, 'w', encoding='utf-8', newline='') as f_out:
    reader = csv.DictReader(f_in)
    fieldnames = reader.fieldnames + list(target_sheets.values())
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()
    for row in reader:
        c3 = iso2_to_3.get(row['cntry'])
        cname = name_map.get(c3)
        yr = str(row['year'])
        for key in target_sheets.values():
            val = results.get((key, cname, yr), '')
            if not val and c3 == 'DEU':
                val = results.get((key, 'Germany (until 1990 period after the unification)', yr), '')
            row[key] = val
        writer.writerow(row)

print(f"Final merge complete. Saved to {ess_final}")
