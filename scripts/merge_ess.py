import pandas as pd
import os
import glob

# Configuration
base_path = "/home/c-vantis/jd/40_projects/43_human_values_project"
countries = ['BE', 'DE', 'FI', 'FR', 'IE', 'NL', 'NO', 'PL', 'PT', 'SE', 'CH', 'SI', 'ES', 'HU', 'GB']

# Mapping rounds to years (approximate start of data collection)
round_years = {
    1: 2002, 2: 2004, 3: 2006, 4: 2008, 5: 2010,
    6: 2012, 7: 2014, 8: 2016, 9: 2018, 10: 2020, 11: 2022
}

all_dfs = []

for r in range(1, 12):
    folder = os.path.join(base_path, f"ESS{r}")
    csv_files = glob.glob(os.path.join(folder, "*.csv"))
    
    if not csv_files:
        print(f"No CSV found for Round {r}")
        continue
    
    # Load CSV
    df = pd.read_csv(csv_files[0], low_memory=False)
    
    # Filter countries (ensure uppercase)
    df['cntry'] = df['cntry'].str.upper()
    df = df[df['cntry'].isin(countries)]
    
    # Define columns to keep
    # Metadata
    meta_cols = ['cntry', 'essround', 'idno']
    
    # Identify variables
    # 1. "ip..." (Important...)
    # 2. "trst..." and "ppl..." (Trust)
    # 3. "stflife" (Lebenszufriedenheit)
    # 4. "vote"
    
    target_cols = [c for c in df.columns if 
                   c.startswith('ip') or 
                   c.startswith('trst') or 
                   c.startswith('ppl') or 
                   c.lower() in ['stflife', 'vote']]
    
    # Suffixes in newer rounds (like ipcrtiva) need normalization to merge correctly
    # But for now, we select them as they are in each round.
    
    cols_to_extract = meta_cols + target_cols
    # Ensure columns exist in this specific round
    cols_to_extract = [c for c in cols_to_extract if c in df.columns]
    
    df_filtered = df[cols_to_extract].copy()
    
    # Add year column
    df_filtered['year'] = round_years.get(r)
    
    all_dfs.append(df_filtered)
    print(f"Round {r} processed: {len(df_filtered)} rows.")

# Merge all
merged_df = pd.concat(all_dfs, ignore_index=True)

# Normalize column names for ip variables (remove trailing 'a' or 'b')
def normalize_col(col):
    if col.startswith('ip') and len(col) > 5:
        if col.endswith('a') or col.endswith('b'):
            return col[:-1]
    return col

merged_df.columns = [normalize_col(c) for c in merged_df.columns]

# Grouping again after normalization might be needed if columns were split
merged_df = merged_df.groupby(lambda x: x, axis=1).first() # Keep first non-null if duplicates occurred

output_file = os.path.join(base_path, "merged_ess_values.csv")
merged_df.to_csv(output_file, index=False)
print(f"Final merged dataset saved to {output_file}")
print(f"Total rows: {len(merged_df)}")
print(f"Columns: {merged_df.columns.tolist()}")
