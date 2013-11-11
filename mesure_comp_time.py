import traceback

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
    def parser(self):
        
        print "run_slices"
        for runslice in self.run_slices:
            print str(runslice)
        
        print "stop_slices"
        for stopslice in self.stop_slices:
            print str(stopslice)
        
                
if __name__ == "__main__":
    f="/home/lojze/newhacks/time_tracking.log"
    p = Parser(f)
    lines = p.readFromFile()
    p.doPairs(lines)
    p.groupInSlices()
    p.parser()
    
    