"""Download archived inputs using the notebook's own download functions."""
from pathlib import Path
import json, os

root = Path(__file__).parent
os.chdir(root)
n = json.loads((root/'air-quality_self.ipynb').read_text(encoding='utf-8'))
ns = {'display': lambda *args, **kwargs: None}
for i in range(1,5):
    exec(''.join(n['cells'][i]['source']),ns)
ns['USE_SAVED_DATA']=False
getter = ns['get_api_data']
def progress(url, headers=None, params=None):
    result = getter(url,headers,params)
    print(url.rsplit('/',2)[-2:], 'rows',len(result.get('results',result.get('data',[]))),flush=True)
    return result
ns['get_api_data']=progress
for i in [5,6,7]:
    print('DOWNLOAD CELL',i,flush=True)
    exec(''.join(n['cells'][i]['source']),ns)
print('All 2025 source downloads complete.',flush=True)
