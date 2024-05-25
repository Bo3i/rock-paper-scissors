import sys
import threading
import pygame
import pika
import traceback
import time
import signal
import wave
import game_components as gc

pygame.init()
pygame.mixer.init()
pygame.mixer.music.load("Atmospheric-ambient-music.wav")
pygame.mixer.music.play(-1)


# Constants
WIDTH = 800
HEIGHT = 600
WHITE = (255, 255, 255)
BACKGROUND = (245, 235, 224)
BUTTON_COLOR = (154, 154, 132)
TEXT_COLOR = (79, 79, 64)
BLACK = (0, 0, 0)
GREY = (133, 117, 110)

# Pygame setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rock Paper Scissors Game")

# Load and resize images
rock_img = pygame.image.load('rock.jpg')
rock_img = pygame.transform.scale(rock_img, (150, 150))

paper_img = pygame.image.load('paper.jpg')
paper_img = pygame.transform.scale(paper_img, (150, 150))

scissors_img = pygame.image.load('scissors.jpg')
scissors_img = pygame.transform.scale(scissors_img, (150, 150))

FONT = pygame.font.Font(None, 32)
LARGE_FONT = pygame.font.Font(None, 56)

# Globals for RabbitMQ
host = ''
player_name = ''
session_id = ''
connection = None
channel = None
opponent = ''
p_id = ''
player_input = ''
consumers = []
stop_event = threading.Event()
is_clicked = False
current_state = 'main_menu'  # Initial state


# Function to exit the game
def exit_game():
    global running



    running = False

    print("DEBUG: Exiting game")



# Function for connecting to the server
def connect():
    global host, player_name, texts, buttons, input_boxes, connection, channel, current_state
    for box in input_boxes:
        if box.text != '':
            player_name = box.text
        else:
            set_name()
    if host == '':
        host = 'localhost'
    print(f"DEBUG: Connecting to host: {host}")

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        channel = connection.channel()
        print(f'DEBUG: Successfully connected to: {host}')
        define_session()
    except Exception as e:
        print(f'ERROR: Cannot connect to host! Error: {e}')
        texts = ['Cannot connect to host!']
        buttons = [button_exit]


# Function to initialize the game
def init_game():
    global buttons, texts, input_boxes
    texts = ["Connect to host, for localhost press enter"]
    buttons = [button_sethost]
    box = gc.InputBox(300, 200, 200, 50, FONT)
    input_boxes = [box]


# Function for starting new session
def start_session():
    global input_boxes, buttons, texts, session_id, channel, connection
    for box in input_boxes:
        if box.text != '':
            session_id = box.text
        else:
            define_session()

    input_boxes = []
    buttons = []

    try:
        channel.queue_declare(queue='start')
        channel.basic_publish(exchange='',
                              routing_key='start',
                              body=f"{session_id},{player_name}")

        conn_consumer = Consumer(f"q{player_name}{session_id}status", host, on_connect, stop_event)
        conn_consumer.start()
        consumers.append(conn_consumer)

        print(f"Connecting to session: {session_id} ...")

        texts = [f"Connecting to session: {session_id} ..."]

    except Exception as e:
        print(f"ERROR: Error starting session: {e}")
        texts = ['Error starting session!']
        buttons = [button_exit]

def on_connect(ch, method, properties, body):
    global texts, buttons
    mess = body.decode()
    print(f"recieved: {mess}")
    if mess == "0":
        conn_consumer = Consumer(f'q{player_name}', host, on_response, stop_event)
        conn_consumer.start()
        consumers.append(conn_consumer)
        texts = ["Waiting for other player..."]
    elif mess == "1":
        texts = [f"Session: {session_id} is full"]
        buttons = [button_menu]

# Function for handling server response
def on_response(ch, method, properties, body):
    global opponent, p_id, player_name, channel, current_state
    try:
        opponent, p_id = body.decode().split(",")
        print(f"DEBUG: Playing against: {opponent}!")

        channel.queue_declare(queue=f"q{player_name}{session_id}{p_id}")
        channel.queue_declare(queue=f"q{player_name}{p_id}won")

        start_game()
    except Exception as e:
        print(f"ERROR: Error in response: {e}")
        texts = ['Error in response!']
        buttons = [button_exit]


def winner(ch, method, properties, body):
    global connection, channel, texts, buttons, screen, opponent, current_state, your_s, their_s, is_clicked
    print("recieved result from server")
    try:
        win, mov, y_score, op_score = body.decode().split(",")
        your_s = y_score
        their_s = op_score
        print(f"DEBUG: {opponent} chose: {mov}")
        print(mov)
        if win == 'Tie':
            print("DEBUG: It's a tie!")
            texts = [f"It's a tie!", f"Score: You {y_score} : {op_score} {opponent}", "Do you want to play again?"]
        elif win == opponent:
            print(f"DEBUG: {win} wins!")
            texts = [f"{win} wins!", f"Score: You {y_score} : {op_score} {opponent}", "Do you want to play again?"]
        else:
            print("DEBUG: You win!")
            texts = ["You win!", f"Score: You {y_score} : {op_score} {opponent}", "Do you want to play again?"]
        screen.fill(BACKGROUND)
        button_menu.rect.x = 125
        button_no.rect.x = 325
        button_yes.rect.x = 525
        button_menu.rect.y = 500
        button_no.rect.y = 500
        button_yes.rect.y = 500
        buttons = [button_yes, button_menu]
        current_state = 'end_round'
        is_clicked = False
        main()
    except Exception as e:
        print(f"ERROR: Error in winner callback: {e},{traceback.format_exc()}")


