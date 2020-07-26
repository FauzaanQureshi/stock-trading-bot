from S_07_IpoPrice import get_price
from math import sqrt, floor
from time import sleep, localtime
import pickle as p
from glob import glob
from os import chdir, system
from traceback import print_exc
import subprocess
from sys import argv

_verbose = True
_freq = 15

class Multiplier:

    def __init__(self, mode: str):
        """

        :param mode: "BUY" or "SELL"
        """
        if mode == 'BUY' or mode == 'b':
            self.counter = 5
        elif mode == "SELL" or mode == 's':
            self.counter = 0
        else:
            raise ValueError

        self.b_count = 20
        self.s_count = 6
        self.next_term = 1
        self.prev_term = 0

    @staticmethod
    def fibonacci(n):
        a = (1+sqrt(5))**n
        b = (1 - sqrt(5))**n
        c = sqrt(5) * (2**n)
        return int((a-b)/c)

    def get_prev(self) -> int:
        self.prev_term = self.fibonacci(self.b_count) if self.b_count > 0 else 0
        self.counter = self.fibonacci(21-self.b_count)
        return self.prev_term

    def b_update(self):
        self.b_count -= 1
        return True

    def get_next(self) -> int:
        self.next_term = self.fibonacci(self.s_count) if self.s_count <= 20 else 0
        self.counter = self.fibonacci(self.s_count-5)
        return self.next_term

    def s_update(self):
        self.s_count += 1
        return True

    def reset(self):
        self.b_count = 20
        self.s_count = 6
        self.counter = 0


