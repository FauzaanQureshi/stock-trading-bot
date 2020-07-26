from lxml import html
import requests
from time import localtime, sleep
from traceback import print_exc
from os import system


def get_price(name: str = None) -> float:
    """
    Returns current price of IPO as mentioned on google search page and stores time of retrieval in 'time' attribute.

    :param name: IPO Name
    :return: Price of stock
    """

    if name is None:
        name = input("Enter Firm name: ")
    try:
        page = requests.get("https://www.google.com/search?q=bse+"+name+"+live")
        get_price.time = str(localtime()[3:6]).replace(', ', ':')[1:-1]
        get_price.name = name
        tree = html.fromstring(page.content)
        #print(page.content)
        price = tree.xpath('//div[@class="BNeawe iBp4i AP7Wnd"]/text()')
        try:
            return float(str(price[0]).replace(',', ''))
        except IndexError:
            page = requests.get("https://www.google.com/search?q="+name+"+share+price")
            get_price.time = '{:02d}:{:02d}:{:02d}'.format(*localtime()[3:6])
            get_price.name = name
            tree = html.fromstring(page.content)
            price = tree.xpath('//div[@class="BNeawe iBp4i AP7Wnd"]/text()')
            return float(str(price[0]).replace(',', ''))
    except Exception:
        system('connectionFailed.vbs '+name)
        if input('Connection Failed.\n\nTry connecting again? (y/n) : ')=='n':
            exit('ConnectionFailed') 
        else:
            return get_price(name)

if __name__ == '__main__':
    try:
        num_, freq = input("Enter number of times, and frequency: ").split(' ')
        name = input("IPO name: ")
        for x in range(int(num_)):
            price = get_price(name)
            print(get_price.time, price)
            if x != int(num_)-1:
                sleep(float(freq))
    except:
        print('\n\n\n')
        print_exc()
        
    finally:
        input("\n\n\n\n\n\nPress enter...")
