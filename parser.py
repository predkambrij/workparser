# -*- coding:utf8 -*-
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
            # comment structure:
            # comment
            # or
            # comment + money entry
            # or
            # comment + money entry + real comment
            # or
            # comment + real comment
            if "//" in comment:
                comment, real_comment = comment.rsplit("//", 1)
            else:
                real_comment = ""
            
            if "!#" in comment:
                comment, money_part = comment.rsplit("!#", 1)
            else:
                money_part = ""
            
            # strip all tree
            comment, money_part, real_comment = comment.strip(), money_part.strip(), real_comment.strip()
            
            start_sec = int(time.mktime(time.strptime(date+"."+year+" "+start, "%d.%m.%Y %H:%M")))
            end_sec = int(time.mktime(time.strptime(mock_date(date,year,start,end)+"."+year+" "+end, "%d.%m.%Y %H:%M")))

            str_diff = format_seconds(end_sec-start_sec)
            ndays.append({"year":year,"date":date,"start":start,"end":end,"duration":(end_sec-start_sec),"str_diff":str_diff,
                                                        "comment":comment, "money_part":money_part, "real_comment":real_comment, "start_sec":start_sec})
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

class MoneyParser:
    def __init__(self):
        # group by day and month
        self.day_income_total = {}
        self.day_outcome_total = {}
        self.month_income_total = {}
        self.month_outcome_total = {}
        self.income_total = {}
        self.outcome_total = {}
        
        self.default_currency = u"€"
        
        
    def parse_moneyword(self, money_word):
        """
        Parse direction, value and currency from moneyword in money section
        for example o_15.4€ => direction:out, value:15.4, currency:€
        """
        if money_word[2:].lower() == "todo":
            value = money_word[2:]
            currency = self.default_currency
        else:
            if not money_word[-1].isdigit():
                currency = money_word[-1]
                value = float(money_word[2:-1])
            else:
                currency = self.default_currency
                value = float(money_word[2:])
            
        if money_word.startswith("o_"):
            direction = "out"
        elif money_word.startswith("i_"):
            direction = "in"
        
        return currency, value, direction
    
    def write_money_to_class_attributes(self, direction, currency, value):
        # outgoing money :(
        if direction == "out":
            # daily
            if self.day_outcome_total.has_key(currency):
                self.day_outcome_total[currency] += value
            else:
                self.day_outcome_total[currency] = value
            
            # monthly
            if self.month_outcome_total.has_key(currency):
                self.month_outcome_total[currency] += value
            else:
                self.month_outcome_total[currency] = value
            
            # total
            if self.outcome_total.has_key(currency):
                self.outcome_total[currency] += value
            else:
                self.outcome_total[currency] = value
        elif direction == "in":
            # daily
            if self.day_income_total.has_key(currency):
                self.day_income_total[currency] += value
            else:
                self.day_income_total[currency] = value
            
            # monthly
            if self.month_income_total.has_key(currency):
                self.month_income_total[currency] += value
            else:
                self.month_income_total[currency] = value
            
            # total
            if self.income_total.has_key(currency):
                self.income_total[currency] += value
            else:
                self.income_total[currency] = value
    
    def parse_moneywords(self, moneywords):
        """
        parse value and description from money section
        for eg. from this:
        !# o_3.25€ dancing o_3.2€ cocktail with strong alcohol
        to that:
        out 3.25€ - dancing
        out 3.2€ - cocktail with strong alcohol
        
        also count money to class attributes
        
        """
        ret_str = ""
        first_word = False
        for money_word in moneywords.split(" "):
            if (money_word.startswith("o_") or money_word.startswith("i_")) and len(money_word) >= 3:
                # parse currency and value
                currency, value, direction = self.parse_moneyword(money_word)
                
                # add value to dictionaries
                if type(value) != type(u"todo"):
                    self.write_money_to_class_attributes(direction, currency, value)
                
                # build string to print entry
                if type(value) != type(u"todo"):
                    ret_str += "\n%s: %.2f%s" % (direction, value, currency)
                else:
                    ret_str += "\n%s: %s%s" % (direction, value, currency)
                
                # if next word will be first word then separator will be added
                first_word = True
            else:
                # it's normal (description) word not money entry (o_15.5€ for eg.)
                if first_word == True:
                    ret_str += " - " + money_word
                    first_word = False
                else:
                    ret_str += " " + money_word
        return ret_str[1:] # first char is whitespace
    
    def calculate_day_balance(self, currency):
        currency_balance = 0
        income = 0
        outcome = 0
        if self.day_income_total.has_key(currency):
            currency_balance += self.day_income_total[currency]
            income = self.day_income_total[currency]
        if self.day_outcome_total.has_key(currency):
            currency_balance -= self.day_outcome_total[currency]
            outcome = self.day_outcome_total[currency]
        return currency_balance, income, outcome
    
    def calculate_month_balance(self, currency):
        currency_balance = 0
        income = 0
        outcome = 0
        if self.month_income_total.has_key(currency):
            currency_balance += self.month_income_total[currency]
            income = self.month_income_total[currency]
        if self.month_outcome_total.has_key(currency):
            currency_balance -= self.month_outcome_total[currency]
            outcome = self.month_outcome_total[currency]
        return currency_balance, income, outcome
    
    def calculate_total_balance(self, currency):
        currency_balance = 0
        income = 0
        outcome = 0
        if self.income_total.has_key(currency):
            currency_balance += self.income_total[currency]
            income = self.income_total[currency]
        if self.outcome_total.has_key(currency):
            currency_balance -= self.outcome_total[currency]
            outcome = self.outcome_total[currency]
        return currency_balance, income, outcome
    
    def total_day_info(self):
        ret_str = ""
        currences = list(set(self.day_income_total.keys()+self.day_outcome_total.keys()))
        for currency in currences:
            currency_balance, income, outcome  = self.calculate_day_balance(currency)
            ret_str += "Total day balance %.2f %s | out %.2f %s | in %.2f %s\n" % (
                            currency_balance, currency, outcome, currency, income, currency)
        self.day_income_total = {}
        self.day_outcome_total = {}
        return ret_str
    
    def total_month_info(self):
        ret_str = ""
        currences = list(set(self.month_income_total.keys()+self.month_outcome_total.keys()))
        for currency in currences:
            currency_balance, income, outcome  = self.calculate_month_balance(currency)
            ret_str += "Total month balance %.2f %s | out %.2f %s | in %.2f %s\n" % (
                            currency_balance, currency, outcome, currency, income, currency)
        self.month_income_total = {}
        self.month_outcome_total = {}
        return ret_str
    
    def total_info(self):
        ret_str = ""
        currences = list(set(self.income_total.keys()+self.outcome_total.keys()))
        for currency in currences:
            currency_balance, income, outcome = self.calculate_total_balance(currency)
            ret_str += "Total balance %.2f %s | out %.2f %s | in %.2f %s\n" % (
                    currency_balance, currency, outcome, currency, income, currency)
        return ret_str
    
    def print_money_entries(self, all_times):
        ret_str = ""
        
        # previous day/month
        day=""
        month=""
        newday=""
        # go over time entries
        for time_entry in all_times:
            moneypart = time_entry["money_part"].decode("utf-8")
            # skip entries which hasn't money entry
            if moneypart == "": continue
            
            # use time stamp from start time of time entry
            time_dt = datetime.datetime.fromtimestamp(time_entry["start_sec"])
            
            # entries are sorted by time so if day changed print it
            if day != time_dt.strftime("%d"):
                # don't do that on first iteration
                if day != "":
                    ret_str += self.total_day_info()
                newday = "\nDay "+time_dt.strftime("%d.%m")+":\n"
                # update previous day variable
                day = time_dt.strftime("%d")
            
            if month != time_dt.strftime("%m"):
                if month != "":
                    # don't do that on first iteration
                    ret_str += self.total_month_info()
                # update previous month variable
                month = time_dt.strftime("%m")
            
            # print new day info after total month
            if newday != "":
                ret_str += newday
                newday = ""
            
            # nicely formated money -> description pairs 
            # also count money to class attributes
            ret_str += self.parse_moneywords(moneywords=moneypart)+"\n"
        
        # add total also at the end
        ret_str += self.total_day_info()
        ret_str += self.total_month_info()
        ret_str += self.total_info()
        
        return ret_str
    
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
    if len(sys.argv) == 4:
        return find_tags(sys.argv[1]),sys.argv[2],True
    elif len(sys.argv) == 3:
        return find_tags(sys.argv[1]),sys.argv[2],False
    else:
        print_usage("You must provide two or three arguments! Given %d"% (len(sys.argv)-1))
# provide list with records
if config.use_web==True:
    data = get_data(web_loc=config.web_location,username=base64.b64decode(config.username),password=base64.b64decode(config.password))
else:
    data = get_data(file_loc=config.file_location)

# get input (list of tags and string regex)
tags,regex,money = parse_input()

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

if money:
    # money part
    mp = MoneyParser()
    print mp.print_money_entries(all_times)


