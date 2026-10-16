// Build the notebook's reproducible Excel snapshot with the bundled spreadsheet tool.
import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const input = JSON.parse(await fs.readFile(process.argv[2], 'utf8'));
const out = input.output_dir;
await fs.mkdir(out, { recursive: true });
const wb = Workbook.create();
const overview = wb.worksheets.add('Overview');
const sheets = new Map();
const counts = {};
const letter = index => {
  let result = '';
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) result = String.fromCharCode(65 + (n - 1) % 26) + result;
  return result;
};
const palette = ['#2878B5', '#D95F02', '#71965A'];
const sourceURLs = {
  'OpenAQ raw': 'Source: https://api.openaq.org/v3/locations and /v3/sensors/{id}/hours',
  'PurpleAir raw': 'Source: https://api.purpleair.com/v1/sensors and /v1/sensors/{id}/history',
  'Weather downloaded': 'Source: Meteostat Python library; https://dev.meteostat.net/python/api/meteostat.hourly',
  'Stations downloaded': 'Source: https://dev.meteostat.net/python/api/meteostat.stations.nearby',
};

for (const [tableIndex, t] of input.tables.entries()) {
  if (!t.columns.length) continue;
  const sheet = wb.worksheets.add(t.name);
  sheets.set(t.name, sheet);
  counts[t.name] = t.rows.length;
  sheet.showGridLines = false;
  const dateSet = new Set(t.date_columns);
  const rows = t.rows.map(row => row.map((value, i) => {
    if (value === null) return null;
    if (dateSet.has(t.columns[i])) {
      // Excel has no timezone: retain each column's documented wall-clock time.
      return new Date(String(value).slice(0, 19) + 'Z');
    }
    return typeof value === 'string' && value.startsWith('=') ? "'" + value : value;
  }));
  sheet.getRangeByIndexes(0, 0, 1, t.columns.length).values = [t.columns];
  for (let start = 0; start < rows.length; start += 1500) {
    const chunk = rows.slice(start, start + 1500);
    sheet.getRangeByIndexes(start + 1, 0, chunk.length, t.columns.length).values = chunk;
  }
  // Style a bounded opening view; full-table per-cell styling is expensive for snapshots.
  const used = sheet.getRangeByIndexes(0, 0, Math.min(20, Math.max(1, rows.length + 1)), t.columns.length);
  used.format.font = { name: 'Arial', size: 10, color: '#243247' };
  used.format.rowHeight = 18;
  used.format.columnWidth = 18;
  used.format.verticalAlignment = 'center';
  const header = sheet.getRangeByIndexes(0, 0, 1, t.columns.length);
  header.format.fill = '#233B5D';
  header.format.font = { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' };
  header.format.wrapText = true;
  header.format.rowHeight = 34;
  header.format.horizontalAlignment = 'center';
  for (let c = 0; c < t.columns.length; c++) {
    const name = t.columns[c];
    const range = sheet.getRangeByIndexes(1, c, Math.min(20, Math.max(1, rows.length)), 1);
    if (dateSet.has(name)) {
      sheet.getRangeByIndexes(1, c, Math.max(1, rows.length), 1).setNumberFormat('yyyy-mm-dd hh:mm');
      range.format.columnWidth = 23;
    } else if (name === 'missing_fraction') {
      range.setNumberFormat('0.0%');
    } else if (rows.some(row => typeof row[c] === 'number')) {
      range.setNumberFormat(/rows|count|missing|columns|hour|weekday|day_of_week/.test(name) ? '#,##0' : '#,##0.00');
    }
    if (/stage|previous|site_id|station_id|column/.test(name)) range.format.columnWidth = 23;
    if (name === 'record') range.format.columnWidth = 62;
    if (name === 'before' || name === 'after') range.format.columnWidth = 29;
    if (name === 'note' || name === 'explanation') {
      range.format.columnWidth = 100;
      range.format.wrapText = true;
      range.format.rowHeight = 42;
    }
    if (name === 'pm25') {
      range.conditionalFormats.add('containsBlanks', { format: { fill: '#FFF2D6' } });
    }
  }
  if (rows.length) {
    const table = sheet.tables.add(`A1:${letter(t.columns.length - 1)}${rows.length + 1}`, true, `Data${tableIndex + 1}`);
    table.showFilterButton = true;
  }
  sheet.freezePanes.freezeRows(1);
  if (sourceURLs[t.name]) {
    sheet.getCell(0, t.columns.length + 1).values = [[sourceURLs[t.name]]];
    sheet.getCell(0, t.columns.length + 1).format.columnWidth = 110;
  }
}

overview.showGridLines = false;
overview.tabColor = '#233B5D';
overview.getRange('A1:P65').format.font = { name: 'Arial', size: 10, color: '#243247' };
overview.getRange('A1:P65').format.columnWidth = 12;
overview.getRange('A1:P65').format.rowHeight = 22;
overview.getRange('A2').values = [['Jakarta air quality — processing review']];
overview.getRange('A2').format.font = { name: 'Arial', size: 16, bold: true };
overview.getRange('A3').values = [[input.period]];
overview.getRange('A5:B8').values = [
  ['Final sensor-hours', counts.Final],
  ['Original OpenAQ rows', counts['OpenAQ raw']],
  ['Original PurpleAir rows', counts['PurpleAir raw']],
  ['Processing snapshots', input.tables.find(t => t.name === 'Stages').rows.length],
];
overview.getRange('A5:A8').format.columnWidth = 31;
overview.getRange('B5:B8').setNumberFormat('#,##0');
overview.getRange('D5').values = [['Stages shows changes; Changes lists affected records.']];
overview.getRange('D6').values = [['Raw tables preserve measurements; blanks mean missing.']];
overview.getRange('D7').values = [['Statistical outliers are retained unless a cleaning rule rejects them.']];
overview.getRange('D8').values = [['Charts and tables are snapshots; rerun the notebook to refresh.']];

function addChart(type, tableName, title, from, to, yTitle) {
  const t = input.tables.find(x => x.name === tableName);
  const chart = overview.charts.add(type, sheets.get(tableName).getRangeByIndexes(0, 0, t.rows.length + 1, t.columns.length));
  chart.title = title;
  chart.titleTextStyle.typeface = 'Arial';
  chart.titleTextStyle.fontSize = 14;
  chart.legend = { position: 'top', textStyle: { typeface: 'Arial', fontSize: 11 } };
  chart.xAxis = { axisType: 'textAxis', textStyle: { typeface: 'Arial', fontSize: 10 } };
  chart.yAxis = { numberFormatCode: '#,##0', numberFormatSourceLinked: false, textStyle: { typeface: 'Arial', fontSize: 10 } };
  chart.yAxis.title.text = yTitle;
  chart.setPosition(from, to);
  for (const [i, series] of chart.series.items.entries()) {
    series.fill = palette[i % palette.length];
    if (type === 'line') series.line = { fill: palette[i % palette.length], style: 'solid', width: 2 };
  }
  return chart;
}
addChart('bar', 'Chart stages', 'Rows and missing PM2.5 by stage', 'A11', 'H29', 'Rows');
addChart('line', 'Chart daily', 'Daily mean of sensor-hours by source', 'I11', 'Q29', 'PM2.5 (µg/m³)');
addChart('bar', 'Chart distribution', 'Final PM2.5 distribution (50 µg/m³ bins)', 'A32', 'Q52', 'Nonmissing readings');
overview.getRange('A54').values = [['Daily means include imputed values and changing sensor coverage. Raw and final IQR flags are in Outlier flags.']];
overview.getRange('A55').values = [['Seven detailed diagnostic figures are also saved as PNG files beside the workbook.']];

wb.recalculate();
console.log((await wb.inspect({ kind: 'table', range: 'Overview!A5:B8', include: 'values,formulas', tableMaxRows: 4, tableMaxCols: 2 })).ndjson);
const errors = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 20 }, summary: 'Export error scan' });
console.log(errors.ndjson);
const file = await SpreadsheetFile.exportXlsx(wb);
await file.save(path.join(out, 'air_quality_audit.xlsx'));

