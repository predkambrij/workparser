import sys, os, unittest
sys.path.insert(0, os.path.dirname(__file__)+"/..")
import parser

class TestRecord(unittest.TestCase):
    def setUp(self):
        pass
    def testParseRegexStartEndComment(self):
        tp = parser.TicketParser()

        cases = (
            ("6:03-7:09 bla bla", "6:03", "7:09", "bla bla"),
            ("6:03-17:09 bla bla", "6:03", "17:09", "bla bla"),
            ("6:03-:09 bla bla", "6:03", ":09", "bla bla"),
            ("6-7:09 bla bla", "6", "7:09", "bla bla"),
            ("6-:09 bla bla", "6", ":09", "bla bla"),
            ("6:03-7 bla bla", "6:03", "7", "bla bla"),
            ("6-7 bla bla", "6", "7", "bla bla"),
            ("-7:09 bla bla", "", "7:09", "bla bla"),
            ("-7 bla bla", "", "7", "bla bla"),
            ("-:09 bla bla", "", ":09", "bla bla"),
            ("6:03- bla bla", "6:03", "", "bla bla"),
            ("6- bla bla", "6", "", "bla bla"),
        )

        for (record, startC, endC, commentC) in cases:
            start, end, comment = tp.parse_regex_start_end_comment(record)
            self.assertEqual(start, startC)
            self.assertEqual(end, endC)
            self.assertEqual(comment, commentC)

    def testProcessStartEndComment(self):
        tp = parser.TicketParser()

        cases = (
            ("6:03", "7:09", "20.2", "2022",
                [],
             "6:03", "7:09", 66),
            ("6:03", "7", "20.2", "2022",
             [],
             "6:03", "7:00", 57),
            ("6", "7:09", "20.2", "2022",
             [],
             "6:00", "7:09", 69),

        )
        for (start, end, date, year, ndays,
                startC, endC, min_diffC) in cases:
            start, end, start_sec, end_sec = tp.process_start_end(start, end, date, year, ndays)
            self.assertEqual(start, startC)
            self.assertEqual(end, endC)
            self.assertEqual((end_sec-start_sec)/60, min_diffC)
            assert True
        assert True
