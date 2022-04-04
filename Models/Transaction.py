import random
from InputsConfig import InputsConfig as p
import numpy as np
import Models.Network
import operator
from scipy.stats import bernoulli
from metalog import metalog
import copy
from Models.Network import Network

class Transaction(object):

    """ Defines the Ethereum Block model.

    :param int id: the uinque id or the hash of the transaction
    :param int timestamp: the time when the transaction is created. In case of Full technique, this will be array of two value (transaction creation time and receiving time)
    :param int sender: the id of the node that created and sent the transaction
    :param int to: the id of the recipint node
    :param int value: the amount of cryptocurrencies to be sent to the recipint node
    :param int size: the transaction size in MB
    :param int gasLimit: the maximum amount of gas units the transaction can use. It is specified by the submitter of the transaction
    :param int usedGas: the amount of gas used by the transaction after its execution on the EVM
    :param int gasPrice: the amount of cryptocurrencies (in Gwei) the submitter of the transaction is willing to pay per gas unit
    :param float fee: the fee of the transaction (usedGas * gasPrice)
    """

    def __init__(self,
	 id=0,
	 timestamp=0 or [],
	 sender=0,
         to=0,
         value=0,
	 size=0.000505,
     weight=0,
         fee=0):

        self.id = id
        self.timestamp = timestamp
        self.sender = sender
        self.to= to
        self.value=value
        self.size = size
        self.weight = weight
        self.fee= fee


