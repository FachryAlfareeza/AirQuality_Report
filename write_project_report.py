from pathlib import Path
import json
import pandas as pd

run = Path('outputs/air-quality-review/20260927T122050540703Z')
m = json.loads((run/'report_metrics.json').read_text(encoding='utf-8'))
stages = pd.read_csv(run/'Stages.csv').set_index('stage')
daily = pd.read_csv(run/'Chart_daily.csv')

def escape(s):
    return str(s).replace('&', r'\&').replace('_', r'\_').replace('%', r'\%')

def bars(labels, values, ymax, ylabel, color='blue'):
    out=[r'\begin{center}\setlength{\unitlength}{1pt}\begin{picture}(450,185)',
         r'\put(40,30){\line(1,0){390}}\put(40,30){\line(0,1){130}}',
         r'\put(0,170){\small '+ylabel+'}']
    for tick in range(6):
        y=30+tick*26
        out += [r'\put(8,%g){\makebox(25,10)[r]{\scriptsize %g}}' % (y-3,tick*ymax/5)]
    width=350/len(labels)
    for i,(lab,v) in enumerate(zip(labels,values)):
        x=58+i*width; h=v/ymax*130
        out += [r'\put(%.2f,30){\color{%s}\rule{%.2fpt}{%.2fpt}}' % (x,color,width*.56,h),
                r'\put(%.2f,%.2f){\makebox(%.2f,10){\scriptsize %.1f}}' % (x-8,35+h,width*.56+16,v),
                r'\put(%.2f,13){\makebox(%.2f,10){\scriptsize %s}}' % (x-12,width*.56+24,escape(lab))]
    return '\n'.join(out+[r'\end{picture}\end{center}'])

def daily_plot():
    out=[r'\begin{center}\setlength{\unitlength}{1pt}\begin{picture}(455,185)',
         r'\put(38,28){\line(1,0){390}}\put(38,28){\line(0,1){135}}',
         r'\put(0,171){\small Daily PM$_{2.5}$ mean ($\mu$g/m$^3$)}']
    for tick in range(5):
        out += [r'\put(4,%g){\makebox(28,10)[r]{\scriptsize %g}}' % (25+tick*30,tick*20)]
    for i,day in [(0,'1 Jan'),(7,'8 Jan'),(14,'15 Jan'),(21,'22 Jan'),(30,'31 Jan')]:
        out += [fr'\put({38+i*12.5-12},12){{\scriptsize {day}}}']
    for col,color in [('OpenAQ','blue'),('PurpleAir','orange')]:
        out += [fr'\color{{{color}}}']
        vals=daily[col].tolist()
        for i in range(len(vals)-1):
            x1,x2=38+i*12.5,38+(i+1)*12.5
            y1,y2=28+vals[i]*1.5,28+vals[i+1]*1.5
            out += [fr'\qbezier({x1:.2f},{y1:.2f})({(x1+x2)/2:.2f},{(y1+y2)/2:.2f})({x2:.2f},{y2:.2f})']
    out += [r'\color{black}\put(280,165){\scriptsize\textcolor{blue}{OpenAQ}\quad\textcolor{orange}{PurpleAir}}']
    return '\n'.join(out+[r'\end{picture}\end{center}'])

missing=bars(['Combined','Hourly','Filled'], [stages.loc[x,'missing_cells'] if False else pd.read_csv(run/(x.replace(' ','_')+'.csv')).pm25.isna().mean()*100 for x in ['Air combined','Air hourly','Air filled']],20,'Missing PM$_{2.5}$ (percent)')
scree=bars([f'PC{i+1}' for i in range(6)],[x*100 for x in m['variance']],50,'Explained variance (percent)')
cumulative_rows='\n'.join(fr'PC{i+1} & {100*v:.2f}\% & {100*m["cumulative"][i]:.2f}\% \\' for i,v in enumerate(m['variance']))
loading_rows='\n'.join(escape(r['feature'])+' & '+ ' & '.join(f'{r[f"PC{i}"]:.3f}' for i in [1,2,3])+r' \\' for r in m['loadings'])

tex=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=2cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath,booktabs,array,xcolor,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue,linkcolor=blue}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\renewcommand{\arraystretch}{1.16}
\definecolor{blue}{RGB}{40,120,181}
\definecolor{orange}{RGB}{217,95,2}
\pagestyle{plain}
\begin{document}
\begin{center}
{\LARGE\bfseries Jakarta Air Quality}\[5pt]
{\large A reproducible preprocessing and PCA study}\[5pt]
January 2024 observations\quad\textbar\quad Rekayasa Data
\end{center}

