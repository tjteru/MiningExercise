from threading import Lock
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit
import requests
import ast

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

# system wide globals
user_list = [("Roger", 0, 0)]
blockchain = {}
difficulty_level = 2
transaction_count = 0
reward = 100
last_hash = 0
hash_mode = 0
block_num = 0

transaction_list = [{"source":"Roger", "dest":"Alice", "amount":10},
                    {"source":"Todd", "dest":"Alice", "amount":17},
                    {"source":"Glenn", "dest":"Todd", "amount":53},
                    {"source":"Alex", "dest":"Alice", "amount":77},
                    {"source":"Alice", "dest":"Bob", "amount":19}]

blockchain = [["0000000000", [{"source":"MINT", "dest":"Roger", "amount":200}]],
              ["50CEB696EF", [{"source":"MINT", "dest":"Roger", "amount":100}, {"source":"Roger", "dest":"Alice", "amount":10}]]]

url = 'https://api.coinbase.com/v2/prices/btc-usd/spot'

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while False: #not doing this now...
        socketio.sleep(60)
        count += 1
        price = ((requests.get(url)).json())['data']['amount']
        socketio.emit('my_response',
                      {'data': 'Bitcoin current price (USD): ' + price, 'count': count})

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode, difficulty=difficulty_level, last_hash=last_hash, reward=reward, hash_mode=hash_mode, blocknum=block_num, blockchain=blockchain)

@app.route('/control')
def control():
    return render_template('control.html', async_mode=socketio.async_mode, userlist=user_list, difficulty=difficulty_level, last_hash=last_hash, reward=reward, hash_mode=hash_mode, blocknum=block_num, blockchain=blockchain)

@app.route('/test')
def test():
    return render_template('test.html', blocknum=block_num)

@socketio.event
def my_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})

# Receive the test request from client and send back a test response
@socketio.on('test_message')
def handle_message(data):
    print('received message: ' + str(data))
    emit('test_response', {'data': 'Test response sent'})

@socketio.on('hash_message')
def handle_message(data):
    print('received hash message: ' + str(data))
    emit('hash_response', data)
    #{'data': 'Hash = ' + str(data)})

@socketio.on('valid_block_message')
def handle_message(data):
    print('received valid block message: ' + str(data))
    emit('valid_block_response', data, broadcast=True)
    foo = data['transactions'].replace('\n',"") #.strip()
    foo = foo.replace(' ',"") #.strip()
    foo = foo.replace('"',"'") #.strip()
    data['transactions'] = foo
    blockchain.append([data['data'], data['transactions']])
    #{'data': 'Hash = ' + str(data)})

# register a username
@socketio.on('name_message')
def handle_name(data):
    print('registering: ' + str(data))
    user_list.append((str(data), 0, 0))
    emit('new_user_response', {'data': len(user_list), 'name': str(data)}, broadcast=True)

# Broadcast a message to all clients
@socketio.on('broadcast_message')
def handle_broadcast(data):
    print('received broadcast_message: ' + str(data))
    emit('broadcast_response', {'data': 'Broadcast sent'}, broadcast=True)

# Broadcast a transaction to all clients
@socketio.on('transaction_message')
def handle_transaction(data):
    global transaction_list
    global transaction_count
    transaction_count = (transaction_count + 1) % len(transaction_list)
    print('received transaction_message: ' + str(data))
    print('sending new_transaction_response: ' + str(transaction_list[transaction_count]))
    emit('transaction_response', {'data': transaction_list[transaction_count]}, broadcast=True)

    #emit('transaction_response', data, broadcast=True) #str(data).replace("'",'"')}, broadcast=True)

# Broadcast a new transaction to all clients
@socketio.on('new_transaction_message')
def handle_new_transaction(data):
    global transaction_list
    global transaction_count
    transaction_count = (transaction_count + 1) % len(transaction_list)
    print('received new_transaction_message: ' + str(data))
    print('sending new_transaction_response: ' + str(transaction_list[transaction_count]))
    emit('new_transaction_response', {'data': transaction_list[transaction_count]}, broadcast=True)


# Broadcast a difficulty to all clients
@socketio.on('difficulty_message')
def handle_difficulty(data):
    global difficulty_level
    print('received difficulty_message: ' + str(data))
    difficulty_level = data['data']
    emit('difficulty_response', {'data': str(data).replace("'",'"')}, broadcast=True)

@socketio.on('reward_message')
def handle_reward(data):
    global reward
    print('received reward_message: ' + str(data))
    reward = data['data']
    emit('reward_response', {'data': str(data).replace("'",'"')}, broadcast=True)

@socketio.on('hash_mode_message')
def handle_hashmode(data):
    global hash_mode
    print('received: ' + str(data))
    hash_mode = data['data']
    emit('hash_mode_response', {'data': str(hash_mode)}, broadcast=True)

@socketio.on('do_nothing_message')
def handle_do_nothing(data):
    print('received: ' + str(data))
    emit('do_nothing_response', {'data': "nothing"}, broadcast=True)


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})

if __name__ == '__main__':
    socketio.run(app, debug=False)
