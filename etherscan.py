# Import standard library modules
import json
import time
import requests as r
import datetime as dt

# Import third party modules
from cryptoaddress import EthereumAddress

# Import user defined function from misc-functions
from analytics import LinearForecast as LF

eth_api_token = '<your_token_here>' # required to connect to etherscan.io api

def get_last_block() -> str:
    return int(json.loads(r.get(
        f"https://api.etherscan.io/api?module=block&action=getblocknobytime&timestamp={round(time.time())}&closest=before&apikey={eth_api_token}"
    ).text)["result"])

def get_last_txs(address, since=1600000) -> dict:
    return json.loads(r.get(
        f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock={get_last_block() - since}&sort=asc&apikey={eth_api_token}"
    ).text)["result"]

def get_eth_price(eth_date):
    class BadTickerException(Exception):
        pass

    price_date = dt.datetime.fromtimestamp(eth_date).strftime('%d-%m-%Y')
    try:
        eth_url = f'https://api.coingecko.com/api/v3/coins/ethereum/history?date={price_date}&localization=en'
        data_out = r.request(method='get', url=eth_url)
        json_data = data_out.json()
        try:
            return round(json_data['market_data']['current_price']['usd'], 2)
        except KeyError:
            return None
    except KeyError:
        raise BadTickerException('\n\nUnable to find the specified token.\nMake sure to use full token names, for example:\nBitcoin\nEthereum')

def convert_timestamp(stamp):
    return dt.datetime.fromtimestamp(int(stamp)).strftime('%m/%d/%Y')

def get_wallet_address(blocks:int=500000) -> dict:
    info_dict = {'data':''}
    def input_wallet():
        try:
            wallet_address = EthereumAddress(input('Enter Wallet Address: '))
            print('The address is valid.')
            return wallet_address
        except ValueError:
            print('Invalid address.')
    count = 3
    while count > 0:
        try:
            count -= 1
            wallet = input_wallet()
            transactions = get_last_txs(wallet, since=blocks)
            try:
                value_record = {convert_timestamp(dict['timeStamp']):int(dict['value']) * (10**-18) * get_eth_price(int(dict['timeStamp'])) for dict in transactions}
                gas_record = {convert_timestamp(dict['timeStamp']):(int(dict['gas']) * (10**-9) * get_eth_price(int(dict['timeStamp']))) for dict in transactions}
                if len(value_record.values()) < 2:
                    info_dict['data'] = 'Not enough data to analyze. At least 2 data points are required'
                else:
                    info_dict.update({'data':'Showing data in USD', 'value_record':value_record, 'gas_record':gas_record})
            except TypeError:
                info_dict['data'] = 'Unable to retreive data at this time. Try again later.'
                value_record = {convert_timestamp(dict['timeStamp']):int(dict['value']) * (10**-18) for dict in transactions}
                gas_record = {convert_timestamp(dict['timeStamp']):(int(dict['gas']) * (10**-9)) for dict in transactions}
                if len(value_record.values()) < 2:
                    info_dict['data'] = 'Not enough data to analyze. At least 2 data points are required'
                else:
                    info_dict.update({'data':'Showing data in ETH (Wei)', 'value_record':value_record, 'gas_record':gas_record})
            break
        except ValueError:
            if count != 0: 
                input_wallet()
            else:
                print('No attempts remain. Please locate your valid ETH wallet address.')
    return info_dict


def append_forecast(periods:int, data:dict=get_wallet_address()) -> dict:
    dates = [dt.datetime.strptime(x,'%m/%d/%Y').strftime('%Y-%m-%d') for x in data['value_record'].keys()]
    vals = list(data['value_record'].values())

    dictionary = {i+1:[dates[i], vals[i]] for i in range(len(dates))}
    forecast = LF(dictionary, periods).linear_regression()

    start_key = len(forecast.keys())
    dictionary.update({start_key+i:[list(forecast.keys())[i], list(forecast.values())[i]] for i in range(start_key)})
    
    dates = [x[0] for x in dictionary.values()]
    values = [x[1] if x[1] >= 0 else 0.0 for x in dictionary.values()]

    return dict(zip(dates, values))