\section*{1. Dataset description and justification}
\textbf{Research question.} How do quality checks, hourly alignment and weather integration change the usable Jakarta PM$_{2.5}$ observations, and how compactly can principal component analysis (PCA) represent their joint variation?

The study selects observations inside longitude 106.689--106.978 and latitude $-6.370$--$-6.079$, from 1 January 2024 at 00:00 to 1 February 2024 at 00:00 in Jakarta time. The interval includes its start and excludes its end. UTC is used for joins; local time is used for interpretation.

\begin{center}\begin{tabular}{p{2.5cm}rp{9cm}}\toprule
Source & Records & Content and role \\\midrule
OpenAQ & 3,990 & Original PM$_{2.5}$ observations from eight contributing sensors. Includes several providers and sensor technologies. \\
PurpleAir & 2,906 & Public outdoor sensor history, with channels A and B; supplementary source comparison. \\
Meteostat & 2,976 & Weather station-hours in the target interval, from four stations with data; five stations were discovered. \\\bottomrule
\end{tabular}\end{center}

\textbf{Why this dataset?} Multiple schemas, missing measurements, disagreement between instrument channels, irregular coverage and distinct spatial supports require real preprocessing. A month-long local selection is small enough to inspect while retaining temporal and spatial variation. No synthetic measurements are added except explicitly flagged short-gap interpolation.

\textbf{Open-data scope.} The primary PCA cohort contains only OpenAQ records whose location metadata explicitly specifies US Public Domain, CC0 1.0 or CC BY 4.0, combined with Meteostat weather. It initially has 3,064 sensor-hours from six sensors. Other OpenAQ providers with unstated licenses and PurpleAir remain supplementary in the audit. API accessibility is not assumed to establish an open license. Provider names and license labels are exported in the source catalog. [1--4]

\textbf{Originality and provenance.} The exact region, month, licensed subset, weather matching and stage audit define this project's selection. Uniqueness relative to classmates still requires confirmation through the class register. Archived responses were retrieved in September 2026; observation dates are January 2024. The supplied assignment's 2025 deadline is historical, and this report does not claim an earlier submission date.

\newpage
\section*{2. Cleaning and before/after changes}
Exact duplicate rows are checked first. Numeric values and timestamps are parsed explicitly. PM$_{2.5}$ outside 0--1,000 $\mu$g/m$^3$ is marked missing. This is a coarse plausibility rule, not a health threshold. PurpleAir requires two valid channels and
\[
 |A-B|\leq\max\{10,\;0.5(A+B)/2\}.
\]
The channel tolerance is a transparent project heuristic, not a validated local calibration. It rejects one available channel pair. OpenAQ values are not assumed to be uniformly reference-grade. Valid high pollution episodes remain in the all-source archive.

Weather limits are $-30$--60 $^\circ$C, 0--100\% relative humidity, 0--500 mm hourly rain, 0--250 km/h wind and 850--1,100 hPa pressure. No available weather measurement is changed by these bounds in this run. Rows outside the selected interval/area or without a usable key are excluded; none of the combined air rows required that exclusion here.

\begin{center}\begin{tabular}{lrr}\toprule
Stage & Rows & Missing PM$_{2.5}$ \\\midrule
Combined, cleaned sources & 6,896 & 737 \\
Hourly grid before filling & 7,511 & 1,352 \\
Hourly grid after filling & 7,511 & 1,214 \\
Weather-integrated final table & 7,511 & 1,214 \\\bottomrule
\end{tabular}\end{center}

__MISSING_PLOT__
\textbf{Interpretation.} Resampling adds 615 absent sensor-hours between each sensor's first and last records. It exposes missing observations rather than creating new observed data. Linear interpolation fills 138 complete internal runs of at most two missing hours. Longer and edge gaps remain missing. The final missing fraction is 16.16\%, down from 18.00\% on the same hourly grid; the initial 10.69\% uses a smaller denominator.

Weather is separately reindexed by station. Bounded gaps up to three hours can be interpolated, except rainfall; none are filled in this snapshot. The integrated table retains 1,488 missing rainfall values (19.81\%). Missing rainfall is not treated as zero.

\newpage
\section*{3. Integration and redundant attributes}
Each air sensor is assigned to the nearest weather station that has usable observations in the period. Great-circle (Haversine) distance uses coordinates in radians and Earth radius 6,371 km. Distances range from 0.13 to 13.93 km. The assignment is fixed by location rather than changed hour by hour.

