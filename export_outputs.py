"""Regenerate the CSV tables, four figures, and summaries from the saved notebook inputs."""
from pathlib import Path
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
os.chdir(root)
out = root / 'outputs'
out.mkdir(exist_ok=True)
nb = json.loads((root / 'air-quality_self.ipynb').read_text(encoding='utf-8'))
ns = {'display': lambda *args, **kwargs: None}
names = iter(['01_cleaning_boxplots', '02_rows_by_stage', '03_weather_correlation', '04_hourly_air_quality'])
def save_figure():
    plt.gcf().savefig(out / (next(names) + '.png'), dpi=160, bbox_inches='tight')
    plt.close('all')
plt.show = save_figure
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        exec(''.join(cell['source']), ns)

for name in ['openaq_raw', 'purpleair_raw', 'weather_raw', 'analysis_ready']:
    ns[name].to_csv(out / (name + '.csv'), index=False)
final = ns['analysis_ready']
assert final['time'].ge(ns['START_UTC']).all() and final['time'].lt(ns['END_UTC']).all()
assert not final.duplicated(['source', 'site_id', 'latitude', 'longitude', 'time']).any()
pd = ns['pd']
coverage = final.assign(month=final['time'].dt.tz_convert('Asia/Jakarta').dt.strftime('%Y-%m'))
coverage = coverage.groupby(['month','source']).agg(rows=('pm25','size'), sensors=('site_id','nunique')).reset_index()
coverage.to_csv(out / 'monthly_coverage.csv', index=False)
source_summary = final.groupby('source')['pm25'].agg(['count','mean','median','min','max']).round(3)
ns['row_summary'].to_csv(out/'row_counts.csv',index=False)
ns['correlation'].to_csv(out/'weather_correlation.csv')
summary = {
    'start_inclusive_jakarta': ns['START_DATE'],
    'end_exclusive_jakarta': ns['END_DATE'],
    'shape': list(final.shape),
    'raw_rows': {k:len(ns[k]) for k in ['openaq_raw','purpleair_raw','weather_raw']},
    'clean_rows': {k:len(ns[k]) for k in ['openaq_clean','purpleair_clean','weather']},
    'row_counts': ns['row_summary'].to_dict(orient='records'),
    'missing': final.isna().sum().to_dict(),
    'source_summary': source_summary.to_dict(),
    'correlation': ns['correlation'].round(6).to_dict(),
    'dropped': ns['drop_columns'],
    'weather_station': str(ns['selected_station']),
    'weather_station_name': ns['available_stations'].iloc[0]['name'],
    'weather_hours': len(ns['city_weather']),
    'stations_with_data': int(ns['weather_raw']['station_id'].nunique()),
    'air_first_jakarta': str(final['time'].min().tz_convert('Asia/Jakarta')),
    'air_last_jakarta': str(final['time'].max().tz_convert('Asia/Jakarta')),
    'months_present': sorted(coverage['month'].unique().tolist()),
}
# Convert missing correlations to JSON null, not nonstandard NaN.
summary = json.loads(pd.Series(summary).to_json())
(out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(summary,indent=2))
