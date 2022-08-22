import random
from InputsConfig import InputsConfig as p
import numpy as np
import Models.Network
import operator
from scipy.stats import bernoulli
from metalog import metalog
import pandas as pd
from datetime import datetime
import math
import xlsxwriter

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

    #block mining rate (unit: second)
    mu = 1 / p.Binterval

    #Block Generation Rate
    lamda = 1049 / p.Binterval

    def estimate_block_propagation_time(block_size):

        estimated_block_propagation_time = LightTransaction.m * block_size + LightTransaction.q
        return estimated_block_propagation_time

    def expected_reward(block_reward_from_fees, block_size):

        block_total_reward = block_reward_from_fees + p.Breward

        block_propagation_time = LightTransaction.estimate_block_propagation_time(block_size)

        exponent = LightTransaction.mu * block_propagation_time

        p_block_not_orphan = 1 / math.exp(exponent)

        expected_reward = p_block_not_orphan * block_total_reward

        return expected_reward

    def compute_success_probability(overhead_time, evil_block_size, reference_block_size):

        #Estimate propagation time of current evil block
        evil_block_prop_time = LightTransaction.estimate_block_propagation_time(evil_block_size)
        #print("prop. time EVIL: {}".format(evil_block_prop_time))

        #Estimate propagation time of reference block
        reference_block_prop_time = LightTransaction.estimate_block_propagation_time(reference_block_size)
        #print("prop. time REFERNCE: {}".format(reference_block_prop_time))

        second_term = (1 / LightTransaction.lamda) * (reference_block_prop_time / evil_block_prop_time)
        #print("second_term: {}".format(second_term))

        if ((second_term - overhead_time) / overhead_time) > p.threshold_value:
            #print("Variazione perc. corrente: {}".format(((second_term - overhead_time) / overhead_time)))
            #print("Variazione perc. soglia: {}".format(p.threshold_value))
            #print("Maggiore!!")
            return True

        #print("Minore!!")
        return False

    def block_statistics(filename, transactions_list):
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()
        worksheet.write(0, 0, "TXs Count")
        worksheet.write(0, 1, "TX Size")
        worksheet.write(0, 2, "TX Fee")
        worksheet.write(0, 3, "Expected Reward")

        if len(transactions_list) == 0:
            worksheet.write(1, 0, 0)
            worksheet.write(1, 1, 0)
            worksheet.write(1, 2, 0)
            worksheet.write(1, 3, 0)
            workbook.close()
        else:
            worksheet.write(1, 0, len(transactions_list))
            counter = 0
            block_reward_from_fees = 0
            block_size = LightTransaction.static_block_header_size
            expected_reward = 0

            while counter < len(transactions_list):
                block_reward_from_fees += transactions_list[counter].fee
                block_size += transactions_list[counter].size
                expected_reward = LightTransaction.expected_reward(block_reward_from_fees, block_size)
                worksheet.write(1 + counter, 1, transactions_list[counter].size)
                worksheet.write(1 + counter, 2, transactions_list[counter].fee)
                worksheet.write(1 + counter, 3, expected_reward)
                counter+=1
            
            workbook.close()

    def create_transactions(simulation_folder_reference_txs_timestamp, run_id, block_count):

        LightTransaction.pending_transactions=[]
        pool= LightTransaction.pending_transactions
        Psize= int(p.Tblock)

        if run_id % 2 == 0:
            txs_filename = simulation_folder_reference_txs_timestamp + "/txs_" + str(run_id) + "_" + str(block_count) + '_.xlsx'
            workbook = xlsxwriter.Workbook(txs_filename)
            worksheet = workbook.add_worksheet()
        else:
            prev_run_id = run_id - 1
            txs_filename = simulation_folder_reference_txs_timestamp + "/txs_" + str(prev_run_id) + "_" + str(block_count) + '_.xlsx'

            df = pd.read_excel(txs_filename, engine="openpyxl", index_col=None, na_values=['NA'])
            tx_ids = df["TX_ID"].tolist()
            tx_senders = df["TX_SENDER"].tolist()
            tx_tos = df["TX_TO"].tolist()
            tx_sizes = df["TX_SIZE"].tolist()
            tx_weight = df["TX_WEIGHT"].tolist()
            tx_fees = df["TX_FEE"].tolist()

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

            if run_id % 2 == 0:
                if i == 0:
                    #print ("\n========== REFERENCE APPROACH ==========")
                    worksheet.write(i, 0, "TX_ID")
                    worksheet.write(i, 1, "TX_SENDER")
                    worksheet.write(i, 2, "TX_TO")
                    worksheet.write(i, 3, "TX_SIZE")
                    worksheet.write(i, 4, "TX_WEIGHT")
                    worksheet.write(i, 5, "TX_FEE")


                tx.id= random.randrange(100000000000)
                worksheet.write(i + 1, 0, tx.id)

                tx.sender = random.choice (p.NODES).id
                worksheet.write(i + 1, 1, tx.sender)

                tx.to= random.choice (p.NODES).id
                worksheet.write(i + 1, 2, tx.to)

                tx.size= random.expovariate(1/p.Tsize)
                worksheet.write(i + 1, 3, tx.size)
                

                r = bernoulli.rvs(segwit_txs_over_total_txs)
                #print ("\nBERNOULLI RV: {}".format(r))
                if r == 1:
                    #It is a segwit tx
                    #count_segwit +=1
                    #Draw samples from metalog_distribution (n is number of samples and term specifies the terms of distribution to sample from)
                    basedata_size_over_total_tx_size = metalog.r(m=metalog_distribution_basedata_size_over_total_tx_size_per_segwit_tx, n=1, term=5)
                    basedata_size = round(tx.size * basedata_size_over_total_tx_size[0], 9)
                    #print ("\n% BASEDATA SIZE: {}".format(basedata_size))
                    tx.weight= basedata_size * 3 + tx.size
                    if tx.weight < 4 * tx.size:
                        count_segwit +=1
                    worksheet.write(i + 1, 4, tx.weight)
                    #print ("{}\t{}".format(tx.size, tx.weight))
                else:
                    #It is a legacy tx
                    tx.weight= 4 * tx.size
                    worksheet.write(i + 1, 4, tx.weight)
                    #print ("{}\t{}".format(tx.size, tx.weight))

                tx.fee= random.expovariate(1/p.Tfee)
                worksheet.write(i + 1, 5, tx.fee)
            else:
                #if i == 0:
                #    print ("\n========== EVIL APPROACH ==========")
                tx.id= tx_ids[i]
                tx.sender = tx_senders[i]
                tx.to= tx_tos[i]
                tx.size = tx_sizes[i]
                tx.weight = tx_weight[i]
                if tx.weight < 4 * tx.size:
                    count_segwit +=1
                tx.fee= tx_fees[i]

            pool += [tx]

        #print ("\nPERCENTAGE SEGWIT TX POOL: {}".format(count_segwit/Psize))
        #print ("\nSEGWIT TX POOL: {}".format(count_segwit))

        if run_id % 2 == 0:
            workbook.close()

        random.shuffle(pool)


    ##### Select and execute a number of transactions to be added in the next block #####
    def execute_transactions(simulation_folder_reference_txs_timestamp, run_id, block_count, minerId, is_evil_block):
        transactions= [] # prepare a list of transactions to be included in the block
        size = LightTransaction.static_block_header_size # to store the total block size (in MB)
        weight = 0 # to store the total block weight (in Million Weight Units)
        count=0 # to scan txs in the pool
        count_segwit = 0
        count_legacy = 0
        block_weight = p.Bweight # the average block weight to match (in Million Weight Units)
        block_propagation_time = 0 # to store the estimated block progation delay (in seconds)
        pool= LightTransaction.pending_transactions

        pool = sorted(pool, key=lambda x: 4 * x.fee/x.weight, reverse=True) # sort pending transactions in the pool based on the gasPrice value

        #print ("\nRUN ID: {}".format(run_id))
        #print ("\nIS EVIL BLOCK: {}".format(is_evil_block))

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

        #print ("\nPERCENTAGE SEGWIT TX BLOCK: {}".format((count_segwit/(count_segwit + count_legacy))))

        if (run_id % 2 == 0):
            stats_filename = simulation_folder_reference_txs_timestamp + "/stats_" + str(run_id) + "_" + str(block_count) + "_" + str(minerId) + '_.xlsx'
            LightTransaction.block_statistics(stats_filename, transactions)
            block_propagation_time = LightTransaction.estimate_block_propagation_time(size)
            return transactions, size, weight, block_propagation_time
        elif (run_id % 2 != 0 and is_evil_block == False):
            stats_filename = simulation_folder_reference_txs_timestamp + "/stats_" + str(run_id) + "_" + str(block_count) + '_reference_.xlsx'
            LightTransaction.block_statistics(stats_filename, transactions)
            block_propagation_time = LightTransaction.estimate_block_propagation_time(size)
            return transactions, size, weight, block_propagation_time
        
        ref_time = datetime.now()

        evil_transactions= [] # prepare a list of transactions to be included into the evil block
        evil_block_size = LightTransaction.static_block_header_size # to store the total evil block size (in MB)
        evil_block_weight = 0 # to store the total evil block weight (in Million Weight Units)
        count=0 # to scan txs into the reference block
        count_segwit = 0
        count_legacy = 0
        block_weight = p.Bweight # the average block weight to match (in Million Weight Units)
        evil_block_propagation_time = 0 # to store the estimated block progation delay (in seconds)

        expected_block_reward_new = 0 
        expected_block_reward_current = 0
        block_reward_from_fees = 0

        while count < len(transactions):
            if (block_weight >= transactions[count].weight):
                expected_block_reward_new = LightTransaction.expected_reward(block_reward_from_fees + transactions[count].fee, evil_block_size + transactions[count].size)
                if expected_block_reward_new >= expected_block_reward_current:
                    block_weight -= transactions[count].weight
                    evil_transactions += [transactions[count]]
                    evil_block_size += transactions[count].size
                    evil_block_weight += transactions[count].weight
                    if transactions[count].weight < 4 * transactions[count].size:
                        count_segwit+=1
                        #print ("\nCOUNT: {} - SEGWIT".format((count_segwit)))
                    else:
                        count_legacy+=1
                        #print ("\nCOUNT: {} - LEGACY".format((count_legacy)))
                    block_reward_from_fees += transactions[count].fee
                    expected_block_reward_current = expected_block_reward_new

                    overhead_time = (datetime.now() - ref_time).total_seconds()
                    #print("overhead_time: {}".format(overhead_time))
                    if LightTransaction.compute_success_probability(overhead_time, evil_block_size, size) == False:

                        print ("\nPERCENTAGE SEGWIT TX BLOCK: {}".format((count_segwit/(count_segwit + count_legacy))))

                        stats_filename = simulation_folder_reference_txs_timestamp + "/stats_" + str(run_id) + "_" + str(block_count) + '_evil_.xlsx'

                        if evil_block_size != LightTransaction.static_block_header_size:
                            LightTransaction.block_statistics(stats_filename, evil_transactions)
                            evil_block_propagation_time = LightTransaction.estimate_block_propagation_time(evil_block_size)
                            #print("ARRIVO!!!")
                            return evil_transactions, evil_block_size, evil_block_weight, evil_block_propagation_time

                        LightTransaction.block_statistics(stats_filename, transactions)
                        block_propagation_time = LightTransaction.estimate_block_propagation_time(size)
                        return transactions, size, weight, block_propagation_time
            count+=1

        print ("\nPERCENTAGE SEGWIT TX BLOCK: {}".format((count_segwit/(count_segwit + count_legacy))))
        stats_filename = simulation_folder_reference_txs_timestamp + "/stats_" + str(run_id) + "_" + str(block_count) + '_evil_.xlsx'

        if evil_block_size != LightTransaction.static_block_header_size:
            LightTransaction.block_statistics(stats_filename, evil_transactions)
            evil_block_propagation_time = LightTransaction.estimate_block_propagation_time(evil_block_size)
            #print("ARRIVO!!!")
            return evil_transactions, evil_block_size, evil_block_weight, evil_block_propagation_time

        LightTransaction.block_statistics(stats_filename, transactions)
        block_propagation_time = LightTransaction.estimate_block_propagation_time(size)
        return transactions, size, weight, block_propagation_time
        
class FullTransaction():

    def create_transactions():
        Psize= int(p.Tn * p.simTime)

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
            tx.fee= random.expovariate(1/p.Tfee)

            sender.transactionsPool.append(tx)
            FullTransaction.transaction_prop(tx)

    # Transaction propogation & preparing pending lists for miners
    def transaction_prop(tx):
        # Fill each pending list. This is for transaction propogation
        for i in p.NODES:
            if tx.sender != i.id:
                t= copy.deepcopy(tx)
                t.timestamp[1] = t.timestamp[1] + Network.tx_prop_delay() # transaction propogation delay in seconds
                i.transactionsPool.append(t)



    def execute_transactions(miner,currentTime):
        transactions= [] # prepare a list of transactions to be included in the block
        size = 0 # calculate the total block gaslimit
        count=0
        blocksize = p.Bsize
        miner.transactionsPool.sort(key=operator.attrgetter('fee'), reverse=True)
        pool= miner.transactionsPool

        while count < len(pool):
                if  (blocksize >= pool[count].size and pool[count].timestamp[1] <= currentTime):
                    blocksize -= pool[count].size
                    transactions += [pool[count]]
                    size += pool[count].size
                count+=1

        return transactions, size
