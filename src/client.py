import sys
import threading
import pygame
import pika
import traceback
import signal
import game_components as gc
import q_consumer as c


# Initialize pygame and pygame.mixer
pygame.init()
pygame.mixer.init()
pygame.mixer.music.load("../assets/Atmospheric-ambient-music.wav")
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
screen = pygame.display.set_mode((WIDTH, HEIGHT), vsync=1)
pygame.display.set_caption("Rock Paper Scissors Game")


# Load and resize images
rock_img = pygame.image.load('../assets/rock.jpg')
rock_img = pygame.transform.scale(rock_img, (150, 150))

paper_img = pygame.image.load('../assets/paper.jpg')
paper_img = pygame.transform.scale(paper_img, (150, 150))

scissors_img = pygame.image.load('../assets/scissors.jpg')
scissors_img = pygame.transform.scale(scissors_img, (150, 150))

FONT = pygame.font.Font(None, 32)
LARGE_FONT = pygame.font.Font(None, 56)


# Globals for RabbitMQ
running = False
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
    global running, stop_event
    stop_event.set()
    running = False

    print("DEBUG: Exiting game")


# Function for connecting to the server
def connect():
    global host, player_name, texts, buttons, input_boxes, connection, channel, current_state
    for box in input_boxes:
        box.text = box.text.strip()
        if box.text:
            player_name = box.text
        else:
            set_name()
            return
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


# Function called when opponent disconnects message is received
def on_exit_recieve(ch, method, properties, body):
    global p_id, texts, buttons, your_s, their_s
    your_s, their_s = 0, 0
    print('Received opponent disconnection')
    texts = ['Opponent disconnected', 'Exit to menu']
    button_menu.rect.y = 300
    button_menu.rect.x = 325
    buttons = [button_menu]


# Function to let the server know player quit the session
def on_exit_publish():
    global host, is_clicked, your_s, their_s
    is_clicked = False
    connection = pika.BlockingConnection(pika.ConnectionParameters(host))
    channel = connection.channel()
    channel.basic_publish(
        exchange='',
        routing_key=f'q{player_name}{session_id}{p_id}exit',
        body=f'{p_id},{session_id}'
    )
    your_s = 0
    their_s = 0
    print('Publishing session exit message')


# Function for starting new session
def start_session():
    global input_boxes, buttons, texts, session_id, channel, connection
    for box in input_boxes:
        box.text = box.text.strip()
        if box.text:
            session_id = box.text
        else:
            define_session()
            return
    input_boxes = []
    buttons = []

    try:
        channel.queue_declare(queue='start')
        channel.basic_publish(exchange='',
                              routing_key='start',
                              body=f"{session_id},{player_name}")

        conn_consumer = c.Consumer(f"q{player_name}{session_id}status", host, on_connect, stop_event)
        conn_consumer.start()
        consumers.append(conn_consumer)
        texts = [f"Connecting to session: {session_id} ..."]
        ex_consumer = c.Consumer(f'q{player_name}{session_id}ex', host, on_exit_recieve, stop_event)
        ex_consumer.start()
        consumers.append(ex_consumer)


        print(f"Connecting to session: {session_id} ...")


    except Exception as e:
        print(f"ERROR: Error starting session: {e}")
        texts = ['Error starting session!']
        buttons = [button_exit]


# Function for handling server response
def on_connect(ch, method, properties, body):
    global texts, buttons, p_id, is_clicked
    is_clicked = False
    mess = body.decode()
    status, p_id = mess.split(',')
    if status == 'o':
        conn_consumer = c.Consumer(f'q{player_name}{session_id}{p_id}', host, on_response, stop_event)
        conn_consumer.start()
        consumers.append(conn_consumer)
        texts = ["Waiting for other player..."]
    elif status == 'f':
        texts = [f"Session: {session_id} is full"]
        buttons = [button_menu]


# Function for handling server response
def on_response(ch, method, properties, body):
    global opponent, p_id, player_name, channel, current_state
    try:
        opponent, p_id = body.decode().split(",")
        print(f"Playing against: {opponent}!")

        channel.queue_declare(queue=f"q{player_name}{p_id}won")

        start_game()
    except Exception as e:
        print(f"ERROR: Error in response: {e}")
        texts = ['Error in response!']
        buttons = [button_exit]


# Function for handling server response with round result
def winner(ch, method, properties, body):
    global connection, channel, texts, buttons, screen, opponent, current_state, your_s, their_s, is_clicked
    try:
        win, mov, y_score, op_score = body.decode().split(",")
        your_s = y_score
        their_s = op_score
        print(f"DEBUG: {opponent} chose: {mov}")
        print(mov)
        if win == 'Tie':
            print("DEBUG: It's a tie!")
            texts = [f"It's a tie!", f"You {y_score} : {op_score} {opponent}", "Do you want to play again?"]
        elif win == opponent:
            print(f"DEBUG: {win} wins!")
            texts = [f"{win} wins!", f"You {y_score} : {op_score} {opponent}", "Do you want to play again?"]
        else:
            print("DEBUG: You win!")
            texts = ["You win!", f"You {y_score} : {op_score} {opponent}", "Do you want to play again?"]
        screen.fill(BACKGROUND)
        button_menu.rect.x = 225
        button_yes.rect.x = 425
        button_menu.rect.y = 500
        button_yes.rect.y = 500
        buttons = [button_yes, button_menu]
        current_state = 'end_round'
        is_clicked = False
    except Exception as e:
        print(f"ERROR: Error in winner callback: {e},{traceback.format_exc()}")


# Function to end the round
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


# Function to send player input to server
def send_input():
    global connection, player_input, opponent, texts, buttons, channel, is_clicked
    try:
        if is_clicked:
            input_consumer = c.Consumer(f"q{player_name}{p_id}won", host, winner, stop_event)
            input_consumer.start()
            consumers.append(input_consumer)
            channel.basic_publish(exchange='',
                                  routing_key=f"q{player_name}{session_id}{p_id}choice",
                                  body=player_input)

    except Exception as e:
        print(f"ERROR: Error in send_input: {e}")


# Starting game
def start_game():
    global buttons, texts, current_state, is_clicked, opponent, your_s, their_s, channel, p_id

    channel.basic_publish(exchange='',
                          routing_key=f"q{player_name}{session_id}{p_id}ready",
                          body=f'{p_id}')

    print("DEBUG: Entering start_game function")
    texts = [f"You {your_s} : {their_s} {opponent}"]
    button_menu.rect.x = 325
    button_menu.rect.y = 450
    buttons = [rock_button, paper_button, scissors_button, button_menu]
    current_state = 'game'


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


# Function to set player name
def set_name():
    global host, texts, buttons, input_boxes
    for box in input_boxes:
        host = box.text

    texts = ["What's your name?"]
    buttons = [button_name]
    box = gc.InputBox(300, 200, 200, 50, FONT)
    input_boxes = [box]


# Function to return to main menu
def menu():
    global connection, texts, buttons, input_boxes
    if current_state != 'main_menu':
        on_exit_publish()
    texts = ["Rock Paper Scissors"]
    button_exit.rect.x = WIDTH/2
    button_exit.rect.y = 200
    buttons = [button_start, button_exit]
    input_boxes = []


# Buttons declaration
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
    global running, current_state, stop_event, consumers
    running = True
    clock = pygame.time.Clock()

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

    signal.signal(signal.SIGINT, signal_handler)

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

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
