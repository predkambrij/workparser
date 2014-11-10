import sys, datetime, os
import measure_comp_time, config
# dej nekak dodaj se uravnotezene procente (v katerem delu tega urnega intervala so pavze)

class PanelFormat:
    def __init__(self):
        self.verbose = 0
        if len(sys.argv) > 1:
            self.verbose = 1
        # monitor last X time - currently last hour
        self.now = datetime.datetime.now()
        self.timeDelta = datetime.timedelta(hours = 1, minutes=0)
        self.check_point = self.now-self.timeDelta#+datetime.timedelta(seconds=1)
        self.check_point = self.check_point.replace(microsecond=0)
        pass
    def in_working(self):
        """
        Find if delta time (check_point) is in running slice or stop_slice
        (later will be splitted)
        """
        for running_slice in self.slices:
            if running_slice["start"] <= self.check_point <= running_slice["end"]:
                return True
        for stop_slice in self.s_slices:
            if stop_slice["start"] <= self.check_point <= stop_slice["end"]:
                return False
        if datetime.datetime.now().weekday() == 0:
            return None
        raise ValueError("time should be between running or stop slice")
        return

    def split_working(self):
        """
        split slice which contains delta time (check_point)
        """
        flag=False
        self.new_running = []
        for running_slice in self.slices:
            if running_slice["start"] <= self.check_point <= running_slice["end"]:
                self.new_running.append({"start":self.check_point, "end":running_slice["end"],
                    "duration":int((running_slice["end"]-self.check_point).total_seconds())})
                flag=True
                continue
            if flag:
                self.new_running.append(running_slice)
        return
    def split_stop(self):
        """
        split slice which contains delta time (check_point)
        """
        flag=False
        self.new_stop = []
        for stop_slice in self.s_slices:
            if stop_slice["start"] <= self.check_point <= stop_slice["end"]:
                self.new_stop.append({"start":self.check_point, "end":stop_slice["end"],
                   "duration":(stop_slice["end"]-self.check_point).total_seconds()})
                flag=True
                continue
            if flag:
                self.new_stop.append(stop_slice)
        return
    def sum_running_slices(self):
        """
        sum slices starting from delta time
        """
        flag=False
        summa = 0
        if self.verbose >= 1:
            print "sum_running_slices"
        for running_slice in self.new_running:
            if self.check_point <= running_slice["start"]:
                summa += running_slice["duration"]
                if self.verbose >= 1:
                    print running_slice["duration"],running_slice["start"],running_slice["end"]
        return summa/60.
    def sum_stop_slices(self):
        """
        sum slices starting from delta time
        """
        flag=False
        summa = 0
        if self.verbose >= 1:
            print "sum_stop_slices"
        for stop_slice in self.new_stop:
            if self.check_point <= stop_slice["start"]:
                summa += stop_slice["duration"]
                if self.verbose >= 1:
                    print stop_slice["duration"],stop_slice["start"],stop_slice["end"]
        return summa/60.
    def process(self):
        """
        Basic operations (calling text processor and methods for processing data)
        """
        # process text file
        p = measure_comp_time.Parser(filename=config.time_tracking_log)

        # settings from arguments for panel format
        cur_argv = sys.argv[:] # save current arguments (deep copy)
        sys.argv = ['measure_comp_time.py', '-p']
        p.argparser()
        sys.argv = cur_argv

        # measure_comp_time operations in __main__
        lines = p.readFromFile()
        p.doPairs(lines)
        p.groupInSlices()
        day_result = p.parser()

        # copy data for processing
        self.day_total = day_result["total_today"]
        self.day_total_b = day_result["total_today_break"]
        self.total = day_result["total"]
        self.total_b = day_result["total_break"]
        self.total_w = day_result["total_w"]
        self.total_b_w = day_result["total_break_w"]

        # for notifacion when to take a rest
        self.slices=day_result["slices"]
        self.s_slices=day_result["s_slices"]

        # select slices corresponding the self.timeDelta
        in_working = self.in_working()
        if in_working == True:
            self.split_working()
            self.new_stop = self.s_slices
        elif in_working == False:
            self.split_stop()
            self.new_running = self.slices
        else: # monday 0:00-1:00
            self.new_stop = self.s_slices
            self.new_running = self.slices
        
    def format(self):
        """
        Format data for xfce panel Generic Monitor
        """
        # break in last self.timeDelta
        break_duration = self.sum_stop_slices()
        padding=""
        if break_duration <= 1:
            color="bgcolor='red'"
            padding="  "
        elif break_duration <= 15:
            color="bgcolor='orange'"
            padding=" "
        else:
            color=""
        sum_break_duration="<span %s>%s%.0f%s</span>" % (color, padding, break_duration, padding)

        # running in last self.timeDelta
        sum_running_duration = "%.0f" % (self.sum_running_slices())
        is_it_working = "%s" % datetime.datetime.now().strftime("%H:%M")
        # format everything together (for Generic Monitor)
        return ("<txt>%.1f_%.1f hours (%s-%s m) %s LOG?</txt>"
                +"<tool>%.1f_%.1f week hours // %.1f_%.1f mon-fri hours</tool>") % (
                            self.day_total,self.day_total_b, sum_running_duration,sum_break_duration,
                            is_it_working,
                            self.total, self.total_b,self.total_w, self.total_b_w)
if __name__ == "__main__":
    P = PanelFormat()
    P.process()
    print P.format()