Air and weather are joined on the assigned station identifier and UTC hour. Both joins validate a many-to-one relationship, preventing duplicate weather records from multiplying air records. The resulting 7,511 rows and 22 columns include source identifiers, weather, distances, imputation flags and Jakarta-time features. No duplicate source--sensor--hour remains.

\textbf{Redundancy test.} Pearson correlations are computed on distinct station-hours so stations linked to several air sensors are not repeatedly counted. Attributes would be dropped when an earlier attribute has absolute correlation greater than 0.95. No pair crosses that threshold. In particular, temperature and humidity are strongly negatively correlated ($r=-0.931$), but retaining both is consistent with the stated cutoff.

\begin{center}\begin{tabular}{lr}\toprule
Weather pair & Pearson $r$ \\\midrule
Temperature--humidity & $-0.931$ \\
Humidity--wind speed & $-0.471$ \\
Temperature--wind speed & $0.337$ \\
Humidity--rain & $0.199$ \\
Rain--wind speed & $-0.045$ \\\bottomrule
\end{tabular}\end{center}

__DAILY_PLOT__
\textbf{Observed temporal pattern.} Both source series show elevated daily means near the start of the month and lower values through much of the middle of the month, with later increases. These are descriptive averages of available sensor-hours, including flagged imputations. Coverage and locations differ by source; the plot is not a calibrated comparison or a citywide exposure estimate. The notebook separately plots hourly reporting counts so changes in means can be assessed alongside coverage.

\newpage
\section*{4. Outlier removal and dimensionality reduction}
For the primary open-data cohort, fixed per-sensor quartiles are estimated from the raw PM$_{2.5}$ series. Bounds are $Q_1-1.5\,\mathrm{IQR}$ and $Q_3+1.5\,\mathrm{IQR}$, requiring at least four readings and nonzero IQR. The same bounds flag raw and processed records. Of 3,064 primary sensor-hours, 94 extremes are excluded from a separate typical-condition PCA cohort. This removes statistical extremes for this analysis without deleting them from the final integration archive.

After this step, 1,801 additional rows lack at least one selected feature, leaving 1,169 complete rows. Rainfall coverage is a material restriction: only five of the six primary sensors remain, and one sensor supplies 717 rows. This is a selected cohort, not an unbiased sample of Jakarta conditions.

Six features enter PCA: PM$_{2.5}$, temperature, humidity, rain, wind speed and pressure. Each is centered and divided by its sample standard deviation:
\[
 Z_{ij}=\frac{X_{ij}-\bar X_j}{s_j},\qquad
 Z=U\Sigma V^\mathsf{T},\qquad
 \lambda_j=\frac{\Sigma_{jj}^2}{n-1}.
\]
PCA scores are $ZV$; explained variance is $\lambda_j/\sum_k\lambda_k$. Standardization prevents variables with larger units from dominating. The standardized covariance matrix, scaling parameters, component coefficients and scores are exported. Identifier and time fields are not PCA inputs.

__SCREE_PLOT__
\begin{center}\begin{tabular}{lrr}\toprule
Component & Individual variance & Cumulative variance \\\midrule
__VARIANCE_ROWS__
\bottomrule\end{tabular}\end{center}
Five components are required to reach the predeclared 95\% target, retaining 99.28\%. Four retain only 89.47\%. Thus reduction is modest (six to five features), and the result is not forced into two dimensions. The first two components explain only 57.20\%; their scatter plot is a partial view.

\newpage
\section*{5. Key insights and sensitivity}
The all-source table contains 6,297 nonmissing PM$_{2.5}$ values: 3,387 from OpenAQ and 2,910 from PurpleAir. Their descriptive means are 32.61 and 31.04 $\mu$g/m$^3$, with medians 27.00 and 23.55. Maxima of 298.0 and 551.6 illustrate the right-skewed distributions. Unequal coverage, sensor response and uncalibrated PurpleAir CF1 values prevent interpreting the difference in means as instrument bias.

\textbf{What the components describe.} The table shows unit-length component coefficients, not correlations between variables and component scores. PC1 contrasts higher humidity with lower temperature and wind speed. PC2 emphasizes PM$_{2.5}$ positively and wind speed negatively. These signs describe variation in this cohort and do not establish causal effects. A component's overall sign could be reversed without changing the solution.

