# If username and password for basic authentication contains special characters
# use %__ where _ is number represented in uri eg. %40 for @
web_uri= "http://user:pass@domain.tld/login/xmlrpc"

web_ticket_num=123

# file will be used if you'll set parameter use_web=False
file_location="data.dat"

# use file or data retreived from web
use_web=False

# path to time_tracking.log file producted by systemd pre and post sleep hook and lock_screen.sh
time_tracking_log="/path/to/time_tracking.log"

import os
class Config:
    fetch_from_web=False
    file_location=os.path.dirname(__file__)+"/inp.dat"
    pass

