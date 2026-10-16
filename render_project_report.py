"""Render the six-section report as a PDF companion when native TeX is unavailable."""
from pathlib import Path
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

root=Path(__file__).parent
run=root/'outputs/air-quality-review/20260927T122050540703Z'
m=json.loads((run/'report_metrics.json').read_text(encoding='utf-8'))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyReport',fontName='Helvetica',fontSize=10.2,leading=13.4,spaceAfter=7))
styles.add(ParagraphStyle(name='ReportTitle',fontName='Helvetica-Bold',fontSize=23,leading=27,textColor=colors.HexColor('#233B5D'),spaceAfter=7,alignment=TA_CENTER))
styles.add(ParagraphStyle(name='SectionReport',fontName='Helvetica-Bold',fontSize=16,leading=20,spaceAfter=10,textColor=colors.HexColor('#233B5D')))
styles.add(ParagraphStyle(name='SmallReport',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=6))
story=[]
def p(s,style='BodyReport'):
    for mark in ['−', '–', '—', '‑']:
        s = s.replace(mark, '-')
    story.append(Paragraph(s,styles[style]))
def section(title): p(title,'SectionReport')
def table(headers,rows,widths):
    data=[[Paragraph(str(x),styles['SmallReport']) for x in headers]]+[[Paragraph(str(x),styles['SmallReport']) for x in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7EDF4')),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#233B5D')),('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#ADB7C3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.extend([t,Spacer(1,9)])
def image(name,width=490):
    from PIL import Image as PILImage
    file=run/'graphs'/name
    with PILImage.open(file) as im: height=width*im.height/im.width
    story.extend([Image(str(file),width=width,height=height),Spacer(1,7)])
def page(): story.append(PageBreak())

p('Jakarta Air Quality','ReportTitle')
p('A reproducible preprocessing and PCA study<br/>January 2024 observations · Rekayasa Data','Title')
section('1. Dataset description and justification')
p('<b>Research question.</b> How do quality checks, hourly alignment and weather integration change usable Jakarta PM2.5 observations, and how compactly can PCA represent their joint variation?')
p('The geographical bounds are longitude 106.689–106.978 and latitude -6.370–-6.079. The observation period is 1 January 2024 at 00:00 inclusive to 1 February 2024 at 00:00 exclusive, in Jakarta time. Joins use UTC.')
table(['Source','Records','Content and role'],[
['OpenAQ','3,990','Original PM2.5 observations from eight contributing sensors and several providers/technologies.'],
['PurpleAir','2,906','Outdoor public-sensor history with A/B channels; supplementary comparison.'],
['Meteostat','2,976','Station-hours within the period; four reporting stations out of five discovered.']], [78,58,363])
p('<b>Why this dataset?</b> Inconsistent schemas, missing measurements, channel disagreement, uneven coverage and different spatial supports require genuine preprocessing. A fixed local month remains inspectable while containing substantial variation. Imputation is explicitly flagged.')
p('<b>Open-data scope.</b> The primary PCA cohort uses only OpenAQ sensors with US Public Domain, CC0 1.0 or CC BY 4.0 explicitly stated in returned metadata, plus Meteostat weather. It starts with 3,064 sensor-hours from six sensors. Other OpenAQ records and PurpleAir remain supplementary in the audit. API accessibility alone is not treated as an open license. Provider names and license labels are exported. [1–4]')
p('<b>Originality and provenance.</b> The region, month, licensed subset, weather assignment and stage audit define this selection. Uniqueness relative to classmates must still be confirmed through the class register. Responses were retrieved in September 2026; measurements refer to January 2024. The stated 2025 assignment deadline is historical; an earlier submission date is not claimed.')
page()

section('2. Cleaning and before/after changes')
p('The code checks exact duplicates, parses numeric values and timestamps, and masks PM2.5 outside 0–1,000 µg/m³. This broad plausibility rule is not a health threshold. PurpleAir requires both channels to be valid and their absolute difference to be no greater than max(10, 50% of their mean). The project heuristic rejects one channel pair; it is not a local sensor calibration. Valid high pollution readings remain in the integration archive.')
p('Weather limits are -30–60 °C, 0–100% humidity, 0–500 mm hourly rain, 0–250 km/h wind and 850–1,100 hPa pressure. No available weather value fails these limits in this run. No combined air row is removed by the key, area or date filters.')
table(['Processing stage','Rows','Missing PM2.5'],[
['Combined cleaned sources','6,896','737'],['Hourly grid before interpolation','7,511','1,352'],['Hourly grid after interpolation','7,511','1,214'],['Weather-integrated final table','7,511','1,214']],[300,95,104])
image('04_missingness.png')
p('<b>Interpretation.</b> Resampling adds 615 absent sensor-hours between each sensor’s first and last observation. Missingness initially rises because unobserved hours become explicit. Interpolation fills 138 complete internal gaps of at most two hours. Longer and edge gaps remain missing. PM2.5 missingness falls from 18.00% to 16.16% on the same hourly grid; the original 10.69% uses a smaller denominator.')
p('Weather is reindexed per station; bounded gaps of up to three hours may be interpolated, except rainfall. None are filled in this snapshot. The integrated table retains 1,488 missing rain values (19.81%). Missing rain is not interpreted as zero.')
page()

section('3. Integration and redundant attributes')
p('Each air sensor is linked to the nearest weather station with usable observations. Haversine distance uses radians and an Earth radius of 6,371 km. Distances range from 0.13 to 13.93 km. Station assignment remains fixed rather than switching between stations hour by hour.')
p('Air and weather are joined on station ID and UTC hour. Both joins enforce a many-to-one relationship. The final table has 7,511 rows and 22 columns, including weather, distances, imputation flags and Jakarta-time features. No duplicate source–sensor–hour remains.')
p('<b>Redundancy.</b> Pearson correlations are computed on distinct weather station-hours so stations assigned to several air sensors are not counted repeatedly. An attribute is removed only if absolute correlation exceeds 0.95 with an earlier attribute. No pair meets that cutoff. Temperature and humidity correlate at -0.931; strong correlation alone does not justify contradicting the stated threshold.')
table(['Weather pair','Pearson r'],[['Temperature–humidity','-0.931'],['Humidity–wind speed','-0.471'],['Temperature–wind speed','0.337'],['Humidity–rain','0.199'],['Rain–wind speed','-0.045']],[370,129])
image('06_weather_merge.png')
p('<b>Temporal pattern.</b> Both sources show elevated averages near the start of the month and lower values through much of the middle of the month, followed by later increases. The notebook’s hourly trend is paired with reporting counts. Means include imputed values and changing sensor coverage; they are not a calibrated source comparison or a citywide exposure estimate.')
page()

section('4. Outlier removal and dimensionality reduction')
p('Fixed raw per-sensor quartiles define Q1 − 1.5 × IQR and Q3 + 1.5 × IQR, requiring at least four readings and nonzero IQR. The same bounds flag raw and final values. In the primary open-data cohort, 94 of 3,064 sensor-hours are excluded from a separate typical-condition PCA cohort. Original high readings remain in the integration archive.')
p('A further 1,801 rows lack at least one selected numerical feature, leaving 1,169 complete rows. Only five of the six primary sensors remain; one provides 717 rows. Complete-case selection and rainfall coverage therefore limit representativeness.')
p('PCA uses PM2.5, temperature, humidity, rain, wind speed and pressure. Each feature is centered and divided by its sample standard deviation. NumPy singular-value decomposition computes the components. Eigenvalues equal squared singular values divided by n − 1. Scores are the standardized data projected onto the component directions. IDs and timestamps are excluded.')
image('08_pca_variance_loadings.png')
table(['Component','Variance','Cumulative'],[[f'PC{i+1}',f'{v*100:.2f}%',f'{m["cumulative"][i]*100:.2f}%'] for i,v in enumerate(m['variance'])],[165,165,169])
p('Five components are needed for the predeclared 95% target and retain 99.28%. Four retain only 89.47%. Reduction is modest: six features become five components. PC1 and PC2 together explain 57.20%, so the two-dimensional scatter plot provides only a partial view.')
page()

section('5. Key insights and sensitivity')
p('The all-source table has 6,297 nonmissing PM2.5 readings: 3,387 from OpenAQ and 2,910 from PurpleAir. Their means are 32.61 and 31.04 µg/m³; medians are 27.00 and 23.55. Maxima of 298.0 and 551.6 show right-skewed distributions. Differences in sensor location, coverage and uncalibrated PurpleAir CF1 response prevent treating the mean difference as instrument bias.')
p('<b>Component interpretation.</b> The coefficients below are unit-length eigenvector entries, not feature–score correlations. PC1 contrasts higher humidity against lower temperature and wind. PC2 emphasizes PM2.5 positively and wind negatively. These are descriptive patterns, not causal effects; a component’s overall sign can be reversed without changing PCA.')
table(['Feature','PC1','PC2','PC3'],[[r['feature'].replace('_',' '),*[f'{r[f"PC{i}"]:.3f}' for i in [1,2,3]]] for r in m['loadings']],[229,90,90,90])
p('<b>Sensitivity.</b> Without IQR filtering, the complete primary cohort has 1,225 records and PC1 explains 37.73%. After filtering, 1,169 records remain and PC1 explains 38.09%. Both require five components to reach 95%. Only 56 of the 94 flagged records otherwise have every feature; the other 38 would already be excluded by completeness. Exclusions must not be counted twice.')
p('Five-component reconstruction has standardized RMSE 0.0851. Assertions check unit diagonal standardized covariance, variance fractions summing to one, the smallest component count reaching 95%, complete scores and unique integrated keys.')
p('<b>Limitations.</b> Missingness and complete-case selection change time/station coverage. A nearby weather station may not represent the sensor’s microenvironment. Repeated station weather in PCA weights conditions by available air sensors. Current discovery may miss historical sensors no longer listed. One month cannot establish seasonal patterns. IQR removal emphasizes ordinary conditions and must not dismiss true pollution events. Interpolation can reduce short-term variation. This PCA is descriptive; predictive work would need time-aware train/test separation.')
page()

section('6. Summary and reproducibility')
p('The workflow preserves original observations, records changes and produces a 7,511-row integrated table. One PurpleAir channel pair is rejected, 615 missing hours are exposed and 138 short gaps are filled. No weather feature crosses the redundancy threshold. A separate openly licensed cohort supports outlier-filtered PCA: 1,169 complete records and five components retain 99.28% of six standardized features’ variation.')
p('The main outcome is traceable preprocessing with explicit missingness. Modest dimensionality reduction and restricted coverage are findings, not defects to conceal. Plausibility checks, statistical flags and cohort exclusions serve distinct purposes and remain inspectable.')
p('<b>Reproduce the run.</b> Execute <font name="Courier">air-quality_self.ipynb</font> from top to bottom with the supplied requirements. Default execution reads archived responses and weather tables from <font name="Courier">data/air_quality_snapshot</font>; credentials are not embedded. The archive must accompany the notebook for offline reproduction. Set the download option and environment-variable API keys to obtain new data.')
p('The notebook includes explicit source links, stage counts, changed-record examples, nine figures, correlation/covariance analysis, PCA and assertions. Outputs include CSV snapshots, a complete Excel audit with native summary charts and embedded diagnostics, and report metrics. No presentation was prepared.')
p('<b>Environment.</b> Python 3.12; pandas 3.0.6; NumPy 2.5.3; Meteostat 2.1.5; Matplotlib 3.11.2; seaborn 0.13.2; XlsxWriter 3.2.9. Archived source data and metrics support reproducibility across future updates.')
p('<b>Sources</b>')
for text,url in [
('[1] OpenAQ: API, source data and retrieval documentation','https://docs.openaq.org/'),
('[2] OpenAQ: licenses and attribution metadata','https://docs.openaq.org/resources/licenses'),
('[3] Meteostat: hourly data','https://dev.meteostat.net/python/api/meteostat.hourly'),
('[3] Meteostat: nearby station metadata','https://dev.meteostat.net/python/api/meteostat.stations.nearby'),
('[4] Meteostat: data license','https://dev.meteostat.net/license'),
('[5] PurpleAir: API','https://api.purpleair.com/'),
('[5] PurpleAir: historical-data access','https://community.purpleair.com/t/about-the-purpleair-api/7145')]:
    p(f'{text}. <link href="{url}" color="blue">{url}</link>','SmallReport')

def footer(canvas,doc):
    canvas.saveState(); canvas.setFont('Helvetica',9); canvas.setFillColor(colors.HexColor('#637082'))
    canvas.drawString(48,27,'Jakarta air quality | January 2024 observations')
    canvas.drawRightString(547,27,str(doc.page)); canvas.restoreState()

doc=SimpleDocTemplate(str(root/'air_quality_report.pdf'),pagesize=(595.276,841.89),rightMargin=48,leftMargin=48,topMargin=42,bottomMargin=44,title='Jakarta Air Quality: Preprocessing and PCA',author='')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('Saved PDF companion:',root/'air_quality_report.pdf')
