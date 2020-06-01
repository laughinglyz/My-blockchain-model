import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import mysql.connector

from collections import OrderedDict

import requests
from flask import Flask, jsonify, request

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="blockchain2",
    auth_plugin='mysql_native_password'
)


mycursor = mydb.cursor()


class Blockchain:
    def __init__(self,str):
        self.indentification= str
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        sql = """
        SELECT
	        COUNT(*)
        FROM
	        blocks
        """
        mycursor.execute(sql)
        length = mycursor.fetchone()

        self.chainlength = int(length[0])

        # Create the genesis block

    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """
        parsed_url = urlparse(address)
        if parsed_url.netloc:

            sql = """
            INSERT INTO neighbors
            VALUES('%s')
            """ % parsed_url.netloc

            mycursor.execute(sql)
            mydb.commit()
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            sql = """
            INSERT INTO neighbors
            VALUES('%s')
            """ % parsed_url.path

            mycursor.execute(sql)
            mydb.commit()
        else:
            raise ValueError('Invalid URL')

    def valid_block(self, block, rewarded):
        """
        Determine if a given block is valid to insert

        :param chain: A block
        :return: True if valid, False if not
        """
        if rewarded:
            if self.current_transactions[:-1] != block['transactions'][:-1]:
                return False
        else:
            if self.current_transactions != block['transactions'][:-1]:
                return False

        last_block = self.last_block
        last_block_hash = self.hash(last_block)

        if block['previous_hash'] != last_block_hash:
            return False
        
        if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

        return True 

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """
        self.chain = []
        sql = "SELECT * FROM blocks"
        mycursor.execute(sql)
        blocks = mycursor.fetchall()
        for row in blocks:
            block = {
                'index': int(row[0]),
                'timestamp': float(row[1]),
                'transactions': json.loads(row[4]),
                'proof': int(row[2]),
                'previous_hash': row[3],
            }
            self.chain.append(block)
        self.nodes = set()
        sql = "SELECT * FROM neighbors"
        mycursor.execute(sql)
        nodenet = mycursor.fetchall()
        for x in nodenet:
            self.nodes.add(x[0])

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = self.chainlength

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            self.chainlength = max_length
            sql = """
            DELETE FROM blocks
            """
            mycursor.execute(sql)
            mydb.commit()

            for i in self.chain:

                data2 = json.dumps(i['transactions'])

                sql = """
                INSERT INTO blocks(I, TS, proof, previous_hash, data)
                VALUES(%s, %s, %s, %s, %s)
                """

                val = (i['index'], str(i['timestamp']),
                       str(i['proof']), i['previous_hash'], data2)

                mycursor.execute(sql, val)
                mydb.commit()

            return True

        return False

    def new_block(self, block):
        """
        Create a new Block in the Blockchain

        :param block: Block to be inserted
        :return: New Block
        """

        data2 = json.dumps(block['transactions'])

        sql = """
        INSERT INTO blocks(I, TS, proof, previous_hash, data)
        VALUES(%s, %s, %s, %s, %s)
        """

        val = (block['index'], str(block['timestamp']),
               str(block['proof']), block['previous_hash'], data2)

        mycursor.execute(sql, val)
        mydb.commit()

        # Reset the current list of transactions
        self.current_transactions = []
        self.chainlength += 1
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """

        ntransaction=OrderedDict([('sender',sender),('recipient',recipient),('amount',amount)])

        self.current_transactions.append(ntransaction)

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        sql = """
        SELECT
	        * 
        FROM
	        blocks 
        WHERE
	        I = ( SELECT MAX( B2.I ) FROM blocks B2 )
        """
        mycursor.execute(sql)
        LB = mycursor.fetchone()
        block = {
            'index': int(LB[0]),
            'timestamp': float(LB[1]),
            'transactions': json.loads(LB[4]),
            'proof': int(LB[2]),
            'previous_hash': LB[3],
        }
        return block

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof

        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)
        block = None

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1
            if proof % 100 == 0:
                url = "http://127.0.0.1:4999/getblock"
                response = requests.get(url)

                if response.status_code == 200:
                    block = json.loads(response.text)
                    return (block, proof)

        return (block, proof)

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.

        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')
print(node_identifier)
# Instantiate the Blockchain
blockchain = Blockchain(node_identifier)


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    combination = blockchain.proof_of_work(last_block)
    rewarded = 0
    if combination[0]:
        if blockchain.valid_block(combination[0], rewarded):
            block = blockchain.new_block(combination[0])
            response = {
                'message': "New Block Created by other nodes1",
                'index': block['index'],
                'transactions': block['transactions'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                'ts': block['timestamp']
            }
            return jsonify(response), 200
        else:
            return "Warning: someone is cheating!", 500
    else:
        # We must receive a reward for finding the proof.
        # The sender is "0" to signify that this node has mined a new coin.
        blockchain.new_transaction(
            sender="0",
            recipient=node_identifier,
            amount=1,
        )
        rewarded = 1
        # Forge the new Block by adding it to the chain
        previous_hash = blockchain.hash(last_block)
        block = {
            'index': blockchain.chainlength + 1,
            'timestamp': time(),
            'transactions': blockchain.current_transactions,
            'proof': combination[1],
            'previous_hash': previous_hash,
        }

        url = "http://127.0.0.1:4999/minedblock"
        rp = requests.post(url, json=block)

        if rp.status_code == 200:
            if blockchain.valid_block(combination[0], rewarded)  :
                block = blockchain.new_block(json.loads(rp.text))
                response = {
                    'message': "New Block Created by other nodes",
                    'index': block['index'],
                    'transactions': block['transactions'],
                    'proof': block['proof'],
                    'previous_hash': block['previous_hash'],
                    'ts': block['timestamp']
                }
                return jsonify(response), 200
            else:
                return "Warning: someone is cheating!", 500
        else:
            block = blockchain.new_block(block)
            response = {
                'message': "New Block Forged",
                'index': block['index'],
                'transactions': block['transactions'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                'ts': block['timestamp']
            }
            return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(
        values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    blockchain.chain = []
    sql = "SELECT * FROM blocks"
    mycursor.execute(sql)
    blocks = mycursor.fetchall()
    for row in blocks:
        block = {
            'index': int(row[0]),
            'timestamp': float(row[1]),
            'transactions': json.loads(row[4]),
            'proof': int(row[2]),
            'previous_hash': row[3],
        }
        blockchain.chain.append(block)
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    blockchain.nodes = set()
    sql = "SELECT * FROM neighbors"
    mycursor.execute(sql)
    nodenet = mycursor.fetchall()
    for x in nodenet:
        blockchain.nodes.add(x)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000,
                        type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port, threaded=True)
