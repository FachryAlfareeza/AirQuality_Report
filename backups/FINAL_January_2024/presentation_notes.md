# Presentation speaking notes — target 7 minutes 30 seconds

## 1. Jakarta Air Quality — 40 seconds
I made this notebook to combine air quality and weather data for Jakarta in January 2024. The focus is PM 2.5. My goal was to make each preprocessing step easy to follow. Whenever a cell changes the data, it shows sample rows, a summary, or a graph. This presentation follows the same order as the program.

## 2. Inputs — 55 seconds
I used OpenAQ and PurpleAir for air measurements and Meteostat for weather. OpenAQ starts with 3,990 rows and PurpleAir with 2,906. Weather contains 2,976 station-hours from four stations with data. A station-hour is not an air measurement. The saved JSON responses and weather CSV files make the notebook repeatable without downloading again. The files stay available so I can compare the starting data with the result.

## 3. Processing design — 60 seconds
I split the work into small cells: loading, cleaning, combining, hourly averaging, merging weather, and checking correlations. Pandas handles the tables. Matplotlib handles the graphs. Requests and Meteostat support data retrieval. I kept the preprocessing simple instead of adding more libraries. The source and sensor ID remain in the data so readings from different sensors stay separate. The notebook shows head() previews, but also counts and graphs because the first five rows alone might not show the changes.

## 4. Cleaning rules — 70 seconds
OpenAQ removes exact duplicates and keeps valid times and PM 2.5 values from zero to one thousand. Missing values fail the check, so 736 records are removed. That does not mean 736 outliers were found. PurpleAir has two channels. Both must pass the range check and their difference must be no more than ten or half their mean, whichever is larger. One record fails. Accepted channels are averaged. The rules are project choices, not a local calibration. The boxplots still show high values because a statistical outlier can be a real pollution event.

## 5. Merge — 60 seconds
The cleaned air tables use the same six columns before they are combined. I filter the chosen area and month, then average existing observations by sensor and UTC hour. No missing hours are added. There are still 6,159 rows. For weather, I choose the nearest available station to the city centre: Jakarta Observatory, station 96745. It provides 744 hours. A left merge by UTC hour adds the weather columns. The many-to-one check prevents the merge from multiplying rows. The final table has twelve columns.

## 6. Before and after — 60 seconds
The air data start with 6,896 records and finish with 6,159, so 737 records or about 10.69 percent are removed. Cleaning causes the reduction; filtering and hourly grouping do not remove more rows in this saved run. The final table has no missing values, although the code would leave missing weather unfilled. I check weather correlations on unique hours. No pair has an absolute correlation above 0.95, so no columns are removed. Temperature and humidity round to minus 0.95, but their unrounded value is below the cutoff in magnitude.

## 7. Graphs and summary — 60 seconds
The boxplots compare distributions before and after cleaning. The row chart shows how much data remains. The correlation heatmap shows relationships between weather variables. The final graph follows each UTC hour across January and shows source means together with counts. It is not a time-of-day average. OpenAQ has a mean PM 2.5 of 32.25 and median 26.85; PurpleAir has a mean 31.02 and median 23.55 micrograms per cubic metre. High values pull up the means. Different coverage means I cannot call the difference between sources a sensor bias.

## 8. Conclusion and limits — 45 seconds
The result is a consistent air and weather table with 6,159 rows and 12 columns. The main benefit is that I can follow how it was produced and rerun the steps from saved data. The checks are basic, and one weather station only represents city-level conditions. High readings still need interpretation. This simplified notebook does not use interpolation or PCA. The results describe patterns, not causes.

Timing is a rehearsal guide, not an automatic playback limit. Pause briefly on each diagram and keep the total below ten minutes.

Sources: https://docs.openaq.org/ ; https://api.purpleair.com/ ; https://dev.meteostat.net/python/api/meteostat.hourly
