"""Run once on your local machine to generate the three small derived datasets.

These CSVs contain no raw ESS microdata — only anonymised aggregates — and are
safe to commit to git and deploy on a public server.

Usage:
    cd /path/to/project
    python dashboard/export_precomputed.py
"""
import sys
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).parent))

# Temporarily move away any existing precomputed files so the full
# computation runs (not the cached version).
import data_pipeline as dp

out = dp.PRECOMPUTED_DIR
out.mkdir(exist_ok=True)

_tmp = out.parent / '_precomputed_backup'
if out.exists() and any(out.iterdir()):
    shutil.move(str(out), str(_tmp))
    out.mkdir(exist_ok=True)

try:
    print('=== 1 / 3  df_main  (load_data) ===')
    df_main = dp.load_data()
    df_main.to_csv(out / 'df_main.csv', index=False)
    kb = (out / 'df_main.csv').stat().st_size // 1024
    print(f'  → df_main.csv  {kb} KB  {len(df_main)} rows\n')

    print('=== 2 / 3  df_scatter  (load_scatter_data) ===')
    df_scatter = dp.load_scatter_data()
    df_scatter.to_csv(out / 'df_scatter.csv', index=False)
    kb = (out / 'df_scatter.csv').stat().st_size // 1024
    print(f'  → df_scatter.csv  {kb} KB  {len(df_scatter)} rows\n')

    print('=== 3 / 3  df_micro  (load_micro_individual) ===')
    df_micro = dp.load_micro_individual()
    df_micro.to_csv(out / 'df_micro.csv', index=False)
    kb = (out / 'df_micro.csv').stat().st_size // 1024
    print(f'  → df_micro.csv  {kb} KB  {len(df_micro)} rows\n')

    # df_gov_exp is built by build_gov_exp.py and already lives in precomputed/;
    # copy it over from raw/indicators if present (so backup/restore loop works).
    from pathlib import Path
    import shutil as _sh
    gov_src = Path(__file__).parent.parent / 'data' / 'raw' / 'indicators' / 'gov_exp_full.csv'
    gov_dst = out / 'df_gov_exp.csv'
    if gov_src.exists() and not gov_dst.exists():
        _sh.copy(gov_src, gov_dst)
        kb = gov_dst.stat().st_size // 1024
        import pandas as _pd
        _n = len(_pd.read_csv(gov_dst))
        print(f'  → df_gov_exp.csv  {kb} KB  {_n} rows (copied from raw)\n')

    print('All done. Files are in dashboard/precomputed/')
    print('Next step: git add dashboard/precomputed/ && git commit')

finally:
    # Clean up backup
    if _tmp.exists():
        shutil.rmtree(str(_tmp))
