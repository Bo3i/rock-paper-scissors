import random

import pika

def play():
    print('Welcome to simple online "ROCK PAPER SCISSORS" game!')
    host = input('Connect to host, for localhost press enter: ')
    if host == "":
        host = 'localhost'
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        channel = connection.channel()
        print(f'Successfully connected to: {host}')
    except:
        print('Cannot connect to host!')
        exit()

    def on_response(ch, method, properties, body):
        resp, p_id = body.decode().split(",")
        print(f"Playing against: {resp}!")
        channel.queue_declare(queue=f"{player_name}{session_id}{p_id}")
        channel.queue_declare(queue=f"{player_name}{p_id}won")
        def play_round():
            print('Please enter "r" for rock "p" for paper and "s" for scissors')
            player_input = input("Your choice: ")
            channel.basic_publish(exchange='',
                                  routing_key=f"{player_name}{session_id}{p_id}",
                                  body=player_input)

            def winner(ch, method, properties, body):
                win, mov, y_score, op_score = body.decode().split(",")
                print(f"{resp} chose: {mov}")
                if win == "Tie":
                    print("It's a tie!")
                elif win == resp:
                    print(f"{win} wins!")
                else:
                    print("You win!")
                print(f"---Score--- \nYou  {y_score} : {op_score}  {resp}")
                play_again = input('Do you want to play again? y/n: ')
                if play_again == 'n':
                    connection.close()
                    print("Exiting... Goodbye!")
                    exit()
                else:
                    play_round()

            channel.basic_consume(queue=f"{player_name}{p_id}won", on_message_callback=winner, auto_ack=True)
        play_round()

    player_name = input('Set your name: ')
    if player_name == '': player_name = input('Name cannot be null! ')
    session_id = input('Connect to session: ')
    if session_id == '':
        print('You have to provide session id! Now exiting....')
        exit()

    channel.queue_declare(queue='start')
    channel.basic_publish(exchange='',
                          routing_key='start',
                          body=f"{session_id},{player_name}")
    channel.queue_declare(queue=player_name)
    channel.basic_consume(queue=player_name, on_message_callback=on_response, auto_ack=True)
    print("Message to server sent")

    print("Waiting for response...")
    channel.start_consuming()


play()
