import random
from InputsConfig import InputsConfig as p
import numpy as np

class Network:
    
    # Delay for propagating blocks in the network
    #def block_prop_delay():
    #	return random.expovariate(1/p.Bdelay)

    def block_prop_delay(block_prop_time):
        mean_block_prop_time = np.log(2) / block_prop_time
        return random.expovariate(1/mean_block_prop_time)

    # Delay for propagating transactions in the network
    def tx_prop_delay():
    	return random.expovariate(1/p.Tdelay)
