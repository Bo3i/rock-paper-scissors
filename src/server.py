import sys

import pika
import threading
import signal
import q_consumer as c

# Connection to the RabbitMQ server
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Declaring the session and score dictionaries
stop_event = threading.Event()
consumers = []
sessions = {}
scores = {}


# Function to remove disconnected players
def remove_disconected(ch, method, properties, body):
    message = body.decode()
    p_id_r, s_id = message.split(',')
    if len(sessions[s_id]) != 0:
        print(f'Removing disconnected players. Session: {s_id} is now empty')

        sessions[s_id].pop(int(p_id_r))
        scores[s_id] = [0, 0]
        if len(sessions[s_id]) == 1:
            channel.basic_publish(
                exchange='',

                routing_key=f'q{sessions[s_id][0]}{s_id}ex',
                body='0'
            )
        sessions[s_id] = []


# Callback function to handle the incoming messages
def callback(ch, method, properties, body):
    message = body.decode()
    session_id, player_name = message.split(',')
    print(f"Received Session ID: {session_id} from player: {player_name }")
    channel.queue_declare(queue=f"q{player_name}{session_id}status")
    join_player(session_id, player_name)
    start_session(session_id)


# Function to start the session
def start_session(session_id):

    if len(sessions[session_id]) == 2:
        print("Session", session_id, "is ready with players:", sessions[session_id], f'and score: {scores[session_id]}')
        for player in sessions[session_id]:
            if sessions[session_id][0] == player:
                opponent = sessions[session_id][1]
                p_id = 0
            else:
                opponent = sessions[session_id][0]
                p_id = 1
            channel.queue_declare(queue=f"q{player}{session_id}{p_id}")
            channel.queue_declare(queue=f"q{player}{p_id}won")
            channel.basic_publish(exchange='',
                                  routing_key=f"q{player}{session_id}{p_id}",
                                  body=f"{opponent},{p_id}")
        start_game(session_id)


# Function to join the player to the session
def join_player(session_id, player_name):
    if session_id in sessions:
        scores[session_id] = [0, 0]
        if len(sessions[session_id]) < 2:
            sessions[session_id].append(player_name)
            if sessions[session_id][0] == player_name:
                p_id = 0
            else:
                p_id = 1
            channel.basic_publish(exchange='',
                                  routing_key=f"q{player_name}{session_id}status",
                                  body=f'o,{p_id}')
            exit_consumer = c.Consumer(f'q{player_name}{session_id}{p_id}exit', 'localhost', remove_disconected, stop_event)
            exit_consumer.start()
            consumers.append(exit_consumer)

        else:
            print(f"Session: {session_id} is full, denied connection to player: {player_name}")
            channel.basic_publish(exchange='',
                                  routing_key=f"q{player_name}{session_id}status",
                                  body='f,0')
    else:
        sessions[session_id] = [player_name]
        scores[session_id] = [0, 0]
        channel.basic_publish(exchange='',
                              routing_key=f"q{player_name}{session_id}status",
                              body=f'o,0')
        exit_consumer = c.Consumer(f'q{player_name}{session_id}0exit', 'localhost', remove_disconected, stop_event)
        exit_consumer.start()
        consumers.append(exit_consumer)


# Function to start the game in the session
def start_game(session_id):
    global channel
    if len(sessions[session_id]) != 2:
        channel.basic_publish(
            exchange='',
            routing_key=f'q{sessions[session_id][0]}{session_id}ex',
            body='0'
        )
        scores[session_id] = [0, 0]
    print(f"Starting new round with score: {scores[session_id]}")
    player1_move, player2_move = '', ''
    recieved = [0, 0]
    print("Waiting for players' choices...")

    def recieve1(ch, method, properties, body):
        nonlocal player1_move, recieved
        player1_move = body.decode()
        print(f"Recieved {player1_move} from player {player1_name}")
        recieved[0] += 1
        if recieved[0] == recieved[1] and recieved[0]+recieved[1] != 0:
            play()
        else:
            print('Waiting for all to respond')

    def recieve2(ch, method, properties, body):
        nonlocal player2_move, recieved
        player2_move = body.decode()
        print(f"Recieved {player2_move} form player {player2_name}")
        recieved[1] += 1
        if recieved[0] == recieved[1] and recieved[0]+recieved[1] != 0:
            print('Checking the winner')
            play()
        else:
            print('Waiting for all to respond')

    player1_name = sessions[session_id][0]
    player2_name = sessions[session_id][1]

    channel.queue_declare(f"q{player1_name}{session_id}0choice")
    channel.queue_declare(f"q{player2_name}{session_id}1choice")

    channel.basic_consume(queue=f"q{player1_name}{session_id}0choice", on_message_callback=recieve1, auto_ack=True)
    channel.basic_consume(queue=f"q{player2_name}{session_id}1choice", on_message_callback=recieve2, auto_ack=True)

    # Function to check the winner
    def play():

        if player1_move != '' and player2_move != '':
            if player1_move == player2_move:
                scores[session_id][0] += 1
                scores[session_id][1] += 1
                winner = "Tie"
            elif (player1_move == "r" and player2_move == "s") or \
                    (player1_move == "p" and player2_move == "r") or \
                    (player1_move == "s" and player2_move == "p"):
                winner = player1_name
                scores[session_id][0] += 1
            else:
                winner = player2_name
                scores[session_id][1] += 1
            print(f"Player {winner} won!")

            player1_queue = f'q{player1_name}0won'
            player2_queue = f'q{player2_name}1won'

            channel.queue_declare(queue=player1_queue)
            channel.queue_declare(queue=player2_queue)

            print(f'score: {scores[session_id]}')

            channel.basic_publish(
                exchange='',
                routing_key=player1_queue,
                body=f"{winner}, {player2_move}, {scores[session_id][0]}, {scores[session_id][1]}"
            )
            channel.basic_publish(
                exchange='',
                routing_key=player2_queue,
                body=f"{winner}, {player1_move}, {scores[session_id][1]}, {scores[session_id][0]}"
            )
            rec = [0, 0]

            def new_round(ch, method, properties, body):
                p_id = body.decode()
                rec[int(p_id)] = 1
                if len(sessions[session_id]) == 2:
                    if rec[0] + rec[1] == 2:
                        print('Starting new session')
                        start_game(session_id)
            channel.queue_declare(queue=f'q{player1_name}{session_id}0ready')
            channel.queue_declare(queue=f'q{player2_name}{session_id}1ready')

            channel.basic_consume(queue=f'q{player1_name}{session_id}0ready', on_message_callback=new_round, auto_ack=True)
            channel.basic_consume(queue=f'q{player2_name}{session_id}1ready', on_message_callback=new_round, auto_ack=True)

        else:
            print("Wrong input!")


# Function to handle keyboard interruption
def signal_handler(sig, frame):
    print('Keyboard interrupt received, stopping consumers...')
    stop_event.set()
    for consumer in consumers:
        if consumer.is_alive():
            consumer.stop()
    for consumer in consumers:
        consumer.join()
    print('All consumers have been stopped.')
    sys.exit()


signal.signal(signal.SIGINT, signal_handler)

# Declaring the queue
result = channel.queue_declare(queue='start', exclusive=False)
queue_name = result.method.queue

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

print("Server is waiting for players...")
channel.start_consuming()