class Bot:

    def __init__(self, name: str = None, balance: float = 10000, brokerage_percent: float = 0.05):
        self.initial_capital = balance          # Used for calculating profit / loss
        self.current_price = get_price(name)    # Current Price of 1 share
        self.prev_price = 0                     # Stores price just before current price to show trends
        self.name = get_price.name              # IPO name
        self.balance =  balance                 # Actual Balance Available
        self.avg_price = 0                      # S(Current Price of share x Number of shares) / Total Number of Shares
        self.shares = 0                         # Total Number of shares bought/available
        self.brokerage = brokerage_percent/100  # Brokerage charged
        self.in_profit = False                  # True if current balance > initial balance
        self.change = 0                         # Change in Initial Balance. +ve=> Profit and -ve=> Loss
        self.closing_time = (15, 33, 00)        # Indian Market Closing Time
        self.mode = None                        # BUY or SELL Mode
        self.b = Multiplier(mode='BUY')         # Class to calculate BUYing price
        self.s = Multiplier(mode='SELL')        # Class to calculate SELLing price
        self.force_buy = None                   # Force buy at given price
        self.force_sell = None                  # Force sell at given price
        system('color')                         # Enable console color
        

    def get_price(self, v: bool = False) -> None:
        """
        Updates self.current price by calling IpoPrice.get_price()

        :return: None
        """
        
        self.prev_price = self.current_price
        self.current_price = get_price(self.name)
        
        if localtime()[3:6] > self.closing_time: # <-- Replace with (15, 30, 00) if bots don't load
            print("MARKET CLOSED!!")
            raise KeyboardInterrupt
        if not v:
            if self.current_price > self.prev_price:
                print(get_price.time+"\t\x1b[1;32;40m{:.2f}\x1b[0m".format(self.current_price))
            elif self.current_price < self.prev_price:
                print(get_price.time+"\t\x1b[1;31;40m{:.2f}\x1b[0m".format(self.current_price))
            else:
                print(get_price.time+"\t{:.2f}".format(self.current_price))

    def is_profitable(self) -> bool:
        #if self.shares == 0:
        #    self.avg_price = max(self.current_price, self.avg_price)
        #    print("Shares = 0 Current = {}     avg = {}".format(self.current_price, self.avg_price))
        # print("AveragePrice * brokerage = {:.2f}".format(self.avg_price))
        if self.avg_price==0:
            return False
        if self.current_price > self.avg_price * (1 + self.brokerage):
            return True
        return False

    def update(self, _: tuple) -> tuple:
        """
        Updates:
            self.avg_price
            self.balance
            self.shares

        :param _: tuple containing (shares_bought, price)
            _[0] -->shares_bought: Num of shares bought
            _[1] -->price: Price of 1 share at which above shares were bought
        :return: None
        """
        shares_bought = _[0]
        price = _[1]

        try:
            if shares_bought > 0:
                self.sell()
                system('bought.vbs '+self.name)
                self.avg_price = ((self.shares * self.avg_price) + (shares_bought * price)) / (self.shares + shares_bought)
            elif shares_bought < 0:
                self.buy()
                system('sold.vbs '+self.name)
                #self.avg_price += -(((self.shares * self.avg_price) + (shares_bought * price)) / (self.shares + shares_bought))
                self.avg_price = 0.95*self.current_price #Setting AvgPrice to be 5% less than CurrentPrice. So, Sell cond = 1.083*CurrentPrice and Buy cond = 0.95*(1-0.0067)*CurrentPrice
        except ZeroDivisionError:
                self.buy()
                self.avg_price = (2*self.sell.__func__.condition + self.buy.__func__.condition)/3

        self.shares += shares_bought
        self.balance -= (price * shares_bought)
        self.change = self.balance - self.initial_capital
        self.in_profit = True if (self.change > 0 or (self.change == 0 and self.shares>0)) else False
        del shares_bought
        del price
        return self.shares, self.balance, self.change

    def buy(self, getConditionOnly=False) -> tuple:
        """
        First checks if %bm will be +ve (It'll be for b_count = 5). Then checks if current stock price * brokerage is
        cheaper than avg_price*bm%. If it is cheaper, buy counter number of the shares. If balance is available to buy
        these shares, keep them and reset sell counter to 0, otherwise, buy 0 shares.

        :return: Shares bought, StockPrice*brokerage
        """
        self.mode = 'BUY'
        buy = 0
        bm = self.b.get_prev()
        self.buy.__func__.condition = (self.avg_price*((bm-self.b.b_count)/(bm+self.b.b_count))/(1+self.brokerage))
        if not getConditionOnly:
            self.force_sell = None
            if self.b.b_count >= 5:
                try:
                    if  self.force_buy is None and self.avg_price*((bm-self.b.b_count)/(bm+self.b.b_count)) >= self.current_price*(1+self.brokerage):
                        buy = self.b.counter
                        if buy*self.current_price*(1+self.brokerage) > self.balance:
                            buy = 0
                        else:
                            self.b.b_update()
                            self.s.reset()
                    elif self.force_buy is not None and self.force_buy >= self.current_price*(1+self.brokerage):
                        buy = self.b.counter
                        if buy*self.current_price*(1+self.brokerage) > self.balance:
                            buy = 0
                        else:
                            self.force_buy = None
                            self.b.b_update()
                            self.s.reset()
                except TypeError:
                    pass
            else:
                buy = 0
        
        return buy, self.current_price*(1+self.brokerage)   # shares_bought, price

    def sell(self, getConditionOnly=False) -> tuple:
        """
        First check if s_count = 20 (If it's > 20, %increase in selling point is =1). Next, it checks if current stock
        price + brokerage is more than avg_price * sm. If it is, and we've enough shares available, sell the shares. If
        enough shares are not available, sell the shares actually available. Finally, reset b_count.
        :return: Shares sold, Price at which they are sold
        """
        self.mode = 'SELL'
        sell = 0
        sm = self.s.get_next()
        self.sell.__func__.condition = (self.avg_price*(1+(sm-self.s.s_count)/(sm+self.s.s_count))/(1 + self.brokerage))
                                   # "SELL if CurrentPrice = {:.2f}".format
        if not getConditionOnly:                           
            self.force_buy = None
            if self.s.s_count <= 20 and self.avg_price!=0:
                try:    
                    if self.force_sell is None and self.avg_price*(1+(sm-self.s.s_count)/(sm+self.s.s_count)) <= self.current_price*(1+self.brokerage):
                        if self.change < 0:
                            sell = floor(self.change/(self.avg_price*(1+(sm-self.s.s_count)/(sm+self.s.s_count))))
                            self.b.reset()
                        else:
                            sell = -self.s.counter
                            if sell > self.shares:
                                sell = -self.shares
                                # self.shares = 0
                            else:
                                self.s.s_update()
                                self.b.reset()
                    elif self.force_sell is not None and self.force_sell <= self.current_price*(1+self.brokerage):
                        if self.change < 0:
                            sell = floor(self.change/self.force_sell)
                            self.b.reset()
                        else:
                            sell = -self.s.counter
                            if sell > self.shares:
                                sell = -self.shares
                                # self.shares = 0
                            else:
                                self.s.s_update()
                                self.b.reset()
                        self.force_sell = None
                except TypeError:
                    pass
                    
            else:
                sell = 0

        return sell, self.current_price   # shares_sold, price

    def run(self, f, verbose: bool = False):
        shares = self.shares
        self.get_price(verbose)
        out = self.update(self.sell() if self.is_profitable() else self.buy())
        
        if shares!=self.shares:
            #f.writelines(self.mode+',{:0.2f},'.format(self.current_price)+'{:0.2f},'.format(self.avg_price)+'{:d},{:0.2f},{:0.2f},'.format(*out)+'{:02d}-{:02d}-{:04d},'.format(*reversed(localtime()[:3]))+'{:0.2f},'.format(self.sell.condition)+'{:0.2f},'.format(self.buy.condition)+'\n')
            with open("~"+self.name+"_log.csv", 'a') as file:
                file.writelines(self.mode+',{:0.2f},'.format(self.current_price)+'{:0.2f},'.format(self.avg_price)+'{:d},{:0.2f},{:0.2f},'.format(*out)+'{:02d}-{:02d}-{:04d},'.format(*reversed(localtime()[:3])))
                self.sell(getConditionOnly=True)
                self.buy(getConditionOnly=True)
                file.writelines('{:0.2f},'.format(self.sell.condition)+'{:0.2f},'.format(self.buy.condition)+'\n')
            file.close()
        if verbose:
            if self.current_price > self.prev_price:
                print(self.mode, '\x1b[1;32;40m\t{:.2f}'.format(self.current_price), '\x1b[0m\t{:.2f}'.format(self.avg_price), '\t{:d}\t\t{:0.2f}\t\t{:0.2f}'.format(*out), '\t', get_price.time)
            elif self.current_price < self.prev_price:
                print(self.mode, '\x1b[1;31;40m\t{:.2f}'.format(self.current_price), '\x1b[0m\t{:.2f}'.format(self.avg_price), '\t{:d}\t\t{:0.2f}\t\t{:0.2f}'.format(*out), '\t', get_price.time)
            else:
                print(self.mode, '\t{:.2f}'.format(self.current_price), '\t{:.2f}'.format(self.avg_price), '\t{:d}\t\t{:0.2f}\t\t{:0.2f}'.format(*out), '\t', get_price.time)
            # print('\x1b[1;31;40m',<prints in red>,'\x1b[0m')
            # print('\x1b[1;32;40m', <prints in green>, '\x1b[0m')
            
            
