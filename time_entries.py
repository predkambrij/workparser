# -*- coding:utf8 -*-
import config
import urllib2, base64, re, time, datetime, sys, xmlrpclib, codecs, argparse

class TicketParser:
    def get_data_from_web(self):
        """
        install plugin to trac installation (see http://trac-hacks.org/wiki/XmlRpcPlugin)
        ssh to server
        easy_install -Z -U http://trac-hacks.org/svn/xmlrpcplugin/trunk
        
        add this to trac.ini
            [components] 
            tracrpc.* = enabled 
        """
        server = xmlrpclib.ServerProxy(config.web_uri)
        ticket = server.ticket.get(config.web_ticket_num)
        comments = server.ticket.changeLog(config.web_ticket_num)
        
        description = ticket[3]["description"]
        comments_content = ""
        for comment in comments:
            if comment[2] == "comment":
                comments_content += comment[4] + "\n"
        
        return (description + "\n" + comments_content).split("\n")
        
    def get_data_from_file(self):
        """
        get data from file_location specified in config.py (default data.dat)
        """
        try:
            lines = file(config.file_location,"rb").read().split("\n")
            selected_lines = []
            for line in lines:
                if line.startswith("===end_of_time_entries==="):
                    break
                selected_lines.append(line)
            return selected_lines
        except IOError,e:
            print e
    
    def parser(self, data):
        """
        :parm data: list of records
        :type data: list
        """
        days = []
        skipped_days = []
        year = "1900"
    
        for line in data:
            stripped_line = line.strip()
    
            if stripped_line == "":
                # skip empty line
                continue
            
            if re.match("^year:[0-9]{4}$", stripped_line):
                year = stripped_line.split(":")[1]
            elif re.match("^[0-9]{1,2}.[0-9]{1,2}$", stripped_line):
                # add new day
                # append tuple as example ('30.10', '1900', [ ... day entries ... ])
                days.append(tuple([stripped_line, year, []]))
            elif re.match("^[0-9]{1,2}:[0-9]{2}[ ]*-[ ]*[0-9]{1,2}:[0-9]{2}[ ]*=[ ]*.*$", stripped_line):
                # add new day entry
                try:
                    days[-1][2].append(stripped_line)
                except: skipped_days.append(stripped_line) 
            else:
                # unparsable line
                skipped_days.append(stripped_line)
        return days,skipped_days
    
    def mock_date(self, date,year,start,end,ret=""):
        if int(time.mktime(time.strptime(start, "%H:%M"))) < int(time.mktime(time.strptime(end, "%H:%M"))):
            return date
        else:
            return (datetime.datetime.fromtimestamp(int(time.mktime(time.strptime(date+"."+year, "%d.%m.%Y"))))+datetime.timedelta(days=1)).strftime("%d.%m")
    
    def time_calculator(self, days):
        ndays = []
        for date, year, records in days:
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
                end_sec = int(time.mktime(time.strptime(self.mock_date(date,year,start,end)+"."+year+" "+end, "%d.%m.%Y %H:%M")))
    
                str_diff = self.format_seconds(end_sec-start_sec)
                ndays.append({"year":year,"date":date,"start":start,"end":end,
                    "duration":(end_sec-start_sec),"str_diff":str_diff,
                    "comment":comment, "money_part":money_part, "real_comment":real_comment,
                    "start_sec":start_sec, "start_dt":datetime.datetime.fromtimestamp(start_sec)})
        return ndays
    
    def format_seconds(self, sec):
        if sec < 60:
            return str(sec)+" s"
        elif sec < 3600:
            return str(sec/60)+"m"
        elif sec < 86400:
            return str(sec/60/60)+"h "+ str((sec/60)%60)+"m"
        else:
            return str(sec/60/60/24)+"d "+str((sec/60/60)%24)+"h "+ str((sec/60)%60)+"m"+"=="+ str(sec/60/60)+"h "+ str((sec/60)%60)+"m"
    
    def find_tags(self, comment):
        return [ x for x in comment.split() if re.match("^#[a-zA-Z]+$",x)]
    
    def selected_records(self, all_times, regex="" ,tags=[], full_regex=False):
        if full_regex == True:
            return [x for x in all_times if (regex=="" or re.match(regex,x["comment"])) and (tags==[] or all((y in self.find_tags(x["comment"])) for y in tags))]
        else:
            return [x for x in all_times if (regex=="" or re.match("^.*"+regex+".*$",x["comment"])) and (tags==[] or all((y in self.find_tags(x["comment"])) for y in tags))]
        
    
    def print_selected(self, records,overall_time=False):
        formated_records_list = [x["date"]+"."+x["year"]+"\t"+x["start"]+"-"+x["end"]+"\t"+x["str_diff"]+"\t"+(x["comment"] if type(x["comment"]) == type(u"") else x["comment"].decode("utf8")) for x in records]
                    
        formated_records = "\n".join(formated_records_list)
        all_time = sum(x["duration"] for x in records)
        return formated_records+"\nOverall: "+self.format_seconds(all_time)
    
    def export_to_excel_selected(self, records,overall_time=False, skip_tags=True):
        formated_records = "\n".join([x["date"].replace(",",".")+"."+"\t"+x["start"]+"\t"+x["end"]+"\t"+x["str_diff"]+"\t"+" ".join(
            word for word in (x["comment"] if type(x["comment"]) == type(u"") else x["comment"].decode("utf8")).split(" ") if not word.startswith("#")).strip() for x in records])
        #TODO codecs.open("out.xls","wb", encoding="utf-8").write(formated_records)
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
    
    def print_money_entries(self, all_times, money_tags, list_money_tags, show_by_tags):
        ret_str = ""
        if money_tags != "NoTags":
            money_tags_list = money_tags.split()
        else:
            money_tags_list = None
            
        all_used_tags = set()
        
        by_tag = {}
        
        # previous day/month
        day=""
        month=""
        newday=""
        
        # go over time entries
        for time_entry in all_times:
            moneypart = time_entry["money_part"].decode('utf-8')
            
            # include just lines which has all required hastags (if flag isn't present ignore that condition)
            if money_tags_list == None or money_tags_list != []:
                tag_words = [word for word in moneypart.split() if re.match("^#[a-zA-Z_]+$",word)]
                
                # if we want lines which doesn't have any tag
                if money_tags == "NoTags":
                    if len(tag_words) != 0:
                        continue
                else:
                    cont = False
                    for tag in money_tags_list:
                        if not tag in tag_words:
                            cont = True
                            break
                    if cont:
                        continue
                
                # add to list of all used tags
                for tag in tag_words:
                    all_used_tags.add(tag)
                
            if show_by_tags:
                tag_words = [word for word in moneypart.split() if re.match("^#[a-zA-Z_]+$",word)]
                for tag in tag_words:
                    if not by_tag.has_key(tag):
                        by_tag[tag] = {"in":{}, "out":{}}
                    
                    # find money part
                    for money_word in moneypart.split():
                        if (money_word.startswith("o_") or money_word.startswith("i_")) and len(money_word) >= 3:
                            # parse currency and value
                            currency, value, direction = self.parse_moneyword(money_word)
                            
                            if not by_tag[tag][direction].has_key(currency):
                                by_tag[tag][direction][currency] = 0
                            
                            by_tag[tag][direction][currency] += value
                
                pass
            else:
                
                # skip entries which hasn't money entry
                if moneypart == u"": continue
                
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
        
        if show_by_tags:
            ret_by_tag = ""
            for tag in sorted(by_tag.keys(), key=lambda tag_x:sum([ sum([ by_tag[tag_x][cur][dir] for dir in by_tag[tag_x][cur].keys()]) for cur in by_tag[tag_x].keys()]), reverse=True
                                                ):
                #print tag, sum([ sum([ by_tag[tag][cur][dir] for dir in by_tag[tag][cur].keys()]) for cur in by_tag[tag].keys()])
                ret_by_tag += "tag: %s\n" % tag
                for currency in sorted(list(set(by_tag[tag]["in"].keys()+by_tag[tag]["out"].keys()))):
                    if by_tag[tag]["in"].has_key(currency):
                       ret_by_tag += "in: %d%s\n" % (by_tag[tag]["in"][currency], currency)
                    if by_tag[tag]["out"].has_key(currency):
                       ret_by_tag += "out: %d%s\n" % (by_tag[tag]["out"][currency], currency)
            ret_str += ret_by_tag
        else:
            # add total also at the end
            ret_str += self.total_day_info()
            ret_str += self.total_month_info()
            ret_str += self.total_info()
        
        if list_money_tags:
            ret_str += "\nUsed tags (%d): \"%s\"" % (
                len(all_used_tags),
                " ".join(sorted(list(all_used_tags))))
        return ret_str

