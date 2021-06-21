from binance.api import API
from binance.spot import Spot
from binance.spot.account import account
from binance.spot.blvt import redemption_record 
from binance.websocket.spot.websocket_client import SpotWebsocketClient as WebsocketClient
from binance.lib.utils import config_logging

import logging
import numpy as np
import time

config_logging(logging, logging.INFO)


class MM:
    def __init__(self):
        #read API Key
        with open('API_Key','r') as f:
            API_Key= f.read().replace('\n','')

        with open('Secret_Key','r') as f:
            Secret_Key = f.read().replace('\n','')

        self.client = Spot(base_url='https://testnet.binance.vision',
                        key=API_Key, 
                        secret=Secret_Key)
        
        self.response = self.client.new_listen_key()

        self.listen_key = self.response['listenKey']

        self.spread = 0.00001
        self.exposure = 0.1/3
        self.base = 'BTC'
        self.quote = 'USDT'
        self.price = 0
        self.initialised = False
        self.orders = {"buy": [],
        "sell": []}
        self.rebalancing = False
        self.inventory = [0]
        
        self.ws_client = WebsocketClient(stream_url='wss://testnet.binance.vision')
        self.ws_client.start()

        quote_bal = [x for x in self.client.account()['balances'] if x['asset'] == self.quote]
        quote_bal = float(quote_bal[0]['free'])
        self.initial_cash = quote_bal

    def handle_update_price(self,message):
        
        try:
            self.price = float(message['p'])
            if not self.initialised:
                print('Making the first market')
                self.initialised = True
                self.make_market()
        except:
            pass
        

    def handle_user_data(self,message):
        # logging.info(self.client.time())
        # logging.info([x for x in self.client.account()['balances'] if x['asset'] in [self.base, self.quote]])
 
        try:
            event_type = message['e']
            order_status = message['X']
            last_executed_quant = message['l']
            order_type = message['S']
            # print(f'ordertype - {order_type}')
            if event_type == 'executionReport':
                if (order_status == 'PARTIALLY_FILLED' or order_status == 'FILLED'):
                    if order_type == 'BUY':
                        self.inventory.append(self.inventory[-1] + float(last_executed_quant))
                    elif order_type == 'SELL':
                        self.inventory.append(self.inventory[-1] - float(last_executed_quant))

                    if not self.rebalancing:
                        self.rebalancing = True
                        logging.info('cancelling all')
                        self.cancel_all()
                        logging.info('making markets again')
                        self.make_market()
                        self.rebalancing = False
        except:
            pass
        


    def cancel_all(self):
        self.client.cancel_open_orders(self.base+self.quote)
        

    def make_market(self):
        account_info = self.client.account()
        base_bal = [x for x in account_info['balances'] if x['asset'] == self.base]
        base_bal = float(base_bal[0]['free'])
        quote_bal = [x for x in account_info['balances'] if x['asset'] == self.quote]
        quote_bal = float(quote_bal[0]['free'])
        quote_qty = round(base_bal * self.exposure,5)
        base_qty = round((quote_bal * self.exposure)/self.price, 5)
        quote_qty = 0.02 #override w constant for simplicity
        base_qty = 0.02 #overrid w constant for simplicity
        ask_price = round(self.price + (self.price * (self.spread / 2)),2)
        bid_price = round(self.price - (self.price * (self.spread / 2)),2)
        
        
        for side in ["buy", "sell"]:
            params = {
                'symbol' : self.base + self.quote,  
                'type' : 'LIMIT',
                'side': side,
                "timeInForce": "GTC",
                'quantity' : base_qty if (side == 'buy') else quote_qty,
                'price': bid_price if side == 'buy' else ask_price
            }
            print(params)
            self.orders[side].append(self.client.new_order(**params))
        logging.info(f'Market Made at {base_qty} {bid_price} | {ask_price} {quote_qty} ----- Last Price {self.price}')
        # logging.info('****Orders info')
        # logging.info(f'number of buys {len(self.orders["buy"])} | number of sells {len(self.orders["sell"])}')
        # logging.info(self.orders['buy'][-1])
        # logging.info(self.orders['sell'][-1])

    def report(self):
        # self.cancel_all()
        self.rebalance()
        quote_bal = [x for x in self.client.account()['balances'] if x['asset'] == self.quote]
        quote_bal = float(quote_bal[0]['free'])
        logging.info(f'Profit = { quote_bal - self.initial_cash}')
        logging.info(f'Average Inventory {np.mean(self.inventory[1:])}')
        logging.info(f'Std Dev Inventory {np.std(self.inventory[1:])}')
        # logging.info(self.inventory)
    
    def rebalance(self):
        account_info = self.client.account()
        base_bal = [x for x in account_info['balances'] if x['asset'] == self.base]
        print(base_bal)
        base_bal = float(base_bal[0]['free'])

        if base_bal - 0.7 < -0.01:
            params = {
                    'symbol' : self.base + self.quote,  
                    'type' : 'MARKET',
                    'side': "buy",
                    'quantity' : round(0.7 -  base_bal,3)
                }

            self.client.new_order(**params)

            account_info = self.client.account()
            base_bal = [x for x in account_info['balances'] if x['asset'] == self.base]
            quote_bal = [x for x in account_info['balances'] if x['asset'] == self.quote]
            print(base_bal)
            print(quote_bal)
        
        elif base_bal -0.7 > 0.01:
            params = {
                    'symbol' : self.base + self.quote,  
                    'type' : 'MARKET',
                    'side': "sell",
                    'quantity' : round(base_bal - 0.7,3)
                }

            self.client.new_order(**params)
            account_info = self.client.account()
            base_bal = [x for x in account_info['balances'] if x['asset'] == self.base]
            quote_bal = [x for x in account_info['balances'] if x['asset'] == self.quote]
            print(base_bal)
            print(quote_bal)
        


    def run(self):

        self.ws_client.trade(
            symbol='btcusdt',
            id = 1,
            callback=self.handle_update_price
            )
        

        self.ws_client.user_data(
            listen_key=self.listen_key,
            id=2,
            callback=self.handle_user_data,
        )



if __name__ == '__main__':
    marketmaker = MM()
    marketmaker.rebalance()
    marketmaker.run()
    time.sleep(60)
    logging.debug("closing ws connection")
    marketmaker.ws_client.stop()
    marketmaker.report()

