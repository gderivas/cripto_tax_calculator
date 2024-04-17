import pandas as pd
import os
from criptotax.utils import preprocees_coinbase, preprocess_kraken, get_price, calculate_coin_profit

class tax_calculator:
    def __init__(self, args):
        self.args = args
        self.kraken_path = args.kraken_file
        self.nmr_path = args.nmr_file
        self.coinbase_path = args.coinbase_file
        self.dfk, self.dfn, self.dfc = self.import_data()

    def import_data(self):
        dfk, dfn, dfc = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        if self.args.plattform == 'all':
            dfn = pd.read_csv(self.nmr_path) # Numerai may be in different files per year -> method
            dfk = pd.read_csv(self.kraken_path)
            dfc = pd.read_csv(self.coinbase_path)
        elif self.args.plattform == 'kraken':
            dfk =  dfk =  pd.read_csv(self.kraken_path)
        elif self.args.plattform == 'nmr':
            dfn = pd.read_csv(self.nmr_path)
        elif self.args.plattform == 'coinbase':
            dfc = pd.read_csv(self.coinbase_path)
        else:
            print('Plattform not recognized')
        print('\nData import succesfully!')
        return dfk,dfn,dfc

    def calculate(self):
        if self.args.plattform == 'all':
            self.calculate_kraken()
            self.dfn_result = self.calculate_nmr()
            self.calculate_coinbase()
        elif self.args.plattform == 'kraken':
            self.calculate_kraken()
        elif self.args.plattform == 'nmr':
            self.dfn_result = self.calculate_nmr()
        elif self.args.plattform == 'coinbase':
            self.calculate_coinbase()
        self.join_exchanges()
        self.summary()
    
    def calculate_coinbase(self):
        print('\nCalculating Coinbase earn profits.')
        dfc = self.dfc
        dfc.Timestamp = pd.to_datetime(dfc.Timestamp.replace('UTC',''))
        dfc.sort_values(by='Timestamp',ascending=True,inplace=True)
        dfc.Notes.fillna('-',inplace=True)
        dfc['transaction'] = '-'
        dfc['beneficio_earn'] = 0

        dfc = dfc.apply(preprocees_coinbase,axis=1)

        dfc['year'] = dfc.Timestamp.dt.year

        dfc = dfc.rename(columns={'Timestamp':'time','Transaction Type':'type','Asset':'asset',
                        'Price at Transaction':'precio','Quantity Transacted':'cantidad',
                        'Fees and/or Spread':'fee','Subtotal':'coste'})

        self.dfc = dfc
        
        if self.args.year == 'all':
            pass
        else:
            dfc = dfc[dfc.year == int(self.args.year)]

        return print(dfc.groupby(['asset','year'])['beneficio_earn'].sum())


    def calculate_nmr(self):
        print('\nCalculating Numerai staked payouts/burns profit&losses:')
        dfn = self.dfn
        dfn = dfn[dfn.type.isin(['burn', 'payout'])]
        dfn.inserted_at = pd.to_datetime(dfn.inserted_at)
        dfn['year'] = dfn.inserted_at.dt.year 
        dfn['profit/loss'] = dfn.value*dfn.nmr_price
        dfn['tax'] = dfn['profit/loss']*0.19 # Calculate % based on profit amount
        dfn['transaction'] = ['earn' if tipo == 'payout' else 'burn' for tipo in dfn.type]
        dfn['asset'] = 'NMR'
        dfn['fee'] = 0
        dfn = dfn.rename(columns = {'inserted_at':'time','nmr_price':'precio','value':'cantidad','profit/loss':'beneficio_earn'})
        dfn['coste'] = dfn['beneficio_earn']
        self.dfn = dfn

        if self.args.year == 'all':
            pass
        else:
            dfn = dfn[dfn.year == int(self.args.year)]

        return print(dfn.groupby('year')[['beneficio_earn','tax']].sum())

    def calculate_kraken(self):
        print('\nCalculating Kraken earn profits/losses:')
        dfk = self.dfk
        dfk_s = dfk[(dfk.type == 'earn') | (dfk.type == 'staking')]
        dfk_s['type'] = 'earn'
        dfk_s = dfk_s[~((dfk_s.fee ==0) & (dfk_s.asset == 'ETH'))]
        dfk_s.asset = dfk_s.asset.replace('BTC.M','BTC').replace('ETH2','ETH')
        dfk_s.time = pd.to_datetime(dfk_s.time)
        dfk_s['year'] = dfk_s.time.dt.year
        dfk_s = dfk_s[dfk_s.amount >= 0]
        dfk_s = dfk_s[dfk_s.txid != 'LR6D75-Z6ZFD-K44RMB'] # Pasar una lista en los argumentos / Identificar
        dfk_s['amount'] = dfk_s['amount'] + dfk_s['fee']
                
        file_precios = 'data/stake_prices.xlsx' # Pasar el fichero como argumento
        if os.path.isfile(file_precios):
            precios_stake = pd.read_excel(file_precios)
            dfk_s['precio'] = dfk_s.time.map(dict(zip(precios_stake.time,precios_stake.precio)))
            dfk_s['fecha_precio'] = dfk_s.time.map(dict(zip(precios_stake.time,precios_stake.fecha_precio)))

        else:
            print(f'Getting prices from Kraken API, this may take aprox. {dfk_s.shape[0]*5/60} Minutes')
            dfk_s = dfk_s.apply(get_price,axis=1)
            dfk_s['fecha_dif'] = dfk_s.time - dfk_s.fecha_precio
            dfk_s[['time','precio','fecha_precio','fecha_dif']].to_excel('data/stake_prices.xlsx',index=False) # Fichero como argumento

        dfk_s['beneficio_earn'] = dfk_s.amount*dfk_s.precio + dfk_s.fee
        dfk_s.precio = dfk_s.precio.astype(float)
        dfk_s['transaction'] = 'earn'
        dfk_s['cantidad'] = dfk_s['amount']
        dfk_s['coste'] = dfk_s['beneficio_earn'] + dfk_s['fee']
        self.dfk_s = dfk_s

        dfk_trades = dfk[dfk.type.isin(['trade','spend','receive'])].groupby('refid').agg({'time':'first','asset':'sum','amount':['first','last'],'fee':['first','last']}).reset_index()
        dfk_trades.columns = dfk_trades.columns.map('{0[0]}_{0[1]}'.format)

        dfk_trades.time_first = pd.to_datetime(dfk_trades.time_first)
        dfk_trades.sort_values(by='time_first',ascending=True,inplace=True)

        dfk_trades = dfk_trades[dfk_trades.asset_sum.str.contains('EUR')]
        dfk_trades = dfk_trades.apply(preprocess_kraken,axis=1)

        dfk_trades['precio'] = dfk_trades.coste/dfk_trades.cantidad
        dfk_trades['fee'] = dfk_trades['fee_cripto']*dfk_trades.precio + dfk_trades['fee_euro']

        dfk_trades = dfk_trades.rename(columns = {'time_first':'time'})

        dfk_trades['beneficio_earn'] = 0
        dfk_trades['beneficio_trades'] = 0

        self.dfk_trades = dfk_trades

        if self.args.year == 'all':
            pass
        else:
            dfk_s = dfk_s[dfk_s.year == int(self.args.year)]

        return print(dfk_s.groupby(['year','asset'])['beneficio_earn'].sum())
    
    def join_exchanges(self):
        print('\nJoining all exchages orders')
        select_columns = ['time','asset','transaction','cantidad','coste','precio','fee','beneficio_earn']
        if (self.args.plattform == 'coinbase') | (self.args.plattform == 'all'):
            self.dfc = self.dfc[select_columns]
        if (self.args.plattform == 'nmr') | (self.args.plattform == 'all'):
            self.dfn = self.dfn[select_columns]
        if (self.args.plattform == 'kraken') | (self.args.plattform == 'all'):
            self.dfk_s = self.dfk_s[select_columns]
            self.dfk_trades = self.dfk_trades[select_columns]
        df = pd.concat([self.dfk_trades,self.dfc,self.dfk_s,self.dfn])
        df.time = pd.to_datetime(df.time, utc=True)
        df.sort_values(by='time',inplace=True)
        df = df[df.transaction != '-'] ################################################# REVISAR
        self.df = df

        print('Calculating profit&losses for all trades')

        df_final = pd.DataFrame()
        for coin in df.asset.unique():
            df_asset = df[df.asset == coin]
            df_asset = calculate_coin_profit(df_asset.reset_index())
            df_asset['time'] = df_asset['time'].dt.tz_localize(None)
            df_asset['year'] = df_asset['time'].dt.year
            if self.args.export:
                df_asset.to_excel('data/export/' + coin +'.xlsx', index=False)
            df_final = pd.concat([df_final,df_asset])
    
        df_final['beneficio'] = df_final['beneficio_trades'] + df_final['beneficio_earn']
        
        if self.args.year == 'all':
            pass
        else:
            df_final = df_final[df_final.year == int(self.args.year)]

        df_final = df_final.sort_values(by='time')
        df_final.drop(['index'],axis=1,inplace=True)

        if self.args.export:
            df_final.to_excel('data/export/result.xlsx',index=False)

        self.df_final = df_final
        return print(df_final[df_final.transaction == 'sell'].groupby(['asset','year'])['beneficio_trades'].sum())

    def summary(self):
        print('\nSummary:')
        return print(self.df_final[(self.df_final.transaction == 'sell') | (self.df_final.transaction == 'earn') | (self.df_final.transaction == 'burn')].groupby(['asset','year'])['beneficio'].sum())





        