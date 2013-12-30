# -*- coding:utf8 -*-
import re, time, datetime, os
import config

class BankMonth:
    def __init__(self, bankaccount, timestamp):
        self.timestamp = timestamp
        self.income = 0
        self.outcome = 0
        self.bankaccount = bankaccount
        
    def add_income(self, value):
        self.income += value

    def add_outcome(self, value):
        self.outcome += value

class Timestamp:
    """
    class for easier carrier timestap (for printing, sorting, ...)
    """
    def __init__(self, start_date, end_date):
        # from start to .. delimiter
        self.start_date_int = int(time.mktime(time.strptime(start_date, "%d.%m.%Y")))
        self.start_date_datetime = datetime.datetime.fromtimestamp(self.start_date_int)
        
        # from .. delimiter to string i_ for income
        self.end_date_int = int(time.mktime(time.strptime(end_date, "%d.%m.%Y")))
        self.end_date_datetime = datetime.datetime.fromtimestamp(self.end_date_int)
        
        self.start_str = self.start_date_datetime.strftime("%d.%m.%Y")
        self.end_str = self.end_date_datetime.strftime("%d.%m.%Y")
        
        # timestamp start..end together for dictionary key
        self.start_end = (self.start_str+".."+self.end_str)

class BankParser:
    def __init__(self, datafiles):
        """
        Rewrite data and set defaults
        
        :parm datafiles: list of strings (paths to .dat files - files with
                        transactions where each file represent bank account)
        """
        self.datafiles = datafiles
        self.bank_months = {}
        
    def structData(self, print_unparsable_lines=True):
        """
        Read data from self.datafiles (list of file paths)
        Convert entries to self.bank_months (it's dict of bank_accounts - file paths)
            - each dict entry is dict of timestamps with object  BankMonth()
        
        :parm print_unparsable_lines: if True unparsable lines will be printed (in any case are ignored)
        """
        for filename in self.datafiles:
            content = file(filename, "rb").read()
            bank_account = os.path.basename(filename)
            self.bank_months[bank_account] = {}
            
            for line in content.split("\n"):
                stripped_line = line.strip()
                if stripped_line == "": continue
                
                if not re.match("^[0-9]{1,2}.[0-9]{1,2}.[0-9]{4}" # from date
                                +"..[0-9]{1,2}.[0-9]{1,2}.[0-9]{4}" # to date
                                +"[ ]i_[0-9]+([.][0-9]+)?" # income transaction
                                +"€[ ]o_[0-9]+([.][0-9]+)?€$" # outcome transaction
                                , stripped_line):
                    if print_unparsable_lines == True:
                        print "Error, line don't match regex!", stripped_line
                    continue
                
                # parse data
                
                # from i_ string to € currency
                income = stripped_line[stripped_line.find("i_")+2:stripped_line.find("€", stripped_line.find("i_"))]
                income_float = float(income)
                
                # from o_ string to € currency (for outcome)
                outcome = stripped_line[stripped_line.find("o_")+2:stripped_line.find("€", stripped_line.find("o_"))]
                outcome_float = float(outcome)
                
                
                timestamp = Timestamp(start_date=stripped_line[:stripped_line.find("..")],
                                      end_date=stripped_line[stripped_line.find("..")+2:stripped_line.find("i_")-1])
                
                # TODO merge somehow double data (dict indexes with BankMonth object)
                b = BankMonth(bank_account, timestamp)
                
                # count transfer
                b.add_income(income_float)
                b.add_outcome(outcome_float)
                
                self.bank_months[bank_account][timestamp.start_end] = b
        return
    
    def transfers_between_accounts(self, filename):
        """
        Expected format (from bank_one to bank_two has been transferred 10€):
        1.11.2013..30.11.2013 bank_one.dat bank_two.dat 10€
        
        :parm filename: file from where to read transactions between files
        """
        
        transfers = []
        content = file(filename, "rb").read()
        for line in content.split("\n"):
            stripped_line = line.strip()
            
            # skip empty lines
            if stripped_line == "": continue
            
            start_end, from_account, to_account, amount_with_currency = stripped_line.split()
            
            start_date_datetime, enddate_datetime, start_end_str = self.split_startstop(start_end)
            amount, currency = self.split_amount_and_currency(amount_with_currency)
            
            transfers.append({"start":start_date_datetime,
                              "end":enddate_datetime,
                              "start..end":start_end_str,
                              "from":from_account,
                              "to":to_account,
                              "amount":amount,
                              "currency":currency})
        return transfers
    
    def split_startstop(self, start_end):
        """
        Helper for transfers_between_accounts() and deposits()
        
        :parm start_end: string in format 1.11.2013..30.11.2013
        :returns: tuple - formated input to datetime and reformated oritinal
                                            in (sole representatin of) string
        """
        start, end = start_end.split("..")
        start_int = int(time.mktime(time.strptime(start, "%d.%m.%Y")))
        start_date_datetime = datetime.datetime.fromtimestamp(start_int)
        
        end_int = int(time.mktime(time.strptime(end, "%d.%m.%Y")))
        enddate_datetime = datetime.datetime.fromtimestamp(end_int)
        # correctly format start..end
        start_end_str = (start_date_datetime.strftime("%d.%m.%Y")
                                +".."+enddate_datetime.strftime("%d.%m.%Y"))
        return start_date_datetime, enddate_datetime, start_end_str
    
    def split_amount_and_currency(self, amount_with_currency):
        """
        split and put value in right format
        TODO unlock from €
        
        :parm amount_with_currency: string example: 10€
        :returns: tuple of float (amount) and string (currency)
        """
        amount_with_currency = amount_with_currency.strip()
        amount = float(amount_with_currency[:amount_with_currency.find("€")])
        currency = amount_with_currency[amount_with_currency.find("€"):]
        return amount, currency
        
    def deposits(self, filename):
        """
        Example line (in this time range on bank_one deposit for 10€ has expired and for 5€ has been made):
        1.11.2013..30.11.2013 bank_one.dat i_10€ o_5€
        TODO unlock from €
        
        :parm filename: file from where to read deposits (created and expired)
        :returns: list with dicts where created and/or expired deposits is described 
        """
        deposits = []
        
        # on which account deposit has been made (don't count that as outcome)
        content = file(filename, "rb").read()
        for line in content.split("\n"):
            # skip empty lines
            stripped_line = line.strip()
            
            # skip empty lines
            if stripped_line == "": continue
            
            start_end, bank_account = stripped_line.split()[:2]
            
            # from i_ string to € currency (for income)
            income = stripped_line[stripped_line.find("i_")+2:stripped_line.find("€", stripped_line.find("i_"))]
            income_float = float(income)
            
            # from o_ string to € currency (for outcome)
            outcome = stripped_line[stripped_line.find("o_")+2:stripped_line.find("€", stripped_line.find("o_"))]
            outcome_float = float(outcome)
                
            start_date_datetime, enddate_datetime, start_end_str = self.split_startstop(start_end)
            deposits.append({ "start":start_date_datetime,
                              "end":enddate_datetime,
                              "start..end":start_end_str,
                              "account":bank_account,
                              "income":income_float,
                              "outcome":outcome_float,
                              "currency":"€"})
        return deposits
    
    def formatBankAccountMonthRatio(self, bank_months):
        """
        Format traffic separated for all bank accounts
        If transfers and/or deposits are present that are subtracted
        
        """
        # string to return
        ret = ""
        
        bank_accounts = sorted(bank_months.keys(), key=lambda x:x)[::-1]
        for bank_account in bank_accounts:
            middle_output = ""
            
            time_ranges = sorted(bank_months[bank_account].keys(), key=lambda x:x)
            for time_range in time_ranges:
                income_str = "income: %.2f" % (bank_months[bank_account][time_range]["calculated_income"])
                outcome_str = "outcome: %.2f" % (bank_months[bank_account][time_range]["calculated_outcome"])
                
                if (bank_months[bank_account][time_range]["income-transfer"] != 0
                        or bank_months[bank_account][time_range]["outcome-transfer"] != 0):
                    income_str += " (transfer:%.2f)" % bank_months[bank_account][time_range]["income-transfer"]
                    outcome_str += " (transfer:%.2f)" % bank_months[bank_account][time_range]["outcome-transfer"]
                
                if (bank_months[bank_account][time_range]["income-deposit"] != 0
                        or bank_months[bank_account][time_range]["outcome-deposit"] != 0):
                    income_str += " (deposit:%.2f)" % bank_months[bank_account][time_range]["income-deposit"]
                    outcome_str += " (deposit:%.2f)" % bank_months[bank_account][time_range]["outcome-deposit"]
                
                middle_output += time_range+"\n"
                middle_output += income_str + "\n"+outcome_str+"\n"
                middle_output += "balance: %.2f\n" % bank_months[bank_account][time_range]["balance"]
                
                # space between months
                middle_output += "\n"
            
            if middle_output != "":
                if ret != "":
                    ret += "\n\n"
                # print account name
                middle_output = bank_account + "\n" + middle_output
                # remove last two new lines
                middle_output = middle_output[:-2]
                
                ret += middle_output
                ret += "\n"
        
        return ret[:-1]
    
    def calculateBankAccountMonthRatio(self, transfers=None, deposits=None):
        """
        Calculate traffic for all bank accounts.
        If transfers and/or deposits are present that are merged
        
        :parm transfers: take care (ignore transactions) for transfers between accounts
        :type transfers: well structured dict or None
        :parm deposits: take care (ignore transactions) for deposits on accounts
        :type deposits: well structured dict or None
        :returns: dict structure in format:
            {"bank_acc.dat":
                    {"time-range":
                        {"income":value,
                         "outcome":value,
                         "income-transfer":value,
                         "outcome-transfer":value,
                         "income-deposit":value,
                         "outcome-deposit":value,
                         "calculated_income":value,
                         "calculated_outcome":value,
                         "balance":value,
                        }
                    ,# another time range
                    }
            , # another bank account
            }
        """
        # bank accounts
        # "bank_account.dat":{time ranges}, "another_account.dat":{time ranges}, ...
        ret_bank_accounts = {}
        
        bank_accounts = self.bank_months.keys()
        for bank_account in bank_accounts:
            # time ranges
            # "time:range":{attributes}, "time range2":{attributes}, ...
            ret_bank_accounts[bank_account] = {}
            
            # pairs timestamp and BankMonth() objects
            months = self.bank_months[bank_account].items()
            
            # order months by start date in this bank account
            ordered_months = sorted(months, key=lambda x:x[1].timestamp.start_date_int)
            
            for month in ordered_months:
                # initialize time range (month[0] is in format start..end)
                ret_bank_accounts[bank_account][month[0]] = {}
                
                # transfers
                t_income_delta = 0
                t_outcome_delta = 0
                if transfers != None:
                    for transfer in transfers:
                        if transfer["start..end"] == month[0]:
                            if transfer["from"] == bank_account:
                                t_outcome_delta -= transfer["amount"]
                            elif transfer["to"] == bank_account:
                                t_income_delta -= transfer["amount"]
                
                # deposits
                d_income_delta = 0
                d_outcome_delta = 0
                if deposits != None:
                    for deposit in deposits:
                        if deposit["start..end"] == month[0] and deposit["account"] == bank_account:
                            d_income_delta -= deposit["income"]
                            d_outcome_delta-= deposit["outcome"]
                
                calculated_income = month[1].income + t_income_delta + d_income_delta
                calculated_outcome = month[1].outcome + t_outcome_delta + d_outcome_delta
                balance = calculated_income - calculated_outcome
                
                # fill time range attributes
                ret_bank_accounts[bank_account][month[0]]["income"]=            month[1].income
                ret_bank_accounts[bank_account][month[0]]["outcome"]=           month[1].outcome
                ret_bank_accounts[bank_account][month[0]]["income-transfer"]=   t_income_delta
                ret_bank_accounts[bank_account][month[0]]["outcome-transfer"]=  t_outcome_delta
                ret_bank_accounts[bank_account][month[0]]["income-deposit"]=    d_income_delta
                ret_bank_accounts[bank_account][month[0]]["outcome-deposit"]=   d_outcome_delta
                ret_bank_accounts[bank_account][month[0]]["calculated_income"]= calculated_income
                ret_bank_accounts[bank_account][month[0]]["calculated_outcome"]=calculated_outcome
                ret_bank_accounts[bank_account][month[0]]["balance"]=           balance
                
        return ret_bank_accounts
    

if __name__ == "__main__":
    bp = BankParser(config.bank_accounts)
    
    transfers = bp.transfers_between_accounts(config.transfers_file)
    deposits = bp.deposits(config.deposits_file)
    bp.structData(print_unparsable_lines=False)
    
    bank_months = self.calculateBankAccountMonthRatio(transfers=transfers, deposits=deposits)
    print bp.formatBankAccountMonthRatio(bank_months)
    
    