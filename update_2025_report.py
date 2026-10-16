"""Write the plain-language article using the regenerated 2025 results."""
from pathlib import Path
import json

root=Path(__file__).resolve().parent
dest=root/'FINAL_2025_staging'
s=json.loads((dest/'outputs/summary.json').read_text())
fmt=lambda x:f'{x:,}'
tex=lambda x:str(x).replace('_',r'\_').replace('&',r'\&').replace('%',r'\%')
raw=s['raw_rows']; clean=s['clean_rows']; stages={x['stage']:x['rows'] for x in s['row_counts']}
rows,cols=s['shape']; removed=stages['Raw']-stages['Cleaned']
stats=s['source_summary']
source_rows='\n'.join(f"{name} & {fmt(int(stats['count'][name]))} & {stats['mean'][name]:.2f} & {stats['median'][name]:.2f} & {stats['max'][name]:.2f} \\\\" for name in stats['count'])
missing=sum(s['missing'].values())
missing_text=('All final columns have zero missing values in this saved run.' if not missing else
              'The final table still has missing weather values. These are left unfilled: '+', '.join(f"{tex(key)} ({fmt(value)})" for key,value in s['missing'].items() if value)+'.')
dropped=s['dropped']
drop_text=('No columns are removed in this run.' if not dropped else 'The removed columns are '+', '.join(tex(x) for x in dropped)+'.')
r=s['correlation'].get('temperature',{}).get('humidity')
corr_text='' if r is None else f'Temperature and humidity have a correlation of {r:.3f}. The decision uses the unrounded correlation.'
text=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.2cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,amsmath,booktabs,hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\title{Jakarta Air Quality: Basic Data Preprocessing}
\author{Fachry Alfareeza}
\date{January--December 2025 observations}
\begin{document}
\maketitle
\section{What I wanted to do}
I made this notebook to combine air quality readings with weather data for Jakarta. The main measurement is PM$_{2.5}$, which describes fine particles in the air. I wanted to see what happens during cleaning and merging, so the notebook shows sample rows, row counts, and graphs after each important step.

Originally, I wanted to use 3 data sources: OpenAQ's API, PurpleAir,'s API, and BMKG's weather API. But due to unavailability and the limited amount of BMKG's data, i chose to pull weather data straight from the meteostat library. I chose these sources because they have different formats and some readings need to be checked before they can be used together. The project covers the full 2025 calendar year: 1 January 2025 at 00:00 up to, but not including, 1 January 2026 at 00:00 in Jakarta time. This includes all of 31 December 2025. The selected area is longitude 106.689--106.978 and latitude $-6.370$--$-6.079$. UTC is used to match records from different sources.
\section{Data and program design}
OpenAQ and PurpleAir provide air measurements. Meteostat provides weather observations and station information. The starting data contain @OPENAQ_RAW@ OpenAQ rows, @PURPLE_RAW@ PurpleAir rows, and @WEATHER_RAW@ weather station-hours. @STATIONS@ weather stations have observations. A station-hour means one hour from one weather station.

The notebook uses pandas for tables and Matplotlib for graphs. Requests and Meteostat support the download functions. The full year is downloaded in shorter request windows, with pagination for OpenAQ. Successful API responses and weather CSV files are saved in a separate 2025 folder. Saved inputs are used by default, so the notebook can run again without new requests or API keys.

The cells follow this order: load the data, clean each source, combine the air measurements, group them by hour, select a weather station, merge the tables, and check correlations. I used operations such as \texttt{drop\_duplicates()}, \texttt{concat()}, \texttt{groupby()}, and \texttt{merge()} to pre-process the data. Each step that changes the data shows a preview, summary, or graph using \texttt{head()}, \texttt{display()}, or Matplotlib.
\section{Cleaning the air measurements}
For OpenAQ, I remove exact duplicate rows, convert time and PM$_{2.5}$ to the correct types, and keep valid times and PM$_{2.5}$ values between 0 and 1,000 $\mu$g/m$^3$. Missing values cannot pass this check. This reduces the table from @OPENAQ_RAW@ to @OPENAQ_CLEAN@ rows. Removed records can be duplicates, missing readings, or invalid readings; the row reduction should not be described as a count of statistical outliers.

PurpleAir has two channels, A and B. Both must be between 0 and 1,000. They must also satisfy
\[
|A-B|\leq\max\left(10,\;0.5\frac{A+B}{2}\right).
\]
I use the mean of the accepted channels as PM$_{2.5}$. This keeps @PURPLE_CLEAN@ of the original @PURPLE_RAW@ rows. The range and channel checks are simple project choices, not a local calibration or a health standard.

