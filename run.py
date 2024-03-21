from criptotax.utils import get_args
from criptotax.calculator import tax_calculator

if __name__ == '__main__':
    
    args = get_args()

    calc = tax_calculator(args,path = ['data/trades.csv','data/nmr.csv'])

    tax_calculator.calculate()