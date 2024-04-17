import configargparse
import requests
from datetime import datetime
import json
import time
import os

def get_args():
    parser = configargparse.ArgParser()

    parser.add_argument("-y", "--year", type=str, default="all",
                        help="Select for which year calculate the profits/loss")
    
    parser.add_argument("-p", "--plattform", type=str, default="all",
                        help="Select for which plattform calculate the profits/loss")
    
    parser.add_argument("-e", "--export", type=bool, default=True,
                    help="Export results.")
    
    parser.add_argument("-cf", "--coinbase_file", type=str, default="data/coinbase.csv",
                        help="Select the coinbase export file")
    
    parser.add_argument("-kf", "--kraken_file", type=str, default="data/kraken.csv",
                    help="Select the coinbase export file")
    
    parser.add_argument("-nf", "--nmr_file", type=str, default="data/nmr.csv",
                    help="Select the coinbase export file")

    args = parser.parse_args()

    return args

def preprocees_coinbase(df):
    if (df['Transaction Type'] == 'Receive') & ('Earn' in df.Notes):
        df.transaction = 'earn'
        df.beneficio_earn = df['Quantity Transacted']*df['Price at Transaction'] - df['Fees and/or Spread']
    elif df['Transaction Type'] == 'Buy':
        df.transaction = 'buy'
        df.beneficio_earn = 0
    elif (df['Transaction Type'] == 'Receive') & ('GDAX' in df.Notes):
        df.transaction = 'buy'
        df.beneficio_earn = 0
    else:
        df.transaction = '-'
        df.beneficio_earn = 0
    return df

def get_price(df):
    print(str(df.time))
    timestamp = datetime.strptime(str(df.time), "%Y-%m-%d %H:%M:%S").timestamp()
    endpoint = 'https://api.kraken.com/0/public/OHLC'
    pair = df.asset+'EUR'
    payLoad = {'pair':pair,
           'interval':10080,
           'since' : timestamp}
    response = requests.get(endpoint, payLoad)
    
    if df.asset == 'BTC':
        pair_ = 'XXBTZEUR'
    elif df.asset == 'ETH':
        pair_ = 'XETHZEUR'
    else:
        raise ValueError(f'No {df.asset} pair information for kraken API')
        
    try:
        df['precio'] = response.json()['result'][pair_][0][1]
        timestamp_price = response.json()['result'][pair_][0][0]
        df['fecha_precio'] = datetime.fromtimestamp(timestamp_price) 
    except:
        print(str(df.time))
        print(json.loads(response.text))
        
    time.sleep(5)
    return df

def preprocess_kraken(df):
    cond1 = (df.asset_sum.startswith('EUR')) & (df.amount_first < 0)
    cond2 = (not df.asset_sum.startswith('EUR')) & (df.amount_first > 0)
    if cond1:
        df['asset'] = df.asset_sum[-3:]
        df['transaction'] = 'buy'
        df['coste' ]= abs(df.amount_first)
        df['cantidad'] = abs(df.amount_last)
        df['fee_cripto'] = abs(df.fee_last)
        df['fee_euro'] = abs(df.fee_first)
    elif cond2:
        df['asset'] = df.asset_sum[:3]
        df['transaction'] = 'buy'
        df['coste' ]= abs(df.amount_last)
        df['cantidad'] = abs(df.amount_first)
        df['fee_cripto'] = abs(df.fee_first)
        df['fee_euro'] = abs(df.fee_last)
    else:
        df['asset'] = df.asset_sum[:3]
        df['transaction'] = 'sell'
        df['coste'] = abs(df.amount_last)
        df['cantidad'] = abs(df.amount_first)
        df['fee_cripto'] = abs(df.fee_first)
        df['fee_euro'] = abs(df.fee_last)
    return df

def calculate_coin_profit(df_coin):
    ledger = 0

    df_coin['ledger'] = 0
    df_coin['cantidad_por_vender'] = df_coin['cantidad']
    df_coin['beneficio_trades'] = 0 

    for index,row in df_coin.iterrows():
        if (row.transaction == 'buy') | (row.transaction == 'earn'):
            ledger += row.cantidad
        elif row.transaction == 'sell':
            ledger -= row.cantidad
            cantidad_a_vender = row.cantidad
            beneficio = 0
            precio_venta = row.precio
            for index2,row2 in df_coin.iterrows():
                cantidad_por_vender = row2.cantidad_por_vender
                if (cantidad_por_vender > 0) & ((row2.transaction == 'buy') | (row2.transaction == 'earn')):
                    precio_compra = row2.precio
                    dif_precio = precio_venta - precio_compra
                    if cantidad_por_vender >= cantidad_a_vender:
                        df_coin.at[index2,'cantidad_por_vender'] = cantidad_por_vender - cantidad_a_vender
                        df_coin.at[index2,'beneficio_trades'] = row2.beneficio_trades + dif_precio*cantidad_a_vender
                        df_coin.at[index,'cantidad_por_vender'] = 0
                        beneficio = beneficio + dif_precio*cantidad_a_vender
                        df_coin.at[index,'beneficio_trades'] = beneficio
                        break
                    else: # Si la cantidad por vender es menor que la cantidad a vender
                        df_coin.at[index2,'beneficio_trades'] = row2.beneficio_trades + dif_precio*cantidad_por_vender
                        cantidad_a_vender = cantidad_a_vender - cantidad_por_vender
                        df_coin.at[index2,'cantidad_por_vender'] = 0
                        df_coin.at[index,'cantidad_por_vender'] = cantidad_a_vender
                        beneficio = beneficio + dif_precio*cantidad_por_vender
                        df_coin.at[index,'beneficio_trades'] = beneficio
        elif row.transaction == 'burn':
            ledger += row.cantidad
            df_coin.at[index,'cantidad_por_vender'] = 0
            df_coin.at[index,'beneficio_trades'] = 0
        
        df_coin.at[index,'ledger'] = ledger
    return df_coin


def clean_previous():
    path = 'data/export/'
    files = os.listdir(path)
    for file in files:
        if os.path.isfile(path + file):
            os.remove(path + file)






    