class ParseArguments:
    def checkNumberOfdays(self, value):
        """It have to be positive number"""
        show_type_error = False
        try:
            intvalue = int(value)
            if intvalue > 0:
                return intvalue
            else:
                show_type_error = True
        except:
            show_type_error = True
            
        if show_type_error == True:
            raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
        return
    
    def checkDateFormat(self, value):
        """Parse date from value"""
        day = value
        
        day_int = 0
        
        current_month_and_year = datetime.datetime.now().strftime("%m.%Y")
        try: day_int = int(time.mktime(time.strptime(day+"."+current_month_and_year, "%d.%m.%Y")))
        except: pass
        
        if day_int == 0:
            current_year = datetime.datetime.now().strftime("%Y")
            try: day_int = int(time.mktime(time.strptime(day+"."+current_year, "%d.%m.%Y")))
            except: pass
        
        if day_int == 0:
            try: day_int = int(time.mktime(time.strptime(day, "%d.%m.%Y")))
            except: pass
        
        if day_int == 0:
            raise argparse.ArgumentTypeError("%s uncorrect format. It must be in \"%%d.%%m.%%Y\" eg. 6.12.2013" % value)
        else:
            # create and return datetime object from absolute time
            return datetime.datetime.fromtimestamp(day_int)
    
    def parseArguments(self):
        """
        Parse arguments
        """
        
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest='command')
        
        self.parseArgsTimeEntries(subparsers)
        self.parseArgsMoneyParser(subparsers)
        
        args = parser.parse_args()
        
        if args.command == "t": # time entries
            self.parseArgsTimeEntriesResult(args)
            return "t"
        elif args.command == "m": # money parser
            self.parseArgsMoneyParserResult(args)
            return "m"
        else:
            pass #argparse will print help message
        return
    def parseArgsTimeEntries(self, subparsers):
        argparser = subparsers.add_parser('t', help="Time entries")
        
        argparser.add_argument('-d', '--day', nargs=1, type=self.checkDateFormat,
            required=False, help="set starting day (default today) in format %%d.%%m.%%Y example:(25 or 25.12 or 25.12.2013)")
        argparser.add_argument('-n', '--number', nargs=1, type=self.checkNumberOfdays,
            required=False, help="display number of days or months (default 1 day) backward starting day (--day flag)\n"
                                +"Example -n 5d (5 days backward starting day); -n 1m (from starting day backward to first in this month); -n 2m (from starting day backward to first in previous month)")
        argparser.add_argument('-f', '--filter', nargs=1, type=str,
            required=False, help="regex filter (re.match) in description for time entry (including tags)")
        argparser.add_argument('-t', '--tags', nargs=1, type=str,
            required=False, help="filter lines by tags (sparated with spaces)\n"
                                +"Example: \"#home #python #urllib\"")
        return
    def parseArgsTimeEntriesResult(self, args):
        # use today if not set
        if args.day == None:
            # convert current timestamp to string and back to datetime (that only year, month and day will remain)
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            today_int = int(time.mktime(time.strptime(today_str, "%Y-%m-%d")))
            self.starting_day = datetime.datetime.fromtimestamp(today_int)
        else:
            self.starting_day = args.day[0]
        
        # number of days to show after starting date (use as default 1 day)
        if args.number == None:
            self.number_of_days = 1
        else:
            self.number_of_days = args.number[0]
        
        if args.filter == None:
            self.filter = [""]
        else:
            self.filter = args.filter
        
        if args.tags == None:
            self.tags = [""]
        else:
            self.tags = args.tags
        return
        
    def parseArgsMoneyParser(self, subparsers):
        moneyparser = subparsers.add_parser('m', help="Money parser")
        moneyparser.add_argument('-d', '--day', nargs=1, type=self.checkDateFormat,
            required=False, help="set starting day (default today) in format %%d.%%m.%%Y example:(25 or 25.12 or 25.12.2013)")
        moneyparser.add_argument('-n', '--number', nargs=1, type=self.checkNumberOfdays,
            required=False, help="display number of days or months (default 1 day) backward starting day (--day flag)\n"
                                +"Example -n 5d (5 days backward starting day); -n 1m (from starting day backward to first in this month); -n 2m (from starting day backward to first in previous month)")
        moneyparser.add_argument('-f', '--filter', nargs=1, type=str,
            required=False, help="regex filter (re.match) in description for time entry (including tags)")
        moneyparser.add_argument('-t', '--tags', nargs=1, type=str,
            required=False, help="filter lines by tags (sparated with spaces)\n"
                                +"Example: \"#home #python #urllib\"")
        moneyparser.add_argument('-m', '--money-tags', nargs=1, type=str,
            required=False, help="Show just lines which has all tags (separated with spaces). --money-tags=NoTags if you want to list entries without hashtag\n"
                                +"Example: \"#food #fish\"")
        moneyparser.add_argument('-l', '--list-money-tags', action='store_true', required=False, help="List all used money hashtags at the end\n")
        moneyparser.add_argument('-s', '--show-by-tags', action='store_true', required=False, help="Show money flow by tags\n")
        
        return
    def parseArgsMoneyParserResult(self, args):
        # use today if not set
        if args.day == None:
            # convert current timestamp to string and back to datetime (that only year, month and day will remain)
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            today_int = int(time.mktime(time.strptime(today_str, "%Y-%m-%d")))
            self.starting_day = datetime.datetime.fromtimestamp(today_int)
        else:
            self.starting_day = args.day[0]
        
        # number of days to show after starting date (use as default 1 day)
        if args.number == None:
            self.number_of_days = 1
        else:
            self.number_of_days = args.number[0]
        
        if args.filter == None:
            self.filter = [""]
        else:
            self.filter = args.filter
        
        if args.tags == None:
            self.tags = [""]
        else:
            self.tags = args.tags
        
        if args.money_tags == None:
            self.money_tags = ""
        else:
            self.money_tags = args.money_tags[0]
        
        if args.list_money_tags == False:
            self.list_money_tags = False
        else:
            self.list_money_tags = True
        
        if args.show_by_tags == False:
            self.show_by_tags = False
        else:
            self.show_by_tags = True
        
        return

