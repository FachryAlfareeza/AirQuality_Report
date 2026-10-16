"""Check that the final notebook, saved inputs, and exported results agree."""
from pathlib import Path
import ast, json, sys, hashlib
import pandas as pd

root=Path(sys.argv[1] if len(sys.argv)>1 else 'FINAL_2025_staging').resolve()
nb=json.loads((root/'air-quality_self.ipynb').read_text(encoding='utf-8'))
cells=[c for c in nb['cells'] if c['cell_type']=='code']
assert all(c.get('execution_count') is not None for c in cells)
assert not any(o.get('output_type')=='error' for c in cells for o in c.get('outputs',[]))
assert sum('image/png' in o.get('data',{}) for c in cells for o in c.get('outputs',[]))==4
for c in cells:
    for node in ast.walk(ast.parse(''.join(c['source']))):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='getenv':
            if len(node.args)>1 and 'KEY' in getattr(node.args[0],'value',''):
                assert not getattr(node.args[1],'value',None), 'Embedded credential in packaged notebook'
s=json.loads((root/'outputs/summary.json').read_text())
assert s['start_inclusive_jakarta']=='2025-01-01 00:00:00+07:00'
assert s['end_exclusive_jakarta']=='2026-01-01 00:00:00+07:00'
data=pd.read_csv(root/'outputs/analysis_ready.csv')
assert list(data.shape)==s['shape']
t=pd.to_datetime(data['time'],utc=True).dt.tz_convert('Asia/Jakarta')
assert t.ge(pd.Timestamp(s['start_inclusive_jakarta'])).all()
assert t.lt(pd.Timestamp(s['end_exclusive_jakarta'])).all()
assert not data.duplicated(['source','site_id','latitude','longitude','time']).any()
assert data.isna().sum().to_dict()==s['missing']
for name,count in s['raw_rows'].items():
    raw=pd.read_csv(root/'outputs'/f'{name}.csv')
    assert len(raw)==count
    dates=pd.to_datetime(raw['time'],utc=True).dt.tz_convert('Asia/Jakarta')
    # Air downloads and loaded weather must be confined to the requested year.
    assert dates.dropna().ge(pd.Timestamp(s['start_inclusive_jakarta'])).all()
    assert dates.dropna().lt(pd.Timestamp(s['end_exclusive_jakarta'])).all()
assert not (root/'data/air_quality_snapshot').exists(), 'Old January 2024 snapshot remains in FINAL'
assert not (root/'presentation_notes.md').exists(), 'Old Canva notes remain in the 2025 package'
manifest=json.loads((root/'data/air_quality_2025/raw_responses/manifest.json').read_text())
assert all((root/'data/air_quality_2025/raw_responses'/e['file']).is_file() for e in manifest)
hashes={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.json' and '__pycache__' not in p.parts}
(root/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
print(f'PASS: {len(cells)} executed code cells, 4 figures, {len(data):,} rows, {len(data.columns)} columns; only 2025 measurements.')
print('Monthly coverage:',s['months_present'])
