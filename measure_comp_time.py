# -*- coding:utf8 -*-
import config
import traceback, time, datetime, argparse

class Parser:
    def __init__(self, filename):
        self.filename = filename
        self.stop_words = ["LOCKED", "PRESUSPEND"]
        self.cont_words = ["POSTSUSPEND", "UNLOCKED"]
        self.slices = []
        self.run_slices = []
        self.stop_slices = []
        
    def readFromFile(self):
        lines = file(self.filename, "rb").read()
        return lines
    def doPairs(self, lines):
        for line in lines.split("\n"):
            if line == "":
                continue
            
            line_words = line.split(" ")
            is_stop = False
            is_cont = False
            
            # is that line stoping or continouing time measure?
            for stopword in self.stop_words:
                for line_word in line_words:
                    if line_word == stopword:
                        is_stop = True
                        break
                if is_stop == True:
                    break
            for contword in self.cont_words:
                for line_word in line_words:
                    if line_word == contword:
                        is_cont = True
                        break
                if is_cont == True:
                    break
            
            if is_stop == True and is_cont == True:
                print "Line "+line+" has stopping and continouing word included. Check that line is really parsable."
                print "".join(traceback.format_stack())
                return
            if is_stop == False and is_cont == False:
                print "Line "+line+" doesn't include stopping or continouing word. Check that line is really parsable."
                print "".join(traceback.format_stack())
                return
            
            if is_stop == True:
                self.slices.append(["stop", line])
            elif is_cont == True:
                self.slices.append(["cont", line])
            else:
                print "Internal error. Line should be stopping or continouing."
                print "Line: " + line
                print "".join(traceback.format_stack())
                return
        return True
    def calculate_duration(self, sec):
        if sec < 60:
            return str(sec)+" s"
        elif sec < 3600:
            return str(sec/60)+"m"
        elif sec < 86400:
            return str(sec/60/60)+"h "+ str((sec/60)%60)+"m"
        else:
            return str(sec/60/60/24)+"d "+str((sec/60/60)%24)+"h "+ str((sec/60)%60)+"m"+"=="+ str(sec/60/60)+"h "+ str((sec/60)%60)+"m"

    def groupInSlices(self):
        run_slice = None
        stop_slice = None
        run = False
        for slice in self.slices:
            if run == False and slice[0] == "stop" and stop_slice != None:
                continue
            if run == True and slice[0] == "cont" and run_slice != None:
                continue
            
            if run == False and slice[0] == "stop":
                stop_slice = slice[1].split(" ")[0]
            if run == True and slice[0] == "cont":
                run_slice = slice[1].split(" ")[0]
            
            if run == False and slice[0] == "cont":
                run_slice = slice[1].split(" ")[0]
                self.stop_slices.append([stop_slice, slice[1].split(" ")[0]])
                stop_slice = None
            if run == True and slice[0] == "stop":
                self.run_slices.append([run_slice, slice[1].split(" ")[0]])
                stop_slice = slice[1].split(" ")[0]
                run_slice = None
            if slice[0] == "cont":
                run = True
            else:
                run = False
        if run_slice != None:
            self.run_slices.append([run_slice, "still"])
        if stop_slice != None:
            self.stop_slices.append([stop_slice, "still"])
        return True
    
    def calculate_slices(self, slices):
        """
        structure slices:
        
        :parm slices list of pairs (start, stop)
        """
        
        #list of day_structure dictionaries
        days = []
        
        # total time (from all slices together - one day)
        run_total = 0
        
        # mark current day
        day = ""
        
        # group slices by day
        for currentslice in slices:
            #FIXME: 
            if currentslice[0]== None: continue
            
            # parse absolute time from epoch to integer
            start_int = int(time.mktime(time.strptime(currentslice[0], "%Y-%m-%d-%H-%M-%S"))) # eg. "2013-11-11-21-57-04"
            
            # parse absolute time from epoch to integer or take current time if slice isn't completed (still)
            if currentslice[1] == "still":
                end_int = int(round(time.time()))
            else:
                end_int = int(time.mktime(time.strptime(currentslice[1], "%Y-%m-%d-%H-%M-%S")))
            
            # create datetime object from absolute time
            start = datetime.datetime.fromtimestamp(start_int)
            end = datetime.datetime.fromtimestamp(end_int)
            
            # calculate duration
            dur_int = end_int-start_int
            
            # capture date if needed
            if day != start.strftime("%d.%m"):
                # don't mark this at first iteration
                if day != "":
                    # total time
                    days[-1]["total"] = run_total
                    run_total = 0
                
                # structure of daily format
                #    day:datetime -> first slice (from which day, month and year will be used)
                #    slices: list of dictionaries (start, end, duration) in datetime format (duration in seconds)
                #    total: int in seconds total time (all slices)
                day_structure = {"day":None, "slices":[], "total":0}
                
                # new day entry
                days.append(day_structure)
                
                # mark datetime of first entry (just day, month and year will be used)
                day_str = start.strftime("%Y-%m-%d")
                day_int = int(time.mktime(time.strptime(day_str, "%Y-%m-%d")))
                days[-1]["day"] = datetime.datetime.fromtimestamp(day_int)
                
                # mark new day
                day = start.strftime("%d.%m")
            
            # add time row
            days[-1]["slices"].append({"start":start, "end":end, "duration":dur_int})
            
            # add duration to total duration variable
            run_total += (end_int-start_int)
            #print start.strftime("%d.%m.%H-%M-%S") + " " + end.strftime("%d.%m.%H-%M-%S") + " total:"+str(run_total)+ "\n"
            
        # total time of remaining date
        days[-1]["total"] = run_total
        
        return days
    
    def select_days_by_arguments(self, all_days):
        """
        Select days by self.starting_day and self.number_of_days
        """
        # copy needed day_structure dictionaries from all_days (self.starting_day and self.number_of_days)
        affected_days = []
        
        # flag
        adding = False
        
        # number of added days
        added = 0
        # choose needed days (self.starting_day and self.number_of_days)
        for day in all_days:
            if adding == False:
                if day["day"] == self.starting_day:
                    adding = True
            
            if adding == True:
                affected_days.append(day)
                added += 1
                if added == self.number_of_days:
                    break
        if added == False:
            raise Exception("Date %s didn't met\n" % self.starting_day.strftime("%d.%m.%Y"))
            
        return affected_days
        
    def format_slices(self, slices, slices_title = ""):
        """
        Build nicely formated string which will be output of that script
        """
        
        # structure time slices by days and calculate duration of each slice and all slices in day
        all_days =  self.calculate_slices(slices)
        
        # select needed days by self.starting_day and self.number_of_days
        affected_days = self.select_days_by_arguments(all_days)
        
        # final string
        ret_str = ""
        
        # title
        ret_str += slices_title+"\n"
        
        for day in affected_days:
            ret_str += "\nDay: " +day["day"].strftime("%d.%m") + "\n"
            
            if self.verbose == True:
                for slice in day["slices"]:
                    ret_str += (slice["start"].strftime("%H:%M")
                        + " - " + slice["end"].strftime("%H:%M")
                        + "  "+"("+self.calculate_duration(slice["duration"])+")"+"\n")
                
            ret_str += "Total: " + self.calculate_duration(day["total"]) + "\n"
        
        return ret_str
    
    def parser(self):
        if self.show_stop_entries == False:
            return self.format_slices(self.run_slices, slices_title="run_slices")
        else:
            return self.format_slices(self.stop_slices, slices_title="stop_slices")
        
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
    
    def argparser(self):
        """Parse values from args or use defaults"""
        argparser = argparse.ArgumentParser()
        argparser.add_argument('-v', '--verbose-entries', action='store_true', required=False, help="display time sections")
        argparser.add_argument('-d', '--day', nargs=1, type=self.checkDateFormat, required=False, help="set starting day (default today) in format %%d.%%m.%%Y example:(25 or 25.12 or 25.12.2013)")
        argparser.add_argument('-n', '--number', nargs=1, type=self.checkNumberOfdays,  required=False, help="display number of days (default 1) after starting day (default today, you can customize it with --day flag)")
        argparser.add_argument('-s', '--stop-entries', action='store_true', required=False, help="displays stop sections instead running time sections")
        # TODO min time resolution
        # list all days, first date, last date from records
        
        args = argparser.parse_args()
        
        # show slices or not
        self.verbose = args.verbose_entries
        
        #show stop entries instead running entries
        self.show_stop_entries = args.stop_entries
        
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
        
        #print "verbose: ", self.verbose
        #print "day: ", self.starting_day
        #print "num: ", self.number_of_days
        #print "stop_entries: ", self.show_stop_entries
        
        return
    
    
    
if __name__ == "__main__":
    
    
    
    p = Parser(filename=config.time_tracking_log)
    
    # parse settings from arguments or use defaults
    p.argparser()
    
      
    lines = p.readFromFile()
    p.doPairs(lines)
    p.groupInSlices()
    print p.parser()
#     
    