def cmd_menu(bot: Bot)-> None:
    try:
        cmd = input("$> ")
        if cmd=='h' or cmd=='help' or cmd=='?' or cmd=='-h' or cmd=='--help':
            print("\nb\t-> Increase Current Balance")
            print("\nc\t-> View BUY/SELL Conditions")
            print("\ncc\t-> View Complete Conditions")
            print("\nfb\t-> Force BUY at entered price")
            print("\nfs\t-> Force SELL at entered price")
            print("\nf\t-> Change frequency")
            print("\nm\t-> Toggle Market Zone between India and USA")
            print("\nn\t-> Change Firm Name")
            print("\np\t-> View Bot Parameters")
            print("\nsa\t-> Sell all shares")
            print("\nv\t-> Toggle Verbose")
            print("\nq\t-> Exit")
            print("\nh\t-> Show this")
            cmd_menu(bot)
            
        elif cmd=='b':
            bal = float(input("Amount to add to balance: "))
            bot.initial_capital += bal
            bot.balance += bal
            del bal
            
        elif cmd=='fb':
            print('Current Price: ', bot.current_price,'\n')
            bot.buy(getConditionOnly=True)
            print("BUY if CurrentPrice ≤ {:.2f}".format(bot.buy.condition)+'\n')
            bot.force_buy = float(input('Force BUY at price = '))
            
        elif cmd=='fs':
            print('Current Price: ', bot.current_price,'\n')
            bot.sell(getConditionOnly=True)
            print("SELL if CurrentPrice ≥ {:.2f}".format(bot.sell.condition)+'\n')
            bot.force_sell = float(input('Force SELL at price = '))
            
        elif cmd=='c':
            if bot.mode=='SELL':
                print("SELL if CurrentPrice ≥ {:.2f}".format(bot.sell.condition)+'\n')
            else:
                print("BUY if CurrentPrice ≤ {:.2f}".format(bot.buy.condition)+'\n')
                
        elif cmd=='cc':
            print(bot.current_price,'\n')
            bot.sell(getConditionOnly=True)
            print("SELL if CurrentPrice ≥ {:.2f}".format(bot.sell.condition)+'\n')
            bot.buy(getConditionOnly=True)
            print("BUY if CurrentPrice ≤ {:.2f}".format(bot.buy.condition)+'\n')
        
        elif cmd=='m':
            cmd_menu.active = not cmd_menu.active
            bot.closing_time = cmd_menu.zone[cmd_menu.active]
        
        elif cmd=='f':
            global _freq
            _freq = int(input('Enter Frequency of retrieval: '))
            print('\n\n')
            
        elif cmd=='n':
            if input('\n\nSHARE PRICES WILL CHANGE!!!\n\nCONTINUE? <y/n> :')=='y':
                bot.name = input('\n\nEnter New Name : ')
                system('title '+bot.name.upper())
                print('\n\n')
            
        elif cmd=='sa':
            pass
        
        elif cmd=='v':
            global _verbose 
            _verbose = not _verbose
            system('cls')
            if _verbose:
                print("MODE\tCurrent\tAvgPrice\tShares\t\tBalance\t\tProfit/Loss\tTime\n")
                
        elif cmd=='p':
            system('cls')
            print('Name            \t:\t', bot.name.upper())
            print('\nInitial Capital \t:\t {:0.2f}'.format(bot.initial_capital))
            print('Current Balance \t:\t {:0.2f}'.format(bot.balance))
            if bot.in_profit:
                print('\n\x1b[1;32;40mPROFIT          \t:\t{:.2f}\x1b[0m'.format(bot.change))
            else:
                print('\n\x1b[1;31;40mLOSS            \t:\t{:.2f}\x1b[0m'.format(bot.change))
            print('Shares          \t:\t', bot.shares)
            print('Averaged Price  \t:\t {:0.2f}'.format(bot.avg_price))
            print('Brokerage       \t:\t {:0.3f}%'.format(bot.brokerage*100))
            print('\nUpdate Frequency\t:\t {}s'.format(_freq))
            print('Market Zone     \t:\t', 'India' if cmd_menu.active else 'USA')
            print('\n\n\n')
                
        elif cmd=='q':
            exit(0)
            
        elif cmd==' ':
            pass
            
        else:
            cmd_menu(bot)
            
        if not _verbose:
            print(" Time\t\tCurrent")
           
    except KeyboardInterrupt:
        print("")
        cmd_menu(bot)


