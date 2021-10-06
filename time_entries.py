# -*- coding:utf8 -*-

import argparse
import codecs
import xmlrpc.client
import datetime
import time
import re
import base64
import urllib.parse
import urllib.error
import urllib.request
import ticketparser.config
import os
import sys
sys.path.insert(
    0, "/home/loj/doing1/projs/ikservis/tachodownloader/repos/workparser")


# class FakeConfig:
#    fetch_from_web=False
#    file_location=os.path.dirname(__file__)+"/inp.dat"
#    pass
#
#mock.patch('ticketparser.config.Config', FakeConfig)


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
        if ticketparser.config.Config.fetch_from_web == False:
            return []
        server = xmlrpc.client.ServerProxy(ticketparser.config.Config.web_uri)
        ticket = server.ticket.get(ticketparser.config.Config.web_ticket_num)
        comments = server.ticket.changeLog(
            ticketparser.config.Config.web_ticket_num)
        comments1 = server.ticket.changeLog(
            ticketparser.config.Config.web_ticket_num1)

        description = ticket[3]["description"]
        comments_content = ""
        for comment in comments:
            if comment[2] == "comment":
                comments_content += comment[4] + "\n"

        comments_content1 = ""
        for comment in comments1:
            if comment[2] == "comment":
                comments_content1 += comment[4] + "\n"

        return (str(description + "\n" + comments_content + "\n" + comments_content1)).split("\n")

    def get_data_from_file(self):
        """
        get data from file_location specified in config.py (default data.dat)
        """
        try:
            lines = codecs.open(ticketparser.config.Config.file_location,
                                "rb", encoding="utf-8").read().split("\n")
            selected_lines = []
            for line in lines:
                if line.startswith("===end_of_time_entries==="):
                    break
                selected_lines.append(line)
            return selected_lines
        except IOError as e:
            print(e)

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
                except:
                    skipped_days.append(stripped_line)
            elif re.match("^[0-9]{1,2}:[0-9]{2}[ ]*-[ ]*=[ ]*.*$", stripped_line):
                # add new day entry (unfinished entry)
                try:
                    days[-1][2].append(stripped_line)
                except:
                    skipped_days.append(stripped_line)
            else:
                # unparsable line
                skipped_days.append(
                    days[-1][0]+"."+days[-1][1]+" :: "+stripped_line)
        return days, skipped_days

    def mock_date(self, date, year, start, end, ret=""):
        if int(time.mktime(time.strptime(start, "%H:%M"))) < int(time.mktime(time.strptime(end, "%H:%M"))):
            return date
        else:
            return (datetime.datetime.fromtimestamp(int(time.mktime(time.strptime(date+"."+year, "%d.%m.%Y"))))+datetime.timedelta(days=1)).strftime("%d.%m")

    def time_calculator(self, days):
        ndays = []
        for date, year, records in days:
            for record in records:
                start_end, comment = record.split("=", 1)
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
                comment, money_part, real_comment = comment.strip(
                ), money_part.strip(), real_comment.strip()

                start_sec = int(time.mktime(time.strptime(
                    date+"."+year+" "+start, "%d.%m.%Y %H:%M")))
                if str(end).strip() == "":
                    # unfinished entry
                    end_sec = start_sec+60
                else:
                    end_sec = int(time.mktime(time.strptime(self.mock_date(
                        date, year, start, end)+"."+year+" "+end, "%d.%m.%Y %H:%M")))

                str_diff = self.format_seconds(end_sec-start_sec)
                ndays.append({"year": year, "date": date, "start": start, "end": end,
                              "duration": (end_sec-start_sec), "str_diff": str_diff,
                              "comment": comment, "money_part": money_part, "real_comment": real_comment,
                              "start_sec": start_sec, "start_dt": datetime.datetime.fromtimestamp(start_sec)})
        return ndays

    def format_seconds(self, sec):
        if sec < 60:
            return str(sec)+" s"
        elif sec < 3600:
            return str(sec/60)+"m"
        elif sec < 86400:
            return str(sec/60/60)+"h " + str((sec/60) % 60)+"m"
        else:
            return str(sec/60/60/24)+"d "+str((sec/60/60) % 24)+"h " + str((sec/60) % 60)+"m"+"==" + str(sec/60/60)+"h " + str((sec/60) % 60)+"m"

    def find_tags(self, comment):
        return [x for x in comment.split() if re.match("^#[a-zA-Z]+$", x)]

    def selected_records(self, all_times, regex="", tags=[], full_regex=False):
        if full_regex == True:
            return [x for x in all_times if (regex == "" or re.match(regex, x["comment"])) and (tags == [] or all((y in self.find_tags(x["comment"])) for y in tags))]
        else:
            return [x for x in all_times if (regex == "" or re.match("^.*"+regex+".*$", x["comment"])) and (tags == [] or all((y in self.find_tags(x["comment"])) for y in tags))]

    def print_selected(self, records, overall_time=False):
        formated_records_list = [x["date"]+"."+x["year"]+"\t"+x["start"]+"-"+x["end"]+"\t"+x["str_diff"]+"\t"+(
            x["comment"] if type(x["comment"]) == type("") else x["comment"]) for x in records]

        formated_records = "\n".join(formated_records_list)
        all_time = sum(x["duration"] for x in records)
        return formated_records+"\nOverall: "+self.format_seconds(all_time)

    def export_to_excel_selected(self, records, overall_time=False, skip_tags=True):
        formated_records = "\n".join([x["date"].replace(",", ".")+"."+"\t"+x["start"]+"\t"+x["end"]+"\t"+x["str_diff"]+"\t"+" ".join(
            word for word in (x["comment"] if type(x["comment"]) == type("") else x["comment"]).split(" ") if not word.startswith("#")).strip() for x in records])
        # TODO codecs.open("out.xls","wb", encoding="utf-8").write(formated_records)
        return


