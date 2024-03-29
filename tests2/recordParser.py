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
            ("6:03", "7:09", "20.2", "2022", ([], "6:03", "7:09", 66)),     # test regular interval
            ("23:53", "1:10", "20.2", "2022", ([], "23:53", "1:10", 77)),   # test over midnight
            ("6:03", "7", "20.2", "2022", ([], "6:03", "7:00", 57)),        # test whole numbers
            ("6", "7:09", "20.2", "2022", ([], "6:00", "7:09", 69)),        # test whole numbers
            ("", "7:09", "20.2", "2022", ([{"end":"6:55"}], "6:55", "7:09", 14)),   # test omitted start

            ("6:05", ":19", "20.2", "2022", ([], "6:05", "6:19", 14)),          # test omitted hour for end
            ("", ":19", "20.2", "2022", ([{"end":"6:05"}], "6:05", "6:19", 14)),  # test omitted hour for end

        )
        for (start, end, date, year, (ndays,
                startC, endC, min_diffC)) in cases:
            start, end, start_sec, end_sec = tp.process_start_end(start, end, date, year, ndays)
            self.assertEqual(start, startC)
            self.assertEqual(end, endC)
            self.assertEqual((end_sec-start_sec)/60, min_diffC)
            assert True
        assert True
