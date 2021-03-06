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
        16.10.2012	14:00-14:30	30m	#programming #python #urllib2 #bugfix Bugfix with urllib library ticket #123
        16.10.2012	14:30-14:45	15m	#programming #python #hacking Hacking with python for fun (ticket #150)
        Overall: 45m

        $ python parser.py "#air" ""
        16.10.2012	10:00-14:00	4h 0m	#air Mixing the air
        17.10.2012	7:15-9:00	1h 45m	Driving with a car #car #air
        Overall: 5h 45m

        $ python parser.py "" "ticket"
        16.10.2012	14:00-14:30	30m	#programming #python #urllib2 #bugfix Bugfix with urllib library ticket #123
        16.10.2012	14:30-14:45	15m	#programming #python #hacking Hacking with python for fun (ticket #150)
        Overall: 45m

        $ python parser.py "" ""
        16.10.2012	10:00-14:00	4h 0m	#air Mixing the air
        16.10.2012	14:00-14:30	30m	#programming #python #urllib2 #bugfix Bugfix with urllib library ticket #123
        16.10.2012	14:30-14:45	15m	#programming #python #hacking Hacking with python for fun (ticket #150)
        17.10.2012	6:00-7:15	1h 15m	Fixing an another bug
        17.10.2012	7:15-9:00	1h 45m	Driving with a car #car #air
        Overall: 7h 45m

### Example of NixOS configuration which is adding time tracks for measuring working time: 
        systemd.services."my-pre-suspend" =
            { description = "Pre-Suspend Actions";
                wantedBy = [ "suspend.target" ];
                before = [ "systemd-suspend.service" ];
                script = ''
                        # usefull for debug that this part of code really runs
                        /run/current-system/sw/bin/date > /tmp/MY-PRE-RESUME
                        # add info to my personal time tracker
                        /run/current-system/sw/bin/echo  "$(/run/current-system/sw/bin/date +%Y-%m-%d-%H-%M-%S) PRESUSPEND" >> /home/lojze/newhacks/time_tracking.log
                        # lock screen
                        /home/lojze/newhacks/root_exec.sh /run/current-system/sw/bin/xscreensaver-command -lock 2>/tmp/lock_err
                    '';
        
                serviceConfig.Type = "simple";
            };
        
        systemd.services."my-post-suspend" =
            { description = "Post-Suspend Actions";
                wantedBy = [ "suspend.target" ];
                after = [ "systemd-suspend.service" ];
                script = ''
                        # usefull for debug that this part of code really runs
                        /run/current-system/sw/bin/date > /tmp/MY-POST-RESUME
                        # add info to my personal time tracker
                        /run/current-system/sw/bin/echo  "$(/run/current-system/sw/bin/date +%Y-%m-%d-%H-%M-%S) POSTSUSPEND" >> /home/lojze/newhacks/time_tracking.log
                    '';
        
                serviceConfig.Type = "simple";
            };