def main(n):
    chdir("./TradeBots")
    cmd_menu.zone = {True: (15, 33, 00), False: (27, 00, 00)}
    cmd_menu.active = True
    if n!=-1:
        bots = glob("*.bot")
        for index, b in enumerate(bots): print(index, b)
        
        with open(bots[n], 'rb') as _dump:
            bot = p.load(_dump)
        #f = open("~"+bot.name+"_log.csv", 'a')
        f = open("~"+bot.name+"_log.txt", 'a')
        #f.writelines("Mode,Price,AvgPrice,Shares,Balance,Change,Date,SellCondition,BuyCondition\n")
    else:
        bot = Bot(balance=100000)
        f = open("~"+bot.name+"_log.csv", 'a')
        f.writelines("\n================= IPO : "+bot.name+" ====================\n")
        f.writelines("Mode,Price,AvgPrice,Shares,Balance,Change,Date,SellCondition,BuyCondition\n")
        f.close()
    system('title '+bot.name.upper())
    system('cls')
    print("MODE\tCurrent\tAvgPrice\tShares\t\tBalance\t\tProfit/Loss\tTime\n")
    
    try:
        bot.closing_time = (15, 33, 00)
        bot.force_sell = None
        bot.force_buy = None
        bot.brokerage = 0.075/100
        frequency = _freq
        while True:#bot.change <= 0 and bot.shares!=0:
            try:
                bot.run(f, verbose=_verbose)
                sleep(frequency)
                if bot.mode == 'SELL' and bot.current_price*1.0037 >= bot.sell.__func__.condition:
                    frequency = 5
                elif bot.mode == 'BUY' and bot.current_price*0.9981 <= bot.buy.__func__.condition:
                    frequency = 5
                else:
                    frequency = _freq 
            except KeyboardInterrupt:
                print('\n\n')
                cmd_menu(bot)
    except SystemExit:
        pass
    except:
        print_exc()
        input("\n\n\n\nPress Enter...")
    finally:
        with open(bot.name+'.bot', 'wb') as _dump:
            p.dump(bot, _dump, protocol=p.HIGHEST_PROTOCOL)
        f.flush()
        f.close()
        

if __name__ == '__main__':
    if argv.__len__()==2:
        main(int(argv[1]))
    else:
        system('cls')
        n_bots = glob("./TradeBots/*.bot")
        print(*enumerate(n_bots), sep='\n')
        load_choice = input('\nLoad all bots? <y/n>\nPress "n" to create new bot\n\n: ')
        if load_choice!='n' and n_bots.__len__() !=0 :
            for i in range(n_bots.__len__()):
                subprocess.Popen([r'C:\ProgramData\Anaconda3\python.exe', 'TradeBot.py', str(i)], creationflags=subprocess.CREATE_NEW_CONSOLE)
            
        elif load_choice=='n':
            if input('\nCreate New Bot? <y/n>\n:')!='y':
                subprocess.Popen([r'C:\ProgramData\Anaconda3\python.exe', 'TradeBot.py', str(int(input('Open Bot @ Index = ')))], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                main(-1)
