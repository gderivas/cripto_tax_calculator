class tax_calculator:
    def __init__(self, args,path = ['data/trades.csv','data/nmr.csv']):
        self.args = args
        self.kraken_path = path[0]
        self.nmr_path = path[1]
        self.kraken_data, self.nmr_data = self.import_data(args.plattform)

    def import_data(self):
        if self.args.plattform == 'all':
            df_n =  ''
            df_k =  ''
        elif self.args.plattform == 'kraken':
            df_k =  ''
        elif self.args.plattform == 'nmr':
            df_n = ''
        else:
            print('Plattform not recognized')
        return df_k,df_n

    def calculate(self):
        if self.args.plattform == 'all':
            self.calculate_kraken()
            self.calculate_nmr()
        elif self.args.plattform == 'kraken':
            self.calculate_kraken()
        elif self.args.plattform == 'nmr':
            self.calculate_nmr()
        self.summary()


    def calculate_nmr(self):
        pass

    def calculate_kraken(self):
        pass

    def summary(self):
        pass

    def export(self):
        pass




        