def endof_round():
    global current_state, connection
    try:
        connection.close()
        print("DEBUG: Exiting... Goodbye!")
        pygame.quit()
        sys.exit()
    except:
        pygame.quit()
        sys.exit()


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


def consume_from_queue(queue_name, callback):
    global connection, channel
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.queue_declare(queue=queue_name)
    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    channel.start_consuming()

def send_input():
    global connection, player_input, opponent, texts, buttons, channel, is_clicked
    try:
        if is_clicked:
            input_consumer = Consumer(f"q{player_name}{p_id}won", host, winner, stop_event)
            input_consumer.start()
            consumers.append(input_consumer)
            channel.basic_publish(exchange='',
                                  routing_key=f"q{player_name}{session_id}{p_id}",
                                  body=player_input)

    except Exception as e:
        print(f"ERROR: Error in send_input: {e}")


# Starting game
def start_game():
    global buttons, texts, current_state, is_clicked, opponent, your_s, their_s
    print("DEBUG: Entering start_game function")
    texts = [f"You {your_s} : {their_s} {opponent}"]
    button_exit.rect.x = 200
    button_exit.rect.y = 450
    button_menu.rect.x = 400
    button_menu.rect.y = 450
    buttons = [rock_button, paper_button, scissors_button, button_exit, button_menu]
    current_state = 'game'
    main()


# Functions for handling player choices
def on_rock():
    global player_input, is_clicked
    player_input = 'r'
    print("DEBUG: Player chose rock")
    is_clicked = True
    send_input()


def on_paper():
    global player_input, is_clicked
    player_input = 'p'
    print("DEBUG: Player chose paper")
    is_clicked = True
    send_input()


def on_scissors():
    global player_input, is_clicked
    player_input = 's'
    print("DEBUG: Player chose scissors")
    is_clicked = True
    send_input()


# Function to define a session
def define_session():
    global input_boxes, buttons, texts
    buttons = [button_session]
    texts = ["Connect to session:"]
    box = gc.InputBox(300, 200, 200, 50, FONT)
    input_boxes = [box]
    main()


# Function to set player name
def set_name():
    global host, texts, buttons, input_boxes
    for box in input_boxes:
        host = box.text

    texts = ["What's your name?"]
    buttons = [button_name]
    box = gc.InputBox(300, 200, 200, 50, FONT)
    input_boxes = [box]
    main()


def menu():
    global connection, texts, buttons, input_boxes

    texts = ["Rock Paper Scissors"]
    button_exit.rect.x = WIDTH/2
    button_exit.rect.y = 200
    buttons = [button_start, button_exit]
    input_boxes = []
    main()


# Create buttons
button_start = gc.Button(WIDTH / 4, 200, 150, 50, "Start", FONT, BUTTON_COLOR, GREY, init_game)
button_exit = gc.Button(WIDTH / 2, 200, 150, 50, "Exit", FONT, BUTTON_COLOR, GREY, exit_game)
rock_button = gc.ImageButton(100, 250, rock_img, on_rock)
paper_button = gc.ImageButton(325, 250, paper_img, on_paper)
scissors_button = gc.ImageButton(550, 250, scissors_img, on_scissors)
button_sethost = gc.Button(350, 300, 100, 50, "Ok", FONT, BUTTON_COLOR, GREY, set_name)
button_name = gc.Button(350, 300, 100, 50, "Ok", FONT, BUTTON_COLOR, GREY, connect)
button_session = gc.Button(350, 300, 100, 50, "Ok", FONT, BUTTON_COLOR, GREY, start_session)
button_no = gc.Button(WIDTH / 6, 500, 150, 50, "No", FONT, BUTTON_COLOR, GREY, endof_round)
button_yes = gc.Button(WIDTH / 4, 500, 150, 50, "Yes", FONT, BUTTON_COLOR, GREY, start_game)
button_menu = gc.Button(WIDTH / 2, 500, 150, 50, "Menu",  FONT, BUTTON_COLOR, GREY, menu)

# Initial texts and buttons
texts = ["Rock Paper Scissors"]
buttons = [button_start, button_exit]
input_boxes = []
your_s = 0
their_s = 0


# Main function
def main():
    global running, current_state
    running = True
    clock = pygame.time.Clock()


    while running:
        screen.fill(BACKGROUND)
        i = 0
        for text in texts:

            gc.draw_text(screen, text, LARGE_FONT, TEXT_COLOR, (WIDTH / 2, 150+i))
            i += 100

        for button in buttons:
            button.update(is_clicked)
            button.draw(screen)

        for box in input_boxes:
            box.update()
            box.draw(screen)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for button in buttons:
                button.handle_event(event, is_clicked)
            for box in input_boxes:
                box.handle_event(event)
            if len(input_boxes) != 0:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        for button in buttons:
                            button.callback()

        clock.tick(30)

    stop_event.set()


    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