class LightTransaction():

    pending_transactions=[] # shared pool of pending transactions

    """Block propagation time: linear regression model parameters
    m: slope 
    q: intercept 
    """
    m = 0.2484
    q = 0.1539

    #Static Block Header Size (unit: MB)
    static_block_header_size = 0.000080

    def estimate_block_propagation_time(block_size):

        estimated_block_propagation_time = LightTransaction.m * block_size + LightTransaction.q
        return estimated_block_propagation_time

    def create_transactions():

        LightTransaction.pending_transactions=[]
        pool= LightTransaction.pending_transactions
        Psize= int(p.Tn * p.Binterval)

        count_segwit = 0

        #fit metalog distribution to basedata size over total tx size (it only applies to segwit txs)
        sample_data_basedata_size_over_total_tx_size_per_segwit_tx = np.array(p.basedata_size_over_total_tx_size_per_segwit_tx)
        metalog_distribution_basedata_size_over_total_tx_size_per_segwit_tx = metalog.fit(x=sample_data_basedata_size_over_total_tx_size_per_segwit_tx, boundedness='b', bounds=[0, 1], term_limit=5)

        #fit metalog distribution to segwit txs over total txs per block (it applies to any block)
        sample_data_segwit_txs_over_total_txs_per_block = np.array(p.segwit_txs_over_total_txs_per_block)
        metalog_distribution_segwit_txs_over_total_txs_per_block = metalog.fit(x=sample_data_segwit_txs_over_total_txs_per_block, boundedness='b', bounds=[0, 1], term_limit=19)

        #Draw samples from metalog_distribution (n is number of samples and term specifies the terms of distribution to sample from)
        segwit_txs_over_total_txs = metalog.r(m=metalog_distribution_segwit_txs_over_total_txs_per_block, n=1, term=19)

        for i in range(Psize):
            # assign values for transactions' attributes. You can ignore some attributes if not of an interest, and the default values will then be used
            tx= Transaction()

            tx.id= random.randrange(100000000000)
            tx.sender = random.choice (p.NODES).id
            tx.to= random.choice (p.NODES).id
            tx.size= random.expovariate(1/p.Tsize)
            r = bernoulli.rvs(segwit_txs_over_total_txs)
            #print ("\nBERNOULLI RV: {}".format(r))
            if r == 1:
                #It is a segwit tx
                count_segwit +=1
                #Draw samples from metalog_distribution (n is number of samples and term specifies the terms of distribution to sample from)
                basedata_size_over_total_tx_size = metalog.r(m=metalog_distribution_basedata_size_over_total_tx_size_per_segwit_tx, n=1, term=5)
                basedata_size = round(tx.size * basedata_size_over_total_tx_size[0], 9)
                #print ("\n% BASEDATA SIZE: {}".format(basedata_size))
                tx.weight= basedata_size * 3 + tx.size
            else:
                #It is a legacy tx
                tx.weight= 4 * tx.size

            tx.fee= random.expovariate(1/p.Tfee)

            pool += [tx]

        print ("\nPERCENTAGE SEGWIT TX POOL: {}".format(count_segwit/Psize))
        random.shuffle(pool)


    ##### Select and execute a number of transactions to be added in the next block #####
    def execute_transactions(IsSegWitNode):
        transactions= [] # prepare a list of transactions to be included in the block
        size = LightTransaction.static_block_header_size # to store the total block size (in MB)
        count=0 # to scan txs in the pool
        block_propagation_time = 0 # to store the estimated block progation delay (in seconds)
        pool= LightTransaction.pending_transactions

        if IsSegWitNode == True:

            weight = 0 # to store the total block weight (in Million Weight Units)
            count_segwit = 0 #to count the number of segwit txs in the block
            count_legacy = 0 #to count the number of legacy txs in the block
            block_weight = p.Bweight # the average block weight to match (in Million Weight Units)
        
            pool = sorted(pool, key=lambda x: 4 * x.fee/x.weight, reverse=True) # sort pending transactions in the pool based on the Satoshi/Vbyte value

            while count < len(pool):
                if (block_weight >= pool[count].weight):
                    block_weight -= pool[count].weight
                    transactions += [pool[count]]
                    size += pool[count].size
                    weight += pool[count].weight
                    if pool[count].weight < 4 * pool[count].size:
                        count_segwit+=1
                        #print ("\nCOUNT: {} - SEGWIT".format((count_segwit)))
                    else:
                        count_legacy+=1
                        #print ("\nCOUNT: {} - LEGACY".format((count_legacy)))
                count+=1

            print ("\nPERCENTAGE SEGWIT TX BLOCK: {}".format((count_segwit/(count_segwit + count_legacy))))
            block_propagation_time = LightTransaction.estimate_block_propagation_time(size)
            return transactions, size, weight, block_propagation_time

        blocksize = p.Bsize

        pool = sorted(pool, key=lambda x: x.fee/x.size, reverse=True) # sort pending transactions in the pool based on the Satoshi/Byte value

        while count < len(pool):
            if (blocksize >= pool[count].size):
                blocksize -= pool[count].size
                transactions += [pool[count]]
                size += pool[count].size
            count+=1

        block_propagation_time = LightTransaction.estimate_block_propagation_time(size)
        return transactions, size, 0, block_propagation_time


