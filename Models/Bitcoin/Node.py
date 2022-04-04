from Models.Block import Block
from Models.Node import Node as BaseNode

class Node(BaseNode):
    def __init__(self,id,hashPower,isSegWitNode):
        '''Initialize a new miner named name with hashrate measured in hashes per second.'''
        super().__init__(id)#,blockchain,transactionsPool,blocks,balance)
        self.hashPower = hashPower
        self.isSegWitNode = isSegWitNode #whether the node is a SegWit-compliant node (True) or not (False).
        self.blockchain= []# create an array for each miner to store chain state locally
        self.transactionsPool= []
        self.blocks= 0# total number of blocks mined in the main chain
        self.balance= 0# to count all reward that a miner made, including block rewards + uncle rewards + transactions fees
        
