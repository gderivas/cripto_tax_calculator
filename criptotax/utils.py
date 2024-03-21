import configargparse

def get_args():
    parser = configargparse.ArgParser()

    parser.add_argument("-y", "--year", type=int, default="all",
                        help="Select for which year calculate the profits/loss")
    
    parser.add_argument("-p", "--plattform", type=str, default="all",
                        help="Select for which plattform calculate the profits/loss")

    args = parser.parse_args()

    return args






    