class FullTransaction():

    """Block propagation time: linear regression model parameters
    m: slope 
    q: intercept 
    """
    m = 0.2484
    q = 0.1539

    #Static Block Header Size (unit: MB)
    static_block_header_size = 0.000080

    def estimate_block_propagation_time(block_size):

        estimated_block_propagation_time = LightTransaction.m * block_size + LightTransaction.q
        return estimated_block_propagation_time

    def create_transactions():
        Psize= int(p.Tn * p.simTime)

        count_segwit = 0

        #fit metalog distribution to basedata size over total tx size (it only applies to segwit txs)
        sample_data_basedata_size_over_total_tx_size_per_segwit_tx = np.array(p.basedata_size_over_total_tx_size_per_segwit_tx)
        metalog_distribution_basedata_size_over_total_tx_size_per_segwit_tx = metalog.fit(x=sample_data_basedata_size_over_total_tx_size_per_segwit_tx, boundedness='b', bounds=[0, 1], term_limit=5)

        for i in range(Psize):
            # assign values for transactions' attributes. You can ignore some attributes if not of an interest, and the default values will then be used
            tx= Transaction()

            tx.id= random.randrange(100000000000)
            creation_time= random.randint(0,p.simTime-1)
            receive_time= creation_time
            tx.timestamp= [creation_time,receive_time]
            sender= random.choice (p.NODES)
            tx.sender = sender.id
            tx.to= random.choice (p.NODES).id
            tx.size= random.expovariate(1/p.Tsize)

            r = bernoulli.rvs(p.segwit_txs_over_total_txs, size=1)
            #print ("\nBERNOULLI RV: {}".format(r))
            if r == 1:
                #It is a segwit tx
                count_segwit +=1
                #Draw samples from metalog_distribution (n is number of samples and term specifies the terms of distribution to sample from)
                basedata_size_over_total_tx_size = metalog.r(m=metalog_distribution_basedata_size_over_total_tx_size_per_segwit_tx, n=1, term=5)
                basedata_size = round(tx.size * basedata_size_over_total_tx_size[0], 9)
                #print ("\n% BASEDATA SIZE: {}".format(basedata_size))
                tx.weight= basedata_size * 3 + tx.size
            else:
                #It is a legacy tx
                tx.weight= 4 * tx.size

            tx.fee= random.expovariate(1/p.Tfee)

            sender.transactionsPool.append(tx)
            FullTransaction.transaction_prop(tx)

        print ("\nPERCENTAGE SEGWIT TX POOL: {}".format(count_segwit/Psize))

    # Transaction propogation & preparing pending lists for miners
    def transaction_prop(tx):
        # Fill each pending list. This is for transaction propogation
        for i in p.NODES:
            if tx.sender != i.id:
                t= copy.deepcopy(tx)
                t.timestamp[1] = t.timestamp[1] + Network.tx_prop_delay() # transaction propogation delay in seconds
                i.transactionsPool.append(t)

    def sortFunctionSegWit(p):
        return 4 * p.fee / p.weight

    def sortFunctionLegacy(p):
        return p.fee / p.size

    def execute_transactions(miner,currentTime,IsSegWitNode):
    
        transactions= [] # prepare a list of transactions to be included in the block
        size = LightTransaction.static_block_header_size # to store the total block size (in MB)
        count=0 # to scan txs in the pool
        block_propagation_time = 0 # to store the estimated block progation delay (in seconds)

        if IsSegWitNode == True:

            weight = 0 # to store the total block weight (in Million Weight Units)
            count_segwit = 0 #to count the number of segwit txs in the block
            count_legacy = 0 #to count the number of legacy txs in the block
            block_weight = p.Bweight # the average block weight to match (in Million Weight Units)

            miner.transactionsPool.sort(key=FullTransaction.sortFunctionSegWit, reverse=True)
            pool= miner.transactionsPool

            while count < len(pool):
                if  (block_weight >= pool[count].weight and pool[count].timestamp[1] <= currentTime):
                    block_weight -= pool[count].weight
                    transactions += [pool[count]]
                    size += pool[count].size
                    weight += pool[count].weight
                    if pool[count].weight < 4 * pool[count].size:
                        count_segwit+=1
                        #print ("\nCOUNT: {} - SEGWIT".format((count_segwit)))
                    else:
                        count_legacy+=1
                        #print ("\nCOUNT: {} - LEGACY".format((count_legacy)))
                count+=1

            print ("\nPERCENTAGE SEGWIT TX BLOCK: {}".format((count_segwit/(count_segwit + count_legacy))))
            block_propagation_time = FullTransaction.estimate_block_propagation_time(size)
            return transactions, size, weight, block_propagation_time

        blocksize = p.Bsize

        miner.transactionsPool.sort(key=FullTransaction.sortFunctionLegacy, reverse=True)
        pool= miner.transactionsPool

        while count < len(pool):
            if  (blocksize >= pool[count].size and pool[count].timestamp[1] <= currentTime):
                blocksize -= pool[count].size
                transactions += [pool[count]]
                size += pool[count].size
            count+=1

        block_propagation_time = LightTransaction.estimate_block_propagation_time(size)
        return transactions, size, 0, block_propagation_time
