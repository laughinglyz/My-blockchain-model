from flask import Flask, jsonify, request
import mysql.connector
import json

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="king125001",
    database="nodes",
    auth_plugin='mysql_native_password'
)
mycursor = mydb.cursor()

sql = "SELECT  COUNT(*) FROM allnodes"
mycursor.execute(sql)
nodeno = mycursor.fetchone()[0]


app = Flask(__name__)

block = None
NoofReceiver = 0



@app.route('/getblock', methods=['GET'])
def resend_block():
   global block, NoofReceiver
   if block:
      NoofReceiver += 1
      block2=block
      if nodeno==NoofReceiver:
         NoofReceiver=0
         block=None
      return jsonify(block2), 200
   else:
      return "No block inside",204


@app.route('/minedblock', methods=['POST'])
def store_block():
   global block, NoofReceiver
   if block:
      NoofReceiver += 1
      block2=block
      if nodeno==NoofReceiver:
         NoofReceiver=0
         block=None
      return jsonify(block2), 200
   else:
      block = request.get_json()
      NoofReceiver += 1
      return "You are the miner",204


if __name__ == '__main__':
   app.run(host='0.0.0.0', port=4999)
