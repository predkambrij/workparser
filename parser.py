import config
import urllib2,base64,re,time,datetime,sys


def get_data(file_loc="",web_loc="",username="",password=""):
    """
    If you decited to read from file just file_loc="<file location>" needed
    If you want to read from web trac ticket you need to give web_loc and username and password for basic authentication
    """
    if web_loc!="":
        request = urllib2.Request(web_loc)
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)   
        result = urllib2.urlopen(request)
        result= result.read()
        
        adding = 0
        description = []
        for line in result.split("\n"):
            if adding == 1 and '</textarea>' in line:
                break
            if adding == 1:
                description.append(line)
            if '<textarea id="field-description" name="field_description"' in line:
                adding = 1
        return description

    elif file_loc!="":
        try:
            return file(file_loc,"rb").read().split("\n")
        except IOError,e:
            print e
    else:
        raise ValueError, "No location or web address given"

def parser(data):
    """
    :parm data: list of records
    """
    days = []
    skipped_days = []

    for line in data:
        stripped_line = line.strip()

        if stripped_line == "":
            # skip empty line
            continue
        if re.match("^[0-9]{1,2}.[0-9]{1,2}$", stripped_line):
            # add new day
            # append tuple as example ('30.10', [ ... day entries ... ])
            days.append(tuple([stripped_line,[]]))
        elif re.match("^[0-9]{1,2}:[0-9]{2}[ ]*-[ ]*[0-9]{1,2}:[0-9]{2}[ ]*=[ ]*.*$", stripped_line):
            # add new day entry
            try:
                days[-1][1].append(stripped_line)
            except: skipped_days.append(stripped_line) 
        else:
            # unparsable line
            skipped_days.append(stripped_line)
    return days,skipped_days

def mock_date(date,year,start,end,ret=""):
    if int(time.mktime(time.strptime(start, "%H:%M"))) < int(time.mktime(time.strptime(end, "%H:%M"))):
        return date
    else:
        return (datetime.datetime.fromtimestamp(int(time.mktime(time.strptime(date+"."+year, "%d.%m.%Y"))))+datetime.timedelta(days=1)).strftime("%d.%m")

def time_calculator(days):
    year = "2012"
    ndays = []
    for date, records in days:
        for record in records:
            start_end, comment = record.split("=",1)
            start = start_end.split("-")[0].strip()
            end = start_end.split("-")[1].strip()
            comment = comment.strip()

            start_sec = int(time.mktime(time.strptime(date+"."+year+" "+start, "%d.%m.%Y %H:%M")))
            end_sec = int(time.mktime(time.strptime(mock_date(date,year,start,end)+"."+year+" "+end, "%d.%m.%Y %H:%M")))

            str_diff = format_seconds(end_sec-start_sec)
            ndays.append({"year":year,"date":date,"start":start,"end":end,"duration":(end_sec-start_sec),"str_diff":str_diff,"comment":comment})
    return ndays

def format_seconds(sec):
    if sec < 60:
        return str(sec)+" s"
    elif sec < 3600:
        return str(sec/60)+"m"
    elif sec < 86400:
        return str(sec/60/60)+"h "+ str((sec/60)%60)+"m"
    else:
        return str(sec/60/60/24)+"d "+str((sec/60/60)%24)+"h "+ str((sec/60)%60)+"m"+"=="+ str(sec/60/60)+"h "+ str((sec/60)%60)+"m"

def find_tags(comment):
    return [ x for x in comment.split() if re.match("^#[a-zA-Z]+$",x)]

def selected_records(all_times, regex="" ,tags=[]):
    return [x for x in all_times if (regex=="" or re.match("^.*"+regex+".*$",x["comment"])) and (tags==[] or all((y in find_tags(x["comment"])) for y in tags))]

def print_selected(records,overall_time=False):
    formated_records = "\n".join([x["date"]+"."+x["year"]+"\t"+x["start"]+"-"+x["end"]+"\t"+x["str_diff"]+"\t"+x["comment"] for x in records])
    all_time = sum(x["duration"] for x in records)
    return formated_records+"\nOverall: "+format_seconds(all_time)

def export_to_excel_selected(records,overall_time=False, skip_tags=True):
    formated_records = "\n".join([x["date"].replace(",",".")+"."+"\t"+x["start"]+"\t"+x["end"]+"\t"+x["str_diff"]+"\t"+" ".join(word for word in x["comment"].split(" ") if not word.startswith("#")).strip() for x in records])
    file("out.xls","wb").write(formated_records)
    return

def print_usage(additional=""):
    sys.stderr.write(
        ("" if additional=="" else additional+"\n")
        +"Usage: parser.py \"tags separated with spaces\" \"regex\"\n"
        +"Examples:\n"
        +"Given tags and regex (note: regex is actually ^.*bugfix.*$)\n"
        +"python parser.py \"#home #python #urllib\" \"bugfix\"\n"
        +"Ommited tags\n"
        +"python parser.py \"\" \"bugfix\"\n"
        +"Ommited regex\n"
        +"python parser.py \"#home #python #urllib\" \"\"\n")
    sys.exit(1)

def parse_input():
    if len(sys.argv) != 3:
        print_usage("You must provide two arguments! Given %d"% (len(sys.argv)-1))
    return find_tags(sys.argv[1]),sys.argv[2]

# provide list with records
if config.use_web==True:
    data = get_data(web_loc=config.web_location,username=base64.b64decode(config.username),password=base64.b64decode(config.password))
else:
    data = get_data(file_loc=config.file_location)

# get input (list of tags and string regex)
tags,regex = parse_input()

# structured data
time_pairs,skipped = parser(data)

# even more structured data
all_times = time_calculator(time_pairs)

# select records which match all tags AND regex
selected = selected_records(all_times,regex=regex,tags=tags)

# format for print and add overall spent time
out = print_selected(selected)
export_to_excel_selected(selected)
print out