// Small representative previews of every sheet, plus complete chart views.
const previews = path.join(out, '_previews');
await fs.mkdir(previews, { recursive: true });
for (const sheet of [overview, ...sheets.values()]) {
  const table = input.tables.find(t => t.name === sheet.name);
  const range = sheet === overview ? 'A1:Q29' : `A1:${letter(Math.min(table.columns.length, 6) - 1)}${Math.min(table.rows.length + 1, 6)}`;
  const image = await wb.render({ sheetName: sheet.name, range, scale: 1, format: 'png' });
  await fs.writeFile(path.join(previews, sheet.name.replaceAll(' ', '_') + '.png'), new Uint8Array(await image.arrayBuffer()));
}
const bottom = await wb.render({ sheetName: 'Overview', range: 'A32:Q55', scale: 1, format: 'png' });
await fs.writeFile(path.join(previews, 'Overview_distribution.png'), new Uint8Array(await bottom.arrayBuffer()));
await fs.writeFile(path.join(out, 'export_verification.json'), JSON.stringify({ rows: counts, charts: overview.charts.items.map(c => ({ title: c.title.text, series: c.series.items.map(s => ({ values: s.formula, categories: s.categoryFormula })) })) }, null, 2));
console.log(`Saved air_quality_audit.xlsx (${sheets.size + 1} sheets, 3 native charts).`);
