# -*- coding:utf8 -*-
from __future__ import with_statement

import unittest
import os, sys

import mock
from mock import MagicMock

# import for mocking
import ticketparser.config
import codecs
# functions
from ticketparser.time_entries import moneyparser, time_entries, common
# classes
from ticketparser.time_entries import ParseArguments, MoneyParser, TicketParser

# fake config
class FakeConfig:
    fetch_from_web=False
    file_location=os.path.dirname(__file__)+"/inp.dat"
    pass

# fake codecs.open (for mocking)
def codecsopen(filename, mode='rb', encoding=None, errors='strict', buffering=1):
        return CodecsOpen(filename, mode=mode, encoding=encoding, errors=errors, buffering=buffering)
class CodecsOpen:
    def __init__(self, filename, mode='rb', encoding=None, errors='strict', buffering=1):
        self.fn = filename
        self.m = mode
    def read(self):
        if self.fn == FakeConfig.file_location:
            return TestTEN.input_data
        raise ValueError("other file "+self.fn)
    def write(self, content):
        if self.fn == "week_export.xsl":
            print "week_export.xsl:"
            print content
        pass
    
# test class
class TestTEN(unittest.TestCase):
    # load data for testing
    input_data = codecs.open(FakeConfig.file_location,"rb", encoding="utf-8").read()
    argv = ['time_entries.py', 'm', '-l', '-d', '7.11', '-n', '700']
    def setUp(self):
        # mock arguments (sys.argv), file open and config (source for data)
        with (mock.patch('sys.argv', TestTEN.argv)
              ), mock.patch('codecs.open', codecsopen), mock.patch('ticketparser.config.Config', FakeConfig):
            
            self.args = ParseArguments()
            subparser = self.args.parseArguments()
            
            if subparser== "t":
                time_entries(self.args)
            elif subparser== "m":
                #moneyparser(args)
                
                self.selected, self.tp = common(self.args)
                self.mp = MoneyParser()
                pass
            else:
                pass # shouldn't happen that

    
    def test_general(self):
        with (mock.patch('sys.argv', TestTEN.argv)
              ), mock.patch('codecs.open', codecsopen), mock.patch('ticketparser.config.Config', FakeConfig):
            r = self.mp.print_money_entries(self.selected,
                self.args.money_tags, self.args.list_money_tags, self.args.show_by_tags)
            
            solutions={#balance, outcome, income
                       "07.11.2014":{u"S":[-235,235,0]},
                       
                       "10.11.2014":{u"S":[-16,16,0],
                                     u"\u20ac":[-4,4,0],#€
                                     },
                       "13.11.2014":{u"S":[-30,30,0]},
                       "14.11.2014":{u"S":[-10,10,0]},
                       "17.11.2014":{u"S":[-567,567,0]},
                       }
            
            # assert days
            #print repr(r["days"]["07.11.2014"]["balance"][u"S"])
            for k in solutions.keys():
                curs = solutions[k].keys()
                for c in curs:
                    cb = int(r["days"][k]["balance"][c][0])
                    co = int(r["days"][k]["balance"][c][2])
                    ci = int(r["days"][k]["balance"][c][1])
                    self.assertEquals(cb, solutions[k][c][0])
                    self.assertEquals(co, solutions[k][c][1])
                    self.assertEquals(ci, solutions[k][c][2])
            
            # assert weeks
            solutions_weeks={tuple(["07.11.2014","07.11.2014"]):{u"S":[-235,235,0]},
                             tuple(["10.11.2014","14.11.2014"]):{u"S":[-56,56,0],
                                                                 u"\u20ac":[-4,4,0],#€
                                                                 },
                             tuple(["17.11.2014","17.11.2014"]):{u"S":[-567,567,0]},
                             }
            for k in solutions_weeks.keys():
                curs = solutions_weeks[k].keys()
                for c in curs:
                    cb = int(r["weeks"][k]["balance"][c][0])
                    co = int(r["weeks"][k]["balance"][c][2])
                    ci = int(r["weeks"][k]["balance"][c][1])
                    self.assertEquals(cb, solutions_weeks[k][c][0])
                    self.assertEquals(co, solutions_weeks[k][c][1])
                    self.assertEquals(ci, solutions_weeks[k][c][2])
            
            
            print self.mp.formatDicts(r, see=["d","w","t", "taglist"])
        pass
