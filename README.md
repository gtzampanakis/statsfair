pinnacle_download.py
=========

PinnacleSports is one of the largest bookmakers in the world. They have very large betting limits and never ban winning players. Due to those features they attract the sharpest bettors and thus their odds are widely considered the market consensus at any one time.

PinnacleSports do not hide their odds. They offer a free API, accessible to anyone, with the only limitation that the user should not make more than one call per minute. Having access to those odds is valuable to bettors and even more valuable to researchers building statistical models.

Since not all researchers are well-versed in HTTP and XML, I have decided to share the Python script I have been using to download the data. Once called, it will connect to the PinnacleSports API every 120 seconds (this interval is configurable) and save the data to an sqlite database. The script has no dependencies other than the Python standard library.

The database created by the script offers a convenient view, called GAMESDENORM that outputs a selection of the odds collected, more-or-less as they appear in [www.statsfair.com](www.statsfair.com/pinnacle), where pinnacle_download.py does the data collection.

You can use the sqlite3 command line shell (downloadable from [here](https://www.sqlite.org/download.html) to examine the data and/or export to file. Here is a sample session:

$ sqlite3 pinnacle_odds.db
SQLite version 3.8.7 2014-10-17 11:24:17
Enter ".help" for usage hints.
sqlite> .header on
sqlite> select * from gamesdenorm where evdate >= julianday('2014-12-20 16:45:00') and julianday('2014-12-21') order by evid, evdate limit 10;
424001394|2457012.19791667|2014-12-20 16:45:00|Soccer|Israel Prem|No|Bnei Sakhnin||Bnei Sakhnin|Maccabi Haifa||Maccabi Haifa|0|Match|0.0|m|moneyline|4.79|3.62|1.83333333333333|500|2457012.12583567|2014-12-20 15:01:12|1|1|1|1|3|2
424001394|2457012.19791667|2014-12-20 16:45:00|Soccer|Israel Prem|No|Bnei Sakhnin||Bnei Sakhnin|Maccabi Haifa||Maccabi Haifa|0|Match|0.5|s|spread|2.04||1.84033613445378|1000|2457012.12583567|2014-12-20 15:01:12|1|1|4|4||5
424001394|2457012.19791667|2014-12-20 16:45:00|Soccer|Israel Prem|No|Bnei Sakhnin||Bnei Sakhnin|Maccabi Haifa||Maccabi Haifa|0|Match|2.5|t|total|2.13||1.76335877862595|1000|2457012.12583567|2014-12-20 15:01:12|1|1|6|6||7
424001394|2457012.19791667|2014-12-20 16:45:00|Soccer|Israel Prem|No|Bnei Sakhnin||Bnei Sakhnin|Maccabi Haifa||Maccabi Haifa|1|1st Half|0.25|s|spread|1.87719298245614||2.0|500|2457012.12583567|2014-12-20 15:01:12|1|1|8|8||9
424001394|2457012.19791667|2014-12-20 16:45:00|Soccer|Israel Prem|No|Bnei Sakhnin||Bnei Sakhnin|Maccabi Haifa||Maccabi Haifa|1|1st Half|1.0|t|total|2.07||1.82644628099174|500|2457012.12583567|2014-12-20 15:01:12|1|1|10|10||11
424001396|2457012.22916667|2014-12-20 17:30:00|Soccer|Israel Prem|No|Maccabi Netanya||Maccabi Netanya|Hapoel Tel Aviv||Hapoel Tel Aviv|0|Match|0.0|m|moneyline|3.62|3.51|2.13|500|2457012.12583567|2014-12-20 15:01:12|1|1|14|14|16|15
424001396|2457012.22916667|2014-12-20 17:30:00|Soccer|Israel Prem|No|Maccabi Netanya||Maccabi Netanya|Hapoel Tel Aviv||Hapoel Tel Aviv|0|Match|0.25|s|spread|2.02||1.86206896551724|1000|2457012.12583567|2014-12-20 15:01:12|1|1|17|17||18
424001396|2457012.22916667|2014-12-20 17:30:00|Soccer|Israel Prem|No|Maccabi Netanya||Maccabi Netanya|Hapoel Tel Aviv||Hapoel Tel Aviv|0|Match|2.5|t|total|1.98039215686275||1.9009009009009|1000|2457012.12583567|2014-12-20 15:01:12|1|1|19|19||20
424001396|2457012.22916667|2014-12-20 17:30:00|Soccer|Israel Prem|No|Maccabi Netanya||Maccabi Netanya|Hapoel Tel Aviv||Hapoel Tel Aviv|1|1st Half|0.0|s|spread|2.39||1.60606060606061|500|2457012.12583567|2014-12-20 15:01:12|1|1|21|21||22
425484869|2457012.33333333|2014-12-20 20:00:00|E Sports|LOL IntExMas|No|Gambit Gaming||Gambit Gaming|Team Dignitas||Team Dignitas|0|Match|0.0|m|moneyline|2.17||1.70422535211268|500|2457012.12583567|2014-12-20 15:01:12|1|1|12|12||13
evid|evdatereal|evdate|sporttype|league|islive|pahnameraw|pahpitcher|pahname|pavnameraw|pavpitcher|pavname|penumber|pedesc|threshold|bettype|bettypehr|hprice|dprice|vprice|betlimit|snapshotdatereal|snapshotdate|opening|latest|id|hid|did|vid
sqlite> .mode csv
sqlite> .output odds.csv
sqlite> select * from gamesdenorm where evdate >= julianday('2014-12-20 16:45:00') and julianday('2014-12-21') order by evid, evdate;

The above will data in the file odds.csv. Remember to use data ranges when you have lots of data, otherwise the export file might be too large for your liking.

