#!/run/current-system/sw/bin/bash
#!/usr/bin/env bash

# add info when locked
echo  "$(date +%Y-%m-%d-%H-%M-%S) SCREEN LOCKED" >> /home/lojze/newhacks/time_tracking.log

# actually lock
xscreensaver-command -lock >/tmp/lock_err_loj 2>&1
xset dpms force off

#watch_data=$(/run/current-system/sw/bin/xscreensaver-command -watch | grep -i unblank -m 1) # doesn't work as expected

# check every x seconds if screen unlocked  
for((i=0;;i++)); do 
    sleep 2 
    status=$(xscreensaver-command -time 2>&1 | grep "non-blanked" )
    status_matched=$? 

    # if regex matched write unlock time and exit  
    if [ $status_matched -eq 0 ];then
        # add info when unlocked
        echo  "$(date +%Y-%m-%d-%H-%M-%S) SCREEN UNLOCKED ($status)" >> /home/lojze/newhacks/time_tracking.log
        break
    fi         

    # check every 2 seconds
done 

exit 0 

