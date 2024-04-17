from criptotax.utils import get_args, clean_previous
from criptotax.calculator import tax_calculator

import warnings
warnings.filterwarnings('ignore')

if __name__ == '__main__':
    
    args = get_args()

    clean_previous()

    calc = tax_calculator(args)

    calc.calculate()