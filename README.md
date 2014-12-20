pinnacle_download.py
=========

PinnacleSports is one of the largest bookmakers in the world. They have very large betting limits and never ban winning players. Due to those features they attract the sharpest bettors and thus their odds are widely considered the market consensus at any one time.

PinnacleSports do not hide their odds. They offer a free API, accessible to anyone, with the only limitation that the user should not make more than one call per minute. Having access to those odds is valuable to bettors and even more valuable to researchers building statistical models.

Since not all researchers are well-versed in HTTP and XML, I have decided to share the Python script I have been using to download the data. Once called, it will connect to the PinnacleSports API every 120 seconds (this interval is configurable) and save the data to an sqlite database. The script has no dependencies other than the Python standard library.

The database created by the script offers a convenient view, called `GAMESDENORM` that outputs a selection of the odds collected, more-or-less as they appear in [statsfair.com](http://www.statsfair.com/pinnacle), where pinnacle_download.py does the data collection.

You can use the sqlite3 command line shell (downloadable from [here](https://www.sqlite.org/download.html)) to examine the data and/or export to file. Here is a sample session:

```
$ sqlite3 pinnacle_odds.db
SQLite version 3.8.7 2014-10-17 11:24:17
Enter ".help" for usage hints.
sqlite> select evid, evdate, sporttype, pahname, pavname, 
round(hprice,2), round(dprice, 2), round(vprice, 2), betlimit 
from gamesdenorm 
where evdate >= julianday('2014-12-20 16:45:00') and julianday('2014-12-21') 
and sporttype = 'Soccer' 
order by evid, evdate 
limit 10;
423298448|2014-12-20 19:00:00|Soccer|Charleroi|Lierse|1.76|3.96|4.86|2000
423298448|2014-12-20 19:00:00|Soccer|Charleroi|Lierse|1.99||1.93|4000
423298448|2014-12-20 19:00:00|Soccer|Charleroi|Lierse|1.91||1.99|4000
423298448|2014-12-20 19:00:00|Soccer|Charleroi|Lierse|1.92||1.98|2000
423298448|2014-12-20 19:00:00|Soccer|Charleroi|Lierse|1.88||2.01|2000
423298449|2014-12-20 19:00:00|Soccer|Oostende|Cercle Brugge|1.83|3.75|4.73|2000
423298449|2014-12-20 19:00:00|Soccer|Oostende|Cercle Brugge|2.09||1.83|4000
423298449|2014-12-20 19:00:00|Soccer|Oostende|Cercle Brugge|2.02||1.88|4000
423298449|2014-12-20 19:00:00|Soccer|Oostende|Cercle Brugge|1.98||1.93|2000
423298449|2014-12-20 19:00:00|Soccer|Oostende|Cercle Brugge|1.97||1.92|2000
sqlite> .mode csv
sqlite> .output odds.csv
sqlite> select evid, evdate, sporttype, pahname, pavname, 
round(hprice,2), round(dprice, 2), round(vprice, 2), betlimit 
from gamesdenorm 
where evdate >= julianday('2014-12-20 16:45:00') and julianday('2014-12-21') 
and sporttype = 'Soccer' 
order by evid, evdate 
limit 10;
```

The above will data in the file `odds.csv`. Remember to use data ranges when you have lots of data, otherwise the export file might be too large for your liking.

