import csv
import os
import glob
from collections import defaultdict

base_path = "/home/c-vantis/jd/40_projects/43_human_values_project/data/raw/ess"
countries = {'BE', 'DE', 'FI', 'FR', 'IE', 'NL', 'NO', 'PL', 'PT', 'SE', 'CH', 'SI', 'ES', 'HU', 'GB'}

# Updated round years
round_years = {
    1: 2002, 2: 2004, 3: 2006, 4: 2008, 5: 2010,
    6: 2012, 7: 2014, 8: 2016, 9: 2018, 10: 2020, 11: 2023
}

def normalize_name(name):
    name = name.lower()
    if name.startswith('ip') and len(name) > 5:
        if name.endswith('a') or name.endswith('b'):
            return name[:-1]
    return name

def calculate_stats(vals):
    if not vals: return None, None
    n = len(vals)
    mean = sum(vals) / n
    vals.sort()
    if n % 2 == 1:
        median = vals[n//2]
    else:
        median = (vals[n//2 - 1] + vals[n//2]) / 2
    return mean, median

# Data structure: (country, year) -> {var_name: [values]}
agg_data = defaultdict(lambda: defaultdict(list))
all_ip_vars = set()

for r in range(1, 12):
    # Adjust path to match the actual folder structure found earlier
    folder = f"/home/c-vantis/jd/40_projects/43_human_values_project/ESS{r}"
    if not os.path.exists(folder):
        # Fallback to data/raw/ess/ESS{r} if they were moved
        folder = os.path.join(base_path, f"ESS{r}")
    
    csv_files = glob.glob(os.path.join(folder, "*.csv"))
    if not csv_files:
        print(f"Warning: No CSV for Round {r} in {folder}")
        continue
    
    with open(csv_files[0], mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        ip_cols = {h: normalize_name(h) for h in reader.fieldnames if normalize_name(h).startswith('ip')}
        for norm in ip_cols.values(): all_ip_vars.add(norm)
        
        count = 0
        for row in reader:
            cntry = row['cntry'].upper()
            if cntry in countries:
                year = round_years[r]
                for orig, norm in ip_cols.items():
                    val = row[orig]
                    if val and val.strip() and val.strip().isdigit():
                        v_float = float(val)
                        # ESS Schwartz values are usually 1-6. 7, 8, 9 are missing/refusal
                        if 1 <= v_float <= 6:
                            agg_data[(cntry, year)][norm].append(v_float)
                count += 1
        print(f"Round {r} ({round_years[r]}) processed: {count} cases.")

# Write Results
output_file = "/home/c-vantis/jd/40_projects/43_human_values_project/ess_schwartz_aggregated.csv"
sorted_ip = sorted(list(all_ip_vars))
header = ['country', 'year']
for v in sorted_ip:
    header.append(f"{v}_mean")
    header.append(f"{v}_median")

with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=header)
    writer.writeheader()
    for (cntry, year) in sorted(agg_data.keys()):
        out_row = {'country': cntry, 'year': year}
        for v in sorted_ip:
            m_mean, m_median = calculate_stats(agg_data[(cntry, year)][v])
            out_row[f"{v}_mean"] = round(m_mean, 4) if m_mean is not None else ""
            out_row[f"{v}_median"] = m_median if m_median is not None else ""
        writer.writerow(out_row)

print(f"Aggregated Schwartz values saved to {output_file}")