\begin{center}\begin{tabular}{lrrr}\toprule
Feature & PC1 & PC2 & PC3 \\\midrule
__LOADING_ROWS__
\bottomrule\end{tabular}\end{center}

\textbf{Sensitivity to outlier removal.} Without IQR trimming, the complete primary cohort has 1,225 records and PC1 explains 37.73\%. With trimming, it has 1,169 records and PC1 explains 38.09\%. Both require five components for 95\% variance. Only 56 of the 94 flagged primary records otherwise have all required features; the other 38 would already be excluded by completeness. This distinction avoids double-counting exclusions.

The five-component reconstruction has standardized root-mean-square error 0.0851. Notebook assertions verify unit diagonal standardized covariance, total explained variance of one, selection of the smallest component count attaining 95\%, complete PCA scores and unique integrated keys.

\textbf{Limits.} Missing data are not random by design, and complete-case selection can change station and time coverage. Linked weather stations represent nearby conditions rather than the sensor microenvironment. Repeated station weather in the observation-level PCA weights conditions according to available air sensors. Current sensor discovery can omit historical sensors no longer listed. The one-month window does not establish seasonal patterns. IQR exclusion emphasizes ordinary conditions and should not be used to dismiss genuine pollution events. Interpolation can reduce short-term variability, and PCA is fitted descriptively on the entire selected cohort; predictive evaluation would require a separate time-aware training protocol.

\newpage
\section*{6. Summary and reproducibility}
The workflow preserves downloaded values, records substantive transformations and produces a 7,511-row integrated table. One PurpleAir channel pair is rejected, 615 unobserved hours become explicit, and 138 short gaps are filled. No weather feature is removed by the correlation threshold. An explicitly licensed primary cohort supports a separate outlier-filtered PCA: 1,169 complete records, six standardized features and five retained components explain 99.28\% of variation.

The main outcome is improved traceability and an explicit treatment of missingness. The dimensionality reduction is modest, and coverage restrictions are important findings rather than details to conceal. Scientific plausibility checks, statistical outlier flags and cohort exclusions serve different purposes and are recorded separately.

\textbf{Reproduction.} Run \texttt{air-quality\_self.ipynb} from top to bottom in a Python environment with the supplied requirements. The default uses archived API responses and Meteostat tables in \texttt{data/air\_quality\_snapshot}; API credentials are not embedded. A fresh download can be requested through the notebook setting, using environment variables for keys. The archive must accompany the notebook for offline reproduction.

The executed notebook includes source links, stage counts, changed-record examples, nine diagnostic figures, covariance/correlation analysis, PCA and validation assertions. Each run writes raw/intermediate/final CSV tables, a workbook with the complete audit, editable summary charts and diagnostic images, plus numerical report metrics. The presentation is outside the scope of this deliverable.

\textbf{Environment for the reported run.} Python 3.12; pandas 3.0.6; NumPy 2.5.3; Meteostat 2.1.5; Matplotlib 3.11.2; seaborn 0.13.2; XlsxWriter 3.2.9. Source responses and numeric results are saved so a reviewer can separate library changes from data changes.

\subsection*{Sources}
\small
[1] OpenAQ. API and source-data documentation. \url{https://docs.openaq.org/}. Location query uses the bounding box and January 2024 interval stated in Section 1; sensor-specific endpoint links are in the exported source catalog.

[2] OpenAQ. Licenses resource and attribution metadata. \url{https://docs.openaq.org/resources/licenses}. Primary cohort eligibility follows the license labels returned with location metadata, rather than a blanket license assumption.

[3] Meteostat. Hourly station data. \url{https://dev.meteostat.net/python/api/meteostat.hourly}. Nearby-station metadata: \url{https://dev.meteostat.net/python/api/meteostat.stations.nearby}.

[4] Meteostat. Data license. \url{https://dev.meteostat.net/license}. Attribution must accompany reuse; consult current provider-specific terms.

[5] PurpleAir. API and historical-data access. \url{https://api.purpleair.com/}; \url{https://community.purpleair.com/t/about-the-purpleair-api/7145}. Used as a supplementary public-sensor source with authenticated access.
\end{document}
'''
tex=tex.replace('__MISSING_PLOT__',missing).replace('__DAILY_PLOT__',daily_plot()).replace('__SCREE_PLOT__',scree).replace('__VARIANCE_ROWS__',cumulative_rows).replace('__LOADING_ROWS__',loading_rows)
Path('air_quality_report.tex').write_text(tex,encoding='utf-8')
print('Wrote standalone six-page report source with embedded vector figures.')
