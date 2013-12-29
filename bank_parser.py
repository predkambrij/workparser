# -*- coding:utf8 -*-
import re, time, datetime, os
import config

class BankMonth:
    def __init__(self, bankaccount, start, end):
        self.start = start
        self.end = end
        self.income = 0
        self.outcome = 0
        self.bankaccount = bankaccount
        
    def add_income(self, value):
        self.income += value

    def add_outcome(self, value):
        self.outcome += value


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
                
                # from start to .. delimiter
                start_date = stripped_line[:stripped_line.find("..")]
                start_date_int = int(time.mktime(time.strptime(start_date, "%d.%m.%Y")))
                start_date_datetime = datetime.datetime.fromtimestamp(start_date_int)
                
                # from .. delimiter to string i_ for income
                end_date = stripped_line[stripped_line.find("..")+2:stripped_line.find("i_")-1]
                end_date_int = int(time.mktime(time.strptime(end_date, "%d.%m.%Y")))
                end_date_datetime = datetime.datetime.fromtimestamp(end_date_int)
                
                # from i_ string to € currency
                income = stripped_line[stripped_line.find("i_")+2:stripped_line.find("€", stripped_line.find("i_"))]
                income_float = float(income)
                
                # from o_ string to € currency (for outcome)
                outcome = stripped_line[stripped_line.find("o_")+2:stripped_line.find("€", stripped_line.find("o_"))]
                outcome_float = float(outcome)
                
                # timestamp start..end together for dictionary key
                start_end = start_date_datetime.strftime("%d.%m.%Y")+".."+end_date_datetime.strftime("%d.%m.%Y")
                
                self.bank_months[bank_account][start_end] = BankMonth(bank_account, start_date_datetime, end_date_datetime)
                
                # count transfer
                self.bank_months[bank_account][start_end].add_income(income_float)
                self.bank_months[bank_account][start_end].add_outcome(outcome_float)
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
    
    def bankAccountMonthRatio(self, transfers=None, deposits=None):
        """
        Format traffic separated for all bank accounts
        If transfers and/or deposits are present that are subtracted
        
        :parm transfers: take care (ignore transactions) for transfers between accounts
        :type transfers: well structured dict or None
        :parm deposits: take care (ignore transactions) for deposits on accounts
        :type deposits: well structured dict or None
        """
        ret = ""
        
        bank_accounts = self.bank_months.keys()
        for bank_account in bank_accounts:
            if ret != "":
                ret += "\n\n"
            # pairs timestamp and BankMonth() objects
            months = self.bank_months[bank_account].items()
            
            # order months by start date in this bank account
            ordered_months = sorted(months, key=lambda x:x[1].start)
            
            middle_output = ""
            for month in ordered_months:
                # start..end
                middle_output += month[0] + "\n"
                
                t_income_delta = 0
                t_outcome_delta = 0
                if transfers != None:
                    for transfer in transfers:
                        if transfer["start..end"] == month[0]:
                            if transfer["from"] == bank_account:
                                t_outcome_delta -= transfer["amount"]
                            elif transfer["to"] == bank_account:
                                t_income_delta -= transfer["amount"]
                
                d_income_delta = 0
                d_outcome_delta = 0
                if deposits != None:
                    for deposit in deposits:
                        if deposit["start..end"] == month[0] and deposit["account"] == bank_account:
                            d_income_delta -= deposit["income"]
                            d_outcome_delta-= deposit["outcome"]
                
                income_str = ""
                outcome_str = ""
                income = month[1].income + t_income_delta + d_income_delta
                outcome = month[1].outcome + t_outcome_delta + d_outcome_delta
                income_str += "income: %.2f" % (income)
                outcome_str += "outcome: %.2f" % (outcome)
                
                if t_income_delta != 0 or t_outcome_delta != 0:
                     income_str += " (transfer:%.2f)" % t_income_delta
                     outcome_str += " (transfer:%.2f)" % t_outcome_delta
                
                if d_income_delta != 0 or d_outcome_delta != 0:
                     income_str += " (deposit:%.2f)" % d_income_delta
                     outcome_str += " (deposit:%.2f)" % d_outcome_delta
                
                
                middle_output += income_str + "\n"
                middle_output += outcome_str + "\n"
                
                middle_output += "balance: %.2f\n" % (income-outcome)
                
                # space between months
                middle_output += "\n"
                
            if middle_output != "":
                # print account name
                middle_output = bank_account + "\n" + middle_output
                # remove last two new lines
                middle_output = middle_output[:-2]
            
            ret += middle_output
            ret += "\n"
            
        return ret[:-1] # remove last new line
    

if __name__ == "__main__":
    bp = BankParser(config.bank_accounts)
    
    transfers = bp.transfers_between_accounts(config.transfers_file)
    deposits = bp.deposits(config.deposits_file)
    bp.structData(print_unparsable_lines=False)
    
    
    print bp.bankAccountMonthRatio(transfers=transfers, deposits=deposits)
    
    