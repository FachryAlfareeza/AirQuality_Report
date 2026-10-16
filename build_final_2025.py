"""Prepare a clean package without carrying 2024 outputs or presentation notes forward."""
from pathlib import Path
import json, shutil, re
from datetime import datetime
root = Path(__file__).resolve().parent
dest = root / 'FINAL_2025_staging'
dest.mkdir(exist_ok=True)
inputs=dest/'data/air_quality_2025'
archive=inputs/'raw_responses'
archive.mkdir(parents=True,exist_ok=True)
for filename in ['Stations_downloaded.csv','Weather_downloaded.csv']:
    shutil.copy2(root/'data/air_quality_2025'/filename,inputs/filename)
original=root/'data/air_quality_2025/raw_responses'
manifest=json.loads((original/'manifest.json').read_text())
# Omit the exploratory annual OpenAQ requests superseded by 30-day windows.
manifest=[e for e in manifest if not (e['url'].endswith('/hours') and
    (datetime.fromisoformat(e['params']['datetime_to'])-datetime.fromisoformat(e['params']['datetime_from'])).days>30)]
for index, entry in enumerate(manifest, start=1):
    filename=f'response_{index:04d}.json'
    shutil.copy2(original/entry['file'],archive/filename)
    entry['file']=filename
(archive/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
n=json.loads((root/'air-quality_self.ipynb').read_text(encoding='utf-8'))
for c in n['cells']:
    if c['cell_type']=='code':
        s=''.join(c['source'])
        s=re.sub(r'os\.getenv\(("[A-Z_]*KEY"),\s*"[^"]*"\)',r'os.getenv(\1, "")',s)
        c['source']=s.splitlines(keepends=True)
(dest/'air-quality_self.ipynb').write_text(json.dumps(n,indent=1,ensure_ascii=False),encoding='utf-8')
shutil.copy2(root/'export_outputs.py',dest/'export_outputs.py')
shutil.copy2(root/'run_air_quality_notebook.py',dest/'run_notebook.py')
(dest/'requirements.txt').write_text('pandas>=2.2\nmatplotlib>=3.9\nrequests\nmeteostat>=2.1\nipykernel\nnbclient\nnbformat\n',encoding='utf-8')
print('Prepared',dest)