class MoneyParser:
    def __init__(self):
        # group by day and month
        self.day_income_total = {}
        self.day_outcome_total = {}
        self.week_income_total = {}
        self.week_outcome_total = {}
        self.week_2l_income_total = {}
        self.week_2l_outcome_total = {}
        self.month_income_total = {}
        self.month_outcome_total = {}
        self.income_total = {}
        self.outcome_total = {}

        self.default_currency = "€"

        # for -l flag
        self.all_used_tags = set()

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
            if currency in self.day_outcome_total:
                self.day_outcome_total[currency] += value
            else:
                self.day_outcome_total[currency] = value

            # weekly
            if currency in self.week_outcome_total:
                self.week_outcome_total[currency] += value
            else:
                self.week_outcome_total[currency] = value

            # monthly
            if currency in self.month_outcome_total:
                self.month_outcome_total[currency] += value
            else:
                self.month_outcome_total[currency] = value

            # total
            if currency in self.outcome_total:
                self.outcome_total[currency] += value
            else:
                self.outcome_total[currency] = value
        elif direction == "in":
            # daily
            if currency in self.day_income_total:
                self.day_income_total[currency] += value
            else:
                self.day_income_total[currency] = value

            # weekly
            if currency in self.week_income_total:
                self.week_income_total[currency] += value
            else:
                self.week_income_total[currency] = value

            # monthly
            if currency in self.month_income_total:
                self.month_income_total[currency] += value
            else:
                self.month_income_total[currency] = value

            # total
            if currency in self.income_total:
                self.income_total[currency] += value
            else:
                self.income_total[currency] = value

    def split_moneywords(self, moneywords, str_time):
        """
        parse value and description from money section
        for eg. from this:
        !# o_3.25€ dancing o_3.2€ cocktail with strong alcohol
        to that:
        out 3.25€ - dancing
        out 3.2€ - cocktail with strong alcohol

        if moneywords string has money entries temp_entry get that shape
        {amount:{currency:cur, value:val, direction:dir}} # if money entry hasn't description or tags
        {amount:{currency:cur, value:val, direction:dir}, description:disc}  # if it has description
        {amount:{currency:cur, value:val, direction:dir}, tags:tags}  # if it has tags
        {amount:{currency:cur, value:val, direction:dir}, description:disc, tags:tags}  # if it has description and tags

        result is list of temp_entry dictionaries

        :parm moneywords: money section of time entry eg. o_3.25€ dancing o_3.2€ cocktail with strong alcohol
        :type moneywords: str
        :returns: list of fine structured dictionaries (from input parameter)
        """
        temp_list = []
        temp_entry = {}

        for money_word in moneywords.split(" "):
            if (money_word.startswith("o_") or money_word.startswith("i_")) and len(money_word) >= 3:
                if temp_entry != {}:
                    temp_list.append(temp_entry)
                    temp_entry = {}

                # parse currency and value
                currency, value, direction = self.parse_moneyword(money_word)

                temp_entry["amount"] = {
                    "currency": currency, "value": value, "direction": direction}
            else:
                # it's normal (description) word not money entry (o_15.5€ for eg.)
                if "amount" in temp_entry:  # if junk is present of just empty input
                    if "description" not in temp_entry:
                        temp_entry["description"] = money_word
                    else:
                        temp_entry["description"] += " " + money_word
                elif len(money_word) == 0:
                    pass  # it's ok, just empty string
                else:
                    raise ValueError(
                        "wrong formated money part: ["+str_time+"] "+money_word)

        # add last entry if needed
        if temp_entry != {}:
            temp_list.append(temp_entry)

        ret_list = []
        # move tags from description section to separated dictionary entry
        for time_entry in temp_list:
            if "description" not in time_entry:
                ret_list.append(time_entry)
                continue

            desc_words = []
            tags_words = []
            for desc_word in time_entry["description"].split():
                if desc_word.startswith("#"):
                    tags_words.append(desc_word)
                else:
                    desc_words.append(desc_word)
            time_entry["description"] = " ".join(desc_words)
            time_entry["tags"] = sorted(tags_words)

            ret_list.append(time_entry)
        return ret_list

    def parse_moneywords(self, struct):
        """
        write nicely formated temp_entry from self.split_moneywords()
        also count money to class attributes

        :parm struct: temp_entry dictionary from self.split_moneywords()
        ":returns: nicely formated string
        """

        ret_str = ""

        # rewrite for easier readability
        currency = struct["amount"]["currency"]
        value = struct["amount"]["value"]
        direction = struct["amount"]["direction"]

        # build string to print entry
        if type(value) != type("todo"):
            ret_str += "%s: %.2f%s" % (direction, value, currency)
            # add value to dictionaries
            self.write_money_to_class_attributes(direction, currency, value)
        else:
            ret_str += "%s: %s%s" % (direction, value, currency)

        ret_str += " - (" + \
            " ".join(struct["tags"]) + ") " + struct["description"]

        return ret_str

    def calculate_day_balance(self, currency):
        currency_balance = 0
        income = 0
        outcome = 0
        if currency in self.day_income_total:
            currency_balance += self.day_income_total[currency]
            income = self.day_income_total[currency]
        if currency in self.day_outcome_total:
            currency_balance -= self.day_outcome_total[currency]
            outcome = self.day_outcome_total[currency]
        return currency_balance, income, outcome

    def calculate_week_balance(self, currency):
        currency_balance = 0
        income = 0
        outcome = 0
        if currency in self.week_income_total:
            currency_balance += self.week_income_total[currency]
            income = self.week_income_total[currency]
        if currency in self.week_outcome_total:
            currency_balance -= self.week_outcome_total[currency]
            outcome = self.week_outcome_total[currency]
        return currency_balance, income, outcome

    def calculate_month_balance(self, currency):
        currency_balance = 0
        income = 0
        outcome = 0
        if currency in self.month_income_total:
            currency_balance += self.month_income_total[currency]
            income = self.month_income_total[currency]
        if currency in self.month_outcome_total:
            currency_balance -= self.month_outcome_total[currency]
            outcome = self.month_outcome_total[currency]
        return currency_balance, income, outcome

    def calculate_total_balance(self, currency):
        currency_balance = 0
        income = 0
        outcome = 0
        if currency in self.income_total:
            currency_balance += self.income_total[currency]
            income = self.income_total[currency]
        if currency in self.outcome_total:
            currency_balance -= self.outcome_total[currency]
            outcome = self.outcome_total[currency]
        return currency_balance, income, outcome

    def total_day_info(self):
        ret_str = ""
        r_balance = {}
        currences = list(set(list(self.day_income_total.keys()) +
                             list(self.day_outcome_total.keys())))
        for currency in currences:
            currency_balance, income, outcome = self.calculate_day_balance(
                currency)
            r_balance[currency] = tuple([currency_balance, income, outcome])
            ret_str += "Total day balance %.2f %s | out %.2f %s | in %.2f %s\n" % (
                currency_balance, currency, outcome, currency, income, currency)
        self.day_income_total = {}
        self.day_outcome_total = {}
        return r_balance, ret_str

    def total_week_info(self):
        ret_str = ""
        r_balance = {}
        currences = list(set(list(self.week_income_total.keys())
                             + list(self.week_outcome_total.keys())))
        for currency in currences:
            currency_balance, income, outcome = self.calculate_week_balance(
                currency)
            r_balance[currency] = tuple([currency_balance, income, outcome])
            ret_str += "Total week balance %.2f %s | out %.2f %s | in %.2f %s\n" % (
                currency_balance, currency, outcome, currency, income, currency)
        self.week_income_total = {}
        self.week_outcome_total = {}
        return r_balance, ret_str

    def total_week_info_excel(self):
        """
        same as total_week_info but output for excel and it doesn't reset self.week_(in/out)come_total
        """
        mandatory_excel_currencies = [
            "S", "\u20ac"]  # SEK and € (in that order)
        ret_str = ""
        currences = list(self.week_income_total.keys()) + \
            list(self.week_outcome_total.keys())

        # complement (currences minus mandatory_excel_currencies)
        compl = [x for x in currences if not x in mandatory_excel_currencies]

        all_currences = mandatory_excel_currencies+compl
        for currency in all_currences:
            currency_balance, income, outcome = self.calculate_week_balance(
                currency)
            if currency in currences:
                ret_str += "%.2f\t%.2f\t%.2f\t" % (
                    currency_balance, outcome, income)
            else:
                ret_str += "%.2f\t%.2f\t%.2f\t" % (0, 0, 0)

        return ret_str[:-1]

    def total_month_info(self):
        ret_str = ""
        r_balance = {}
        currences = list(set(list(self.month_income_total.keys()) +
                             list(self.month_outcome_total.keys())))
        for currency in currences:
            currency_balance, income, outcome = self.calculate_month_balance(
                currency)
            r_balance[currency] = tuple([currency_balance, income, outcome])
            ret_str += "Total month balance %.2f %s | out %.2f %s | in %.2f %s\n" % (
                currency_balance, currency, outcome, currency, income, currency)
        self.month_income_total = {}
        self.month_outcome_total = {}
        return r_balance, ret_str

    def total_info(self):
        ret_str = ""
        r_balance = {}
        currences = list(set(list(self.income_total.keys()) +
                             list(self.outcome_total.keys())))
        for currency in currences:
            currency_balance, income, outcome = self.calculate_total_balance(
                currency)
            r_balance[currency] = tuple([currency_balance, income, outcome])
            ret_str += "Total balance %.2f %s | out %.2f %s | in %.2f %s\n" % (
                currency_balance, currency, outcome, currency, income, currency)
        return r_balance, ret_str

    def write_to_class_for_total_balance(self, value, direction, currency):
        if value != "TODO":
            if direction == "out":
                if currency in self.outcome_total:
                    self.outcome_total[currency] += value
                else:
                    self.outcome_total[currency] = value
            elif direction == "in":
                if currency in self.income_total:
                    self.income_total[currency] += float(value)
                else:
                    self.income_total[currency] = float(value)

    def update_list_tags(self, tag_words):
        # add to list of all used tags (for -l flag)
        for tag in tag_words:
            self.all_used_tags.add(tag)

    def update_bytag(self, by_tag, moneypart, tag_words, time_dt):
        currency = moneypart["amount"]["currency"]
        value = moneypart["amount"]["value"]
        direction = moneypart["amount"]["direction"]
        for tag in tag_words:
            # make global (by_tag) dictionary instance if it's not already exists
            if tag not in by_tag:
                by_tag[tag] = {"in": {}, "out": {}}

            if currency not in by_tag[tag][direction]:
                by_tag[tag][direction][currency] = {"value": 0, "entries": []}

            by_tag[tag][direction][currency]["value"] += value

            # for time entry
            by_tag[tag][direction][currency]["entries"].append(
                {"desc": moneypart["description"], "amount": value, "tags": tag_words,
                 "time": time_dt.strftime("%d.%m")})

    def updateExcelInfo(self, excel_string, by_tag, firstDayOfPrevWeek, prevDayForWeek):
        twie = self.total_week_info_excel()

        tags_exc, o_redni_futr_razv, o, cms = self.calculate_tagsExc(by_tag)

        # headers for the first time
        if excel_string == "":
            excel_string += (
                "from\tto\tbal\tout\tin\tbal\tout\tin"
                + "\tallS\tallE\tfutr\trazv\to-r-f-r\tost\tcomm\n")

        excel_string += ("%s\t%s\t%s\t"
                         + "%s\t%.2f\t%.2f\t%s\n") % (
            firstDayOfPrevWeek.strftime("%d.%m"),
            prevDayForWeek.strftime("%d.%m"),
            twie,

            tags_exc,
            o_redni_futr_razv,
            o,
            cms[:-1],
        )
        return excel_string

    def calculate_tagsExc(self, by_tag):
        """
        TODO redni, etc beri s configa, da ne bo hardcodan
        """
        tags_exc = ""
        cms = ""  # comment string
        fs = 0
        rs = 0
        sums = 0  # sum SEK all tags together (verification)
        sume = 0  # sum € all tags together (verification)
        # ostalo-redni (S)
        o = 0
        # ostalo -redni-futr-razv
        o_redni_futr_razv = 0
        # get all currencies
        curs = set([])
        for tag in list(by_tag.keys()):
            curs |= set(by_tag[tag]["out"].keys())
        # go over currencies (sorted for comment)
        for cur in sorted(curs, key=lambda x: ["S", "\u20ac"].index(x)):
            # go over tags (k=tag)
            for k in sorted(list(by_tag.keys()),  # sort by value
                            key=lambda x: (
                "out" in by_tag[x] and
                cur in by_tag[x]["out"] and
                by_tag[x]["out"][cur]["value"]
            ), reverse=True):
                # just expenses
                if "out" in by_tag[k] and cur in by_tag[k]["out"]:
                    # comment (all tags), sort by currency
                    if by_tag[k]["out"][cur]["value"] > 0.00001:
                        if cur == "\u20ac":
                            cms += "%s:%.1f%s\t" % (k,
                                                    by_tag[k]["out"][cur]["value"], cur)
                        else:
                            cms += "%s:%.0f%s\t" % (k,
                                                    by_tag[k]["out"][cur]["value"], cur)
                    if cur == "\u20ac":  # reset € it's not processed further
                        sume += by_tag[k]["out"][cur]["value"]
                        by_tag[k]["out"][cur]["value"] = 0
                    # group SEK expenses by hashtags
                    if "S" in by_tag[k]["out"]:
                        # all tags together (verification)
                        sums += by_tag[k]["out"]["S"]["value"]
                        # by common tags
                        if k == "#redni":
                            # we don't add #redni and it's already noted in cms
                            by_tag[k]["out"]["S"]["value"] = 0
                            continue
                        # other (all-redni)
                        o += by_tag[k]["out"]["S"]["value"]
                        # futr column
                        if k == "#futr":
                            fs += by_tag["#futr"]["out"]["S"]["value"]
                            by_tag["#futr"]["out"]["S"]["value"] = 0
                        # razv column
                        if k == "#razv":
                            rs += by_tag["#razv"]["out"]["S"]["value"]
                            by_tag["#razv"]["out"]["S"]["value"] = 0
                        # other - redni - futr - razv
                        o_redni_futr_razv += by_tag[k]["out"]["S"]["value"]
                        # reset value for next week
                        by_tag[k]["out"]["S"]["value"] = 0
        tags_exc += "%.2f\t%.2f\t%.2f\t%.2f" % (sums, sume, fs, rs)
        return tags_exc, o_redni_futr_razv, o, cms

    def formatExcel(self, rows):
        r_str = ""
        return r_str

    def setDefaultsIfNeeded(self, moneypart):
        try:
            if len(moneypart["description"]) == 0:
                moneypart["description"] = "no description"
        except:
            moneypart["description"] = "no description"
        try:
            if len(moneypart["tags"]) == 0:
                moneypart["tags"] = ['#notag']
        except:
            moneypart["tags"] = ['#notag']

    def print_money_entries(self, all_times, money_tags, list_money_tags, show_by_tags):
        """
        :parm:all_times - output of time_calculator in relevant time interval
        Example:
        9:20-9:50 = comment of the task !# o_123S #moneyhashtag strong wiskey o_456S #anotherHT eggs
        [{'comment': u'comment of the task',
        'money_part': u'o_123S #moneyhashtag strong wiskey o_456S #anotherHT eggs',
        'start_sec': 1415089200, 'real_comment': '', 'duration': 1800, 'str_diff': '30m',
        'year': u'2014', 'date': u'4.11', 'end': u'9:50', 'start': u'9:20',
        'start_dt': datetime.datetime(2014, 11, 4, 9, 20)}, 
        ... ]
        :parm:money_tags -m flag (filter)
        :parm:list_money_tags -l flag
        :parm:show_by_tags -s flag
        look at parseArgsMoneyParser() for description
        """
        # result saving variables
        by_tag = {}
        r_list = {
            "total": {"balance": {}
                      },
            "months": {},
            "weeks": {},
            "days": {},
            "other": {}
        }

        # prepare for filtering
        if money_tags != "NoTags":
            money_tags_list = money_tags.split()
        else:
            money_tags_list = None

        # getting rid of
        ret_str = ""

        # previous day/week/month
        day = ""
        month = ""
        newday = ""
        prevDayForWeek = None
        firstDayOfPrevWeek = None

        # excel export
        excel_string = ""

        # go over time entries
        max_i = len(all_times)-1
        for time_entry in all_times:
            str_time = datetime.datetime.fromtimestamp(
                time_entry["start_sec"]).strftime("%d.%m")
            time_dt = datetime.datetime.fromtimestamp(time_entry["start_sec"])
            moneyparts = time_entry["money_part"]

            # go over moneyparts
            for moneypart in self.split_moneywords(moneyparts, str_time):
                # if description or tags aren't given - give them special name
                self.setDefaultsIfNeeded(moneypart)

                currency = moneypart["amount"]["currency"]
                value = moneypart["amount"]["value"]
                direction = moneypart["amount"]["direction"]

                # process the tags
                tag_words = moneypart["tags"]
                if len(tag_words) > 1:
                    print("more than one tag for the same transaction: " +
                          str_time+"||" + repr(moneypart))

                # for -l flag
                self.update_list_tags(tag_words)

                # filter: include just lines which has all required hastags (if flag isn't present ignore that condition)
                # so skip line if doesn't meet conditions (continoue)
                if money_tags_list == None or money_tags_list != []:
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

                if show_by_tags:
                    self.write_to_class_for_total_balance(
                        value, direction, currency)
                    self.update_bytag(by_tag, moneypart, tag_words, time_dt)
                else:
                    # entries are sorted by time so if day changes we will do a new entry
                    if day != time_dt.strftime("%d.%m.%Y"):
                        # make new entry for current day because of the moneyflow attribute
                        if time_dt.strftime("%d.%m.%Y") not in r_list["days"]:
                            r_list["days"][time_dt.strftime("%d.%m.%Y")] = {
                                "moneyflow": []}
                        # don't do that on the first iteration
                        if day != "":
                            # write total for previous day
                            ret_str = self.writeTotals(
                                ret_str, r_list, ["d"], day=day)

                        newday = "\nDay "+time_dt.strftime("%d.%m")+":\n"
                        # update previous day variable
                        day = time_dt.strftime("%d.%m.%Y")

                    # week entry
                    if prevDayForWeek == None:
                        prevDayForWeek = time_dt
                        firstDayOfPrevWeek = time_dt

                    # difference 7 days or it's surely new week

                    if ((time_dt - firstDayOfPrevWeek) > datetime.timedelta(days=7) or
                            (time_dt.weekday() < prevDayForWeek.weekday())):

                        excel_string = self.updateExcelInfo(excel_string, by_tag,
                                                            firstDayOfPrevWeek, prevDayForWeek)

                        # update week balance
                        ret_str = self.writeTotals(ret_str, r_list, ["w"],
                                                   ws=firstDayOfPrevWeek.strftime(
                                                       "%d.%m.%Y"),
                                                   we=prevDayForWeek.strftime("%d.%m.%Y"))

                        firstDayOfPrevWeek = time_dt

                    # update for tags shown in excel
                    self.update_bytag(by_tag, moneypart, tag_words, time_dt)

                    # keep track of last day for previous week
                    prevDayForWeek = time_dt

                    # month entry
                    if month != time_dt.strftime("%m.%Y"):
                        if month != "":
                            # don't do that on first iteration
                            ret_str = self.writeTotals(
                                ret_str, r_list, ["m"], month=month)

                        # update previous month variable
                        month = time_dt.strftime("%m.%Y")

                    # print new day info after total month
                    if newday != "":
                        ret_str += newday
                        newday = ""

                    # nicely formated money -> description pairs
                    # also count money to class attributes
                    moneyflow = self.parse_moneywords(moneypart)

                    r_list["days"][time_dt.strftime(
                        "%d.%m.%Y")]["moneyflow"].append(moneyflow)
                    ret_str += moneyflow + "\n"

        # at the end of for loops add remaining total values
        if show_by_tags:
            ret_by_tag = ""
            for tag in sorted(list(by_tag.keys()), key=lambda tag_x: sum([
                # directions TODO I think that I'm in mistake but it works for now
                sum([by_tag[tag_x][cur][dir]["value"]
                     for dir in list(by_tag[tag_x][cur].keys())])
                for cur in list(by_tag[tag_x].keys())]), reverse=True  # currencies
            ):
                ret_by_tag += "\ntag: %s\n" % tag
                for currency in sorted(list(set(list(by_tag[tag]["in"].keys())+list(by_tag[tag]["out"].keys())))):
                    if currency in by_tag[tag]["in"]:
                        # prepare entries for that tag
                        # TODO
                        ret_by_tag += "in: %d%s\n" % (
                            by_tag[tag]["in"][currency]["value"], currency)
                    if currency in by_tag[tag]["out"]:
                        # prepare entries for that tag
                        entries = sorted(
                            by_tag[tag]["out"][currency]["entries"], key=lambda entry: entry["amount"], reverse=True)
                        entries_str = "- " + "\n- ".join("["+entry["time"]+"] "+entry["desc"] +
                                                         " ("+"%.2f" % entry["amount"]+currency+")" for entry in entries) + "\n"

                        ret_by_tag += "out: %d%s\n" % (
                            by_tag[tag]["out"][currency]["value"], currency)+entries_str
            ret_str += ret_by_tag
            ret_str += self.total_info()
        else:
            excel_string = self.updateExcelInfo(excel_string, by_tag,
                                                firstDayOfPrevWeek, prevDayForWeek)

            codecs.open("week_export.tsv", "wb",
                        encoding="utf-8").write(excel_string)
            # add total also at the end
            ret_str = self.writeTotals(ret_str, r_list, ["d", "w", "m", "t"],
                                       ws=firstDayOfPrevWeek.strftime(
                                           "%d.%m.%Y"),
                                       we=prevDayForWeek.strftime("%d.%m.%Y"),
                                       day=day,
                                       month=time_dt.strftime("%m.%Y"))

        if list_money_tags:
            taglist = "\nUsed tags (%d): \"%s\"" % (
                len(self.all_used_tags),
                " ".join(sorted(list(self.all_used_tags))))
            ret_str += taglist
            r_list["other"]["taglist"] = taglist

        return r_list  # ret_str

    def writeTotals(self, ret_str, r_list, what, ws=None, we=None,
                    day=None, month=None):
        if "d" in what:
            r_balance, s_day = self.total_day_info()
            ret_str += s_day
            r_list["days"][day]["balance"] = r_balance
        if "w" in what:
            r_balance, s_week = self.total_week_info()
            ret_str += s_week
            r_list["weeks"][tuple([ws, we])] = {"balance": r_balance}
        if "m" in what:
            r_balance, s_month = self.total_month_info()
            ret_str += s_month
            r_list["months"][month] = {"balance": r_balance}
        if "t" in what:
            r_balance, r_str = self.total_info()
            ret_str += r_str
            r_list["total"]["balance"] = r_balance

        return ret_str

    def formatDicts(self, dicts, see):
        # example of structure for return which will be formated to string
        # r_list = {
        #          "total": {"balance":{}
        #          },
        #          "months":{
        #                    "12.2014":{"balance":{}
        #                               }
        #          },
        #          "weeks":{
        #                   ("12.2014", "19.2014"):{"balance":{
        #                                                      "€":(6.0,7.0,1.0),
        #                                                      "S":(6.0,7.0,1.0),
        #                                                      }
        #                                           }
        #          },
        #          "days":{
        #                  "1.12.2014":{"balance":{
        #                                          "€":("v_bal","v_out","v_in"),
        #                                          "S":("v_bal","v_out","v_in"),
        #                                          }
        #                               }
        #                  },
        #          }
        #    }
        # print repr(r_list)
        rstr = ""
        if "d" in see:
            rstr += "DAYS"
            days = [x for x in sorted(
                list(dicts["days"].keys()), key=lambda x:x.split(".")[::-1])]
            for day in days:
                if (len(list(dicts["days"][day]["balance"].keys())) == 0
                        and len(dicts["days"][day]["moneyflow"]) == 0):
                    continue

                rstr += "\nDay %s\n" % day[:-5]

                # moneyflow
                for mf in dicts["days"][day]["moneyflow"]:
                    rstr += mf+"\n"
                # day total
                rstr += self.printBalance(dicts["days"]
                                          [day]["balance"], header="day")

        if "w" in see:
            rstr += "\nWEEKS"
            weeks = [x for x in sorted(
                list(dicts["weeks"].keys()), key=lambda x:x[0].split(".")[::-1])]
            for week in weeks:
                rstr += "\nWeek %s-%s\n" % (week[0][:-5], week[1][:-5])
                # week total
                rstr += self.printBalance(dicts["weeks"]
                                          [week]["balance"], header="week")

        if "m" in see:
            rstr += "\nMONTHS"
            months = [x for x in sorted(
                list(dicts["months"].keys()), key=lambda x:x.split(".")[::-1])]
            for month in months:
                rstr += "\nMonth %s\n" % month[:-5]
                rstr += self.printBalance(dicts["months"]
                                          [month]["balance"], header="month")

        if "t" in see:
            rstr += "\nTOTAL\n"
            rstr += self.printBalance(dicts["total"]
                                      ["balance"], header="total")
            pass
        if "taglist" in see:
            rstr += "\nTag List"
            if "taglist" in dicts["other"]:  # TODO that doesn't crash huh...
                rstr += dicts["other"]["taglist"]

        return rstr[:]

    def printBalance(self, balance, header):
        rstr = ""
        # €, S, ..
        for cur in sorted(list(balance.keys()), key=lambda x: (x == "\u20ac" or x)):
            rstr += "Total %s balance %.2f %s | out %.2f %s | in %.2f %s\n" % (
                    header,
                    balance[cur][0], cur,
                    balance[cur][2], cur,
                    balance[cur][1], cur,
            )
        return rstr


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
            raise argparse.ArgumentTypeError(
                "%s is an invalid positive int value" % value)
        return

    def checkDateFormat(self, value):
        """Parse date from value"""
        day = value

        day_int = 0

        current_month_and_year = datetime.datetime.now().strftime("%m.%Y")
        try:
            day_int = int(time.mktime(time.strptime(
                day+"."+current_month_and_year, "%d.%m.%Y")))
        except:
            pass

        if day_int == 0:
            current_year = datetime.datetime.now().strftime("%Y")
            try:
                day_int = int(time.mktime(time.strptime(
                    day+"."+current_year, "%d.%m.%Y")))
            except:
                pass

        if day_int == 0:
            try:
                day_int = int(time.mktime(time.strptime(day, "%d.%m.%Y")))
            except:
                pass

        if day_int == 0:
            raise argparse.ArgumentTypeError(
                "%s uncorrect format. It must be in \"%%d.%%m.%%Y\" eg. 6.12.2013" % value)
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

        if args.command == "t":  # time entries
            self.parseArgsTimeEntriesResult(args)
            return "t"
        elif args.command == "m":  # money parser
            self.parseArgsMoneyParserResult(args)
            return "m"
        else:
            pass  # argparse will print help message
        return

    def parseArgsTimeEntries(self, subparsers):
        argparser = subparsers.add_parser('t', help="Time entries")

        argparser.add_argument('-d', '--day', nargs=1, type=self.checkDateFormat,
                               required=False, help="set starting day (default today) in format %%d.%%m.%%Y example:(25 or 25.12 or 25.12.2013)")
        argparser.add_argument('-n', '--number', nargs=1, type=self.checkNumberOfdays,
                               required=False, help="display number of days or months (default 1 day) backward starting day (--day flag)\n"
                               + "Example -n 5d (5 days backward starting day); -n 1m (from starting day backward to first in this month); -n 2m (from starting day backward to first in previous month)")
        argparser.add_argument('-f', '--filter', nargs=1, type=str,
                               required=False, help="regex filter (re.match) in description for time entry (including tags)")
        argparser.add_argument('-t', '--tags', nargs=1, type=str,
                               required=False, help="filter lines by tags (sparated with spaces)\n"
                               + "Example: \"#home #python #urllib\"")
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
                                 + "Example -n 5d (5 days backward starting day); -n 1m (from starting day backward to first in this month); -n 2m (from starting day backward to first in previous month)")
        moneyparser.add_argument('-f', '--filter', nargs=1, type=str,
                                 required=False, help="regex filter (re.match) in description for time entry (including tags)")
        moneyparser.add_argument('-t', '--tags', nargs=1, type=str,
                                 required=False, help="filter lines by tags (sparated with spaces)\n"
                                 + "Example: \"#home #python #urllib\"")
        moneyparser.add_argument('-m', '--money-tags', nargs=1, type=str,
                                 required=False, help="Show just lines which has all tags (separated with spaces). --money-tags=NoTags if you want to list entries without hashtag\n"
                                 + "Example: \"#food #fish\"")
        moneyparser.add_argument('-l', '--list-money-tags', action='store_true',
                                 required=False, help="List all used money hashtags at the end\n")
        moneyparser.add_argument('-s', '--show-by-tags', action='store_true',
                                 required=False, help="Show money flow by tags\n")

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
    data = []

    try:
        data = tp.get_data_from_web()
    except:
        print("NOT FETCHED FROM WEB BECAUSE NETWORK ISSUES")
    data += tp.get_data_from_file()

    # get input (list of tags and string regex)
    tags = tp.find_tags(args.tags[0])
    regex = args.filter[0]
    money = False

    # structured data
    time_pairs, skipped = tp.parser(data)
    if len("\n".join(skipped).strip()) != 0:
        raise ValueError("SKIPPED LINES: "+"\n".join(skipped))

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

            if args.starting_day + datetime.timedelta(days=args.number_of_days) < time_entry["start_dt"]:
                break

            selected_entries.append(time_entry)

    # select records which match all tags AND regex
    selected = tp.selected_records(
        selected_entries, regex=regex, tags=tags, full_regex=False)

    return selected, tp


def time_entries(args):
    selected, tp = common(args)
    # format for print and add overall spent time
    out = tp.print_selected(selected)

    tp.export_to_excel_selected(selected)
    print(out.encode('utf-8'))


def moneyparser(args):
    selected, tp = common(args)
    mp = MoneyParser()
    see = ["d", "w", "m", "t", "taglist"]
    r_list = mp.print_money_entries(
        selected, args.money_tags, args.list_money_tags, args.show_by_tags)
    if False == sys.stdout.isatty():  # pipe
        print(mp.formatDicts(r_list, see=see).encode('utf-8'))
    else:  # stdout
        print(mp.formatDicts(r_list, see=see))
    return


if __name__ == "__main__":

    args = ParseArguments()
    subparser = args.parseArguments()

    if subparser == "t":
        time_entries(args)
    elif subparser == "m":
        moneyparser(args)
        pass
    else:
        pass  # shouldn't happen that