Before-and-after boxplots show how the distributions change. Points outside the whiskers are still shown; they are not automatically deleted. High readings can be real pollution events. The boxplots can look similar even when missing rows are removed because missing values are not plotted.
\section{Combining air and weather data}
I combine the air tables using the same fields: source, site ID, latitude, longitude, time, and PM$_{2.5}$. Rows with missing required fields are removed, and only the chosen area and year are kept. I then group existing readings by source, sensor location, and UTC hour and take their mean. No missing hours are added or filled. There are @FILTERED@ rows after filtering and @HOURLY@ rows after hourly grouping.

For weather, I remove exact duplicates and convert the measurements to numbers. Values outside the following ranges become missing: temperature $-30$ to $60\,^{\circ}$C, humidity 0--100\%, rain 0--500 mm, wind speed 0--250 km/h, and pressure 850--1,100 hPa. Missing weather values are left unfilled.

The nearest available station to the Jakarta centre is @STATION_ID@, @STATION_NAME@, with @WEATHER_HOURS@ hourly records. I join its weather to each air measurement by UTC hour. The merge checks that each air row matches at most one weather row. It adds the station ID and five weather columns to the six-column air table. @MISSING_TEXT@
\section{Results and before-and-after comparison}
\begin{center}
\begin{tabular}{lr}\toprule
Stage & Air rows \\\midrule
Starting data & @RAW@ \\
After cleaning & @CLEANED@ \\
After area and time filtering & @FILTERED@ \\
After hourly grouping & @HOURLY@ \\
After weather merge & @FINAL_ROWS@ \\\bottomrule
\end{tabular}
\end{center}
Cleaning removes @REMOVED@ air records, about @REMOVED_PCT@\% of the starting air records. The merge adds weather columns without multiplying the air rows.

I calculate Pearson correlations using one row per weather hour, so weather values are not counted repeatedly for different air sensors. The program removes a later weather column if its absolute correlation with a retained earlier column is greater than 0.95. @DROP_TEXT@ @CORR_TEXT@
\begin{center}
\begin{tabular}{lrrrr}\toprule
Source & Count & Mean & Median & Maximum \\\midrule
@SOURCE_ROWS@
\bottomrule
\end{tabular}
\end{center}
These PM$_{2.5}$ values are in $\mu$g/m$^3$. The means, medians, and maxima show the typical levels and how far the high readings extend. Different sensor and time coverage means a difference between sources does not establish sensor bias.

The notebook has four graph outputs: before-and-after boxplots, a row-count chart, a weather correlation heatmap, and hourly PM$_{2.5}$ means with the number of readings in each mean. The final graph follows the full 2025 period. The count plot helps explain whether a changing mean also involves changing coverage. The saved monthly coverage table reports available rows and sensors in each month; a full-year request does not mean every sensor reported every hour.
\section{Conclusion and limits}
The final table contains @FINAL_ROWS@ rows and @FINAL_COLS@ columns. The program makes the formats consistent, removes duplicate or invalid air readings, and adds weather from the same hour. Showing results after each step makes the process easier to check.

This basic version does not use interpolation or PCA. One weather station gives city-level context rather than the exact conditions at every sensor. High readings may need further investigation, and the results show patterns rather than causes. The notebook, saved inputs, exported tables, graphs, and this article all refer to the 2025 run.
\section*{Source links}
\begin{itemize}
\item OpenAQ: \url{https://docs.openaq.org/}
\item PurpleAir: \url{https://api.purpleair.com/}
\item Meteostat: \url{https://dev.meteostat.net/python/api/meteostat.hourly}
\end{itemize}
\end{document}
'''
values={
 'OPENAQ_RAW':fmt(raw['openaq_raw']),'PURPLE_RAW':fmt(raw['purpleair_raw']), 'WEATHER_RAW':fmt(raw['weather_raw']),
 'OPENAQ_CLEAN':fmt(clean['openaq_clean']),'PURPLE_CLEAN':fmt(clean['purpleair_clean']),
 'STATIONS':str(s['stations_with_data']),'STATION_ID':s['weather_station'],'STATION_NAME':s['weather_station_name'],
 'WEATHER_HOURS':fmt(s['weather_hours']),'MISSING_TEXT':missing_text,'DROP_TEXT':drop_text,'CORR_TEXT':corr_text,
 'RAW':fmt(stages['Raw']),'CLEANED':fmt(stages['Cleaned']),'FILTERED':fmt(stages['Filtered']),'HOURLY':fmt(stages['Hourly']),
 'FINAL_ROWS':fmt(rows),'FINAL_COLS':str(cols),'REMOVED':fmt(removed),'REMOVED_PCT':f'{100*removed/stages["Raw"]:.2f}',
 'SOURCE_ROWS':source_rows,
}
for key,value in values.items(): text=text.replace('@'+key+'@',value)
(root/'air_quality_report.tex').write_text(text,encoding='utf-8')
(dest/'air_quality_report.tex').write_text(text,encoding='utf-8')
print('Updated article with verified 2025 results.')
