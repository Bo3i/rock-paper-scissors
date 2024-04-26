import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

sessions = {}

def callback(ch, method, properties, body):
    message = body.decode()
    print("Received:", message)

    session_id, player_name = message.split(',')

    if session_id in sessions:
        if len(sessions[session_id]) < 2:
            sessions[session_id].append(player_name)
        else:
            print("Session is full")
            #channel.basic_publish(exchange='',
            #                      routing_key=player_name,
            #                      body='#ErR!')
    else:
        sessions[session_id] = [player_name]

    if len(sessions[session_id]) == 2:
        print("Session", session_id, "is ready with players:", sessions[session_id])
        for player in sessions[session_id]:
            if sessions[session_id][0] == player:
                opponent = sessions[session_id][1]
            else:
                opponent = sessions[session_id][0]
            channel.basic_publish(exchange='',
                                  routing_key=player,
                                  body=opponent)
        start_game(session_id)


def start_game(session_id):
    player1_move, player2_move = '', ''
    recieved = [0, 0]

    def recieve1(ch, method, properties, body):
        nonlocal player1_move, recieved
        player1_move = body.decode()
        print(f"Recieved {player1_move} form player {player1_name}")
        recieved[0] += 1
        if recieved[0]+recieved[1] == 2:
            print('Now checking the winner')
            play()
        else:
            print('Waiting for all to respond')

    def recieve2(ch, method, properties, body):
        nonlocal player2_move, recieved
        player2_move = body.decode()
        print(f"Recieved {player2_move} form player {player2_name}")
        recieved[1] += 1
        if recieved[0]+recieved[1] == 2:
            print('Checking the winner')
            play()
        else:
            print('Waiting for all to respond')

    player1_name = sessions[session_id][0]
    player2_name = sessions[session_id][1]

    channel.basic_consume(queue=f"{player1_name}{session_id}", on_message_callback=recieve1, auto_ack=True)
    channel.basic_consume(queue=f"{player2_name}{session_id}", on_message_callback=recieve2, auto_ack=True)

    def play():
        if player1_move != '' and player2_move != '':
            if player1_move == player2_move:
                winner = "It's a tie!"
            elif (player1_move == "r" and player2_move == "s") or \
                    (player1_move == "p" and player2_move == "r") or \
                    (player1_move == "s" and player2_move == "p"):
                winner = player1_name
            else:
                winner = player2_name
            print(f"{winner} won!")
            channel.basic_publish(exchange='',
                                  routing_key=f"{player1_name}won",
                                  body=f"{winner}, {player2_move}")
            channel.basic_publish(exchange='',
                                  routing_key=f"{player2_name}won",
                                  body=f"{winner}, {player1_move}")
        else:
            print("------------")
            print("Wrong input!")
            print(f"Player1: {player1_move}")
            print(f"Player2: {player2_move}")


result = channel.queue_declare(queue='start', exclusive=False)
queue_name = result.method.queue
#channel.queue_bind(exchange='amq.direct', queue=queue_name)

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

print("Server is waiting for players...")
channel.start_consuming()
