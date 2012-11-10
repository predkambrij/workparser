# That's credentials which will be used for parse from ticket description from trac project

# Username and password is used for basic authentication
# Provide basic encoded username and password
# You will get it with:
#import base64
#print base64.b64encode("John")
#print base64.b64encode("Smith")

# Example. If username is "John" and password is "Smith" following entry is correct:
username='Sm9obg=='
password='U21pdGg='

# Example URL to web page
web_location="http://your.web.page.tld/ticket/100"

# file will be used if you'll set parameter use_web=False
file_location="example_work_data.dat"

# use file or data retreived from web
use_web=False

