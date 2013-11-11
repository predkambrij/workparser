import traceback
import time, datetime

class Parser:
    def __init__(self, filename):
        self.filename = filename
        self.stop_words = ["LOCKED", "PRESUSPEND"]
        self.cont_words = ["POSTSUSPEND", "UNLOCKED"]
        self.slices = []
        self.run_slices = []
        self.stop_slices = []
        
    def readFromFile(self):
        lines = file(f, "rb").read()
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
    def format_slices(self, slices, slices_title = ""):
        ret_str = ""
        
        # title
        ret_str += slices_title+"\n"
        
        # total time (from all slices together)
        run_total = 0
        day = ""
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
            
            # format time for printing
            start_str = start.strftime("%H:%M")
            end_str = end.strftime("%H:%M")
            
            # calculate duration
            dur_str = self.calculate_duration(end_int-start_int)
            
            # add duration to total duration variable
            run_total += (end_int-start_int)
            
            # print date if needed
            if day != start.strftime("%d.%m"):
                # don't print this at first iteration
                if day != "":
                    # total time
                    ret_str += "Total: " + self.calculate_duration(run_total) + "\n"
                    run_total = 0
                
                ret_str += "\nDay: " +start.strftime("%d.%m") + "\n"
                day = start.strftime("%d.%m")
            
            # print time row
            ret_str += start_str + " " +end_str+ "  "+"("+dur_str+")"+"\n"
        
        # total time of remaining date
        ret_str += "Total: " + self.calculate_duration(run_total) + "\n"
                
        
        
        return ret_str
    def parser(self):
        print self.format_slices(self.run_slices, slices_title="run_slices")
        print self.format_slices(self.stop_slices, slices_title="stop_slices")
        
        print "stopslice"
        for stopslice in self.stop_slices:
            print str(stopslice)
        print "runslice"
        for runslice in self.run_slices:
            print str(runslice)
        
                
if __name__ == "__main__":
    f="/home/lojze/newhacks/time_tracking.log"
    p = Parser(f)
    lines = p.readFromFile()
    p.doPairs(lines)
    p.groupInSlices()
    p.parser()
    
    