def common(args):
        # time entries
        tp = TicketParser()
        # provide list with records
        
        
        # TODO - fetch if needed
        data = tp.get_data_from_web()
        data += tp.get_data_from_file()
        
        # get input (list of tags and string regex)
        tags = tp.find_tags(args.tags[0])
        regex = args.filter[0]
        money = False
        
        # structured data
        time_pairs,skipped = tp.parser(data)
        
        # even more structured data
        all_times = tp.time_calculator(time_pairs)
        
        # select by first date and limit at args.number_of_days TODO months aren't implemented yet
        num_of_days = 0
        current_day = None
        selected_entries = []
        for time_entry in all_times:
            # add entry if it's in correct date range
            if time_entry["start_dt"] >= args.starting_day:
                # first loop
                if current_day == None:
                    current_day = time_entry["start_dt"].strftime("%d.%m.%Y")
                
                # if day changed - count number of added days
                if current_day != time_entry["start_dt"].strftime("%d.%m.%Y"):
                    current_day = time_entry["start_dt"].strftime("%d.%m.%Y")
                    num_of_days += 1
                
                # number of days limit
                if args.number_of_days == num_of_days:
                    break
                
                selected_entries.append(time_entry)
        
        # select records which match all tags AND regex
        selected = tp.selected_records(selected_entries,regex=regex,tags=tags, full_regex=False)
        return selected
    
def time_entries(args):
        selected = common(args)
        # format for print and add overall spent time
        out = tp.print_selected(selected)
        
        tp.export_to_excel_selected(selected)
        print out

def moneyparser(args):
        selected = common(args)
        mp = MoneyParser()
        print mp.print_money_entries(selected, args.money_tags, args.list_money_tags, args.show_by_tags)
        return

if __name__ == "__main__":
    
    args = ParseArguments()
    subparser = args.parseArguments()
    
    if subparser== "t":
        time_entries(args)
    elif subparser== "m":
        moneyparser(args)
        pass
    else:
        pass # shouldn't happen that

