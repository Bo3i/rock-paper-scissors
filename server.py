import pika
import threading

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

stop_event = threading.Event()
sessions = {}

class Consumer(threading.Thread):
    def __init__(self, queue_name, host, callback, stop_event):
        super().__init__()
        self.queue_name = queue_name
        self.stop_event = stop_event
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue_name)
        self.callback = callback

    def run(self):

        while not self.stop_event.is_set():
            method_frame, header_frame, body = self.channel.basic_get(self.queue_name)
            if method_frame:
                print(f"Received message: {body}")
                self.channel.basic_ack(method_frame.delivery_tag)
                self.callback(self.channel, method_frame, header_frame, body)
            # else:
            #     time.sleep(1)

    def stop(self):
        self.stop_event.set()
        self.connection.close()


def remove_disconected(ch, method, properties, body):
    print('Removing disconected')


def callback(ch, method, properties, body):
    message = body.decode()
    print("Received:", message)
    #ch.basic_ack(delivery_tag=method.delivery_tag)

    session_id, player_name = message.split(',')
    channel.queue_declare(queue=f"q{player_name}{session_id}status")

    if session_id in sessions:
        if len(sessions[session_id]) < 2:
            sessions[session_id].append(player_name)
            if sessions[session_id][0] == player_name:
                p_id = 0
            else:
                p_id = 1
            channel.basic_publish(exchange='',
                                  routing_key=f"q{player_name}{session_id}status",
                                  body=f'o,{p_id}')
            Consumer(f'q{player_name}{session_id}{p_id}exit', 'localhost', remove_disconected, stop_event).start()



        else:
            print("Session is full")
            channel.basic_publish(exchange='',
                                  routing_key=f"q{player_name}{session_id}status",
                                  body='f')
    else:
        sessions[session_id] = [player_name]
        # channel.basic_publish(exchange='',
        #                       routing_key=f"q{player_name}{session_id}status",
        #                       body='0')
        channel.basic_publish(exchange='',
                              routing_key=f"q{player_name}{session_id}status",
                              body=f'o,0')
        Consumer(f'q{player_name}{session_id}0exit', 'localhost', remove_disconected, stop_event).start()

    if len(sessions[session_id]) == 2:
        print("Session", session_id, "is ready with players:", sessions[session_id])
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
            print(f"Sent {opponent},{p_id} to q{player}")
        start_game(session_id, [0, 0])


def start_game(session_id, score):
    print("Starting new round")
    player1_move, player2_move = '', ''
    recieved = [0, 0]
    print("Waiting for players")
    print(f"recieved: {recieved}")

    def recieve1(ch, method, properties, body):
        nonlocal player1_move, recieved
        player1_move = body.decode()
        print(f"Recieved {player1_move} form player {player1_name}")
        #ch.basic_ack(delivery_tag=method.delivery_tag)
        recieved[0] += 1
        if recieved[0] == recieved[1] and recieved[0]+recieved[1] != 0:
            #print(f"Recieved: {recieved}")
            print('Now checking the winner')
            play()
        else:
            print('Waiting for all to respond')
            #print(f"Recieved: {recieved}")

    def recieve2(ch, method, properties, body):
        nonlocal player2_move, recieved
        player2_move = body.decode()
        print(f"Recieved {player2_move} form player {player2_name}")
        #ch.basic_ack(delivery_tag=method.delivery_tag)
        recieved[1] += 1
        if recieved[0] == recieved[1] and recieved[0]+recieved[1] != 0:
            #print(f"Recieved: {recieved}")
            print('Checking the winner')
            play()
        else:
            print('Waiting for all to respond')
            #print(f"Recieved: {recieved}")

    player1_name = sessions[session_id][0]
    player2_name = sessions[session_id][1]
    channel.queue_declare(f"q{player1_name}{session_id}0choice")
    channel.queue_declare(f"q{player2_name}{session_id}1choice")

    channel.basic_consume(queue=f"q{player1_name}{session_id}0choice", on_message_callback=recieve1, auto_ack=True)
    channel.basic_consume(queue=f"q{player2_name}{session_id}1choice", on_message_callback=recieve2, auto_ack=True)

    def play():
        if player1_move != '' and player2_move != '':
            if player1_move == player2_move:
                score[0] += 1
                score[1] += 1
                winner = "Tie"
            elif (player1_move == "r" and player2_move == "s") or \
                    (player1_move == "p" and player2_move == "r") or \
                    (player1_move == "s" and player2_move == "p"):
                winner = player1_name
                score[0] += 1
            else:
                winner = player2_name
                score[1] += 1
            print(f"Player {winner} won!")

            player1_queue = f'q{player1_name}0won'
            player2_queue = f'q{player2_name}1won'

            channel.queue_declare(queue=player1_queue)
            channel.queue_declare(queue=player2_queue)

            print(f'queue1: {player1_queue}')
            print(f'queue2: {player2_queue}')

            channel.basic_publish(
                exchange='',
                routing_key=player1_queue,
                body=f"{winner}, {player2_move}, {score[0]}, {score[1]}"
            )
            channel.basic_publish(
                exchange='',
                routing_key=player2_queue,
                body=f"{winner}, {player1_move}, {score[1]}, {score[0]}"
            )
            print("Starting new round")
            start_game(session_id, score)
        else:
            print("------------")
            print("Wrong input!")
            print(f"Player1: {player1_move}")
            print(f"Player2: {player2_move}")


result = channel.queue_declare(queue='start', exclusive=False)
queue_name = result.method.queue
# channel.queue_bind(exchange='amq.direct', queue=queue_name)

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

print("Server is waiting for players...")
channel.start_consuming()
