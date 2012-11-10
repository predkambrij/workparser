#Work parser 

## What is this?
Workparser is parser which parses your tasks and returns selected tasks by query (tags and regex) and with calculated time.

### Methods to retreive data:
* Work log stored into file
* Work log stored into trac ticket (description field)

### Requirements:
* python2.7 and modules urllib2,base64,re,time,datetime,sys

### Required files:
* parser.py - parser
* config.py - config data

### Example (from included file example\_work\_data.dat):
1. configure config.py for your needs (see config.sample.py it's very brief) or just copy it to config.py for including example
2. run

    $ python parser.py "#programming #python" "ticket"

   Output:

    16.10.2012	14:00-14:30	30m	#programming #python #urllib2 #bugfix Bugfix with urllib library ticket #123
    16.10.2012	14:30-14:45	15m	#programming #python #hacking Hacking with python for fun (ticket #150)
    Overall: 45m

