import re
import os

def extract_vars(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'<li>\s*<a href="#[^"]+">\s*<span>([^<]+)</span>\s*<span>\s*-\s*([^<]+)</span>'
    matches = re.findall(pattern, content)
    return {name.strip().lower(): label.strip() for name, label in matches}

base_path = "/home/c-vantis/jd/40_projects/43_human_values_project"
rounds = ["ESS1", "ESS2", "ESS3", "ESS4", "ESS5", "ESS6", "ESS7", "ESS8", "ESS9", "ESS10", "ESS11"]

data = {}
for r in rounds:
    folder = os.path.join(base_path, r)
    html_files = [f for f in os.listdir(folder) if f.endswith('.html') and 'codebook' in f.lower()]
    if html_files:
        data[r] = extract_vars(os.path.join(folder, html_files[0]))

def normalize(name):
    if name.startswith('ip') and len(name) > 5:
        if name.endswith('a') or name.endswith('b'):
            return name[:-1]
    return name

all_normalized_names = {}
for r in rounds:
    if r not in data: continue
    all_normalized_names[r] = {normalize(name): name for name in data[r].keys()}

common_bases = set(all_normalized_names["ESS1"].keys())
for r in rounds[1:]:
    if r in all_normalized_names:
        common_bases &= set(all_normalized_names[r].keys())

# Define white list of prefixes and exact names for opinions/values/feelings
white_list_prefixes = ('ip', 'stf', 'trst', 'ppl', 'im', 'rlg')
white_list_exact = {
    'happy', 'health', 'lrscale', 'polintr', 'pray', 'sclmeet', 'sclact', 
    'aesfdrk', 'clsprty', 'freehms', 'gincdif', 'vote', 'badge', 'bctprd', 
    'contplt', 'sgnptit', 'dscrgrp'
}

filtered = []
for base in sorted(common_bases):
    if base.startswith(white_list_prefixes) or base in white_list_exact:
        # Exclude some rlg that are not feelings/opinions if necessary, but most are fine
        if base in ('imgfrnd', 'impcntr', 'imsmetn', 'imdfetn', 'imbgeco', 'imueclt', 'imwbcnt'):
             pass # keep
        
        orig_name = all_normalized_names["ESS1"][base]
        label = data["ESS1"][orig_name]
        
        # Clean label for ip variables
        if base.startswith('ip'):
            label = label.split(':')[-1].strip() if ':' in label else label
            
        filtered.append((orig_name, label))

with open(os.path.join(base_path, "ess_common_variables.md"), "w") as f:
    f.write("# Gemeinsame ESS Variablen (Werte, Meinungen, Gefühle)\n\n")
    f.write("Diese Tabelle enthält Variablen, die in allen ESS-Runden (1-11) vorkommen und sich auf individuelle Meinungen, Ansichten, Gefühle oder Werte beziehen.\n\n")
    f.write("| Kürzel | Volle Bezeichnung |\n")
    f.write("| :--- | :--- |\n")
    for name, label in filtered:
        f.write(f"| {name} | {label} |\n")

print(f"Table written to {os.path.join(base_path, 'ess_common_variables.md')}")
