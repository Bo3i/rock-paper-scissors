import sys
import threading
import pygame
import pika
import traceback

pygame.init()

# Constants
WIDTH = 700
HEIGHT = 400
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
is_clicked = False
current_state = 'main_menu'  # Initial state


# Function to draw text on screen
def draw_text(surface, text, font, color, pos):
    text_object = font.render(text, True, color)
    text_rect = text_object.get_rect(center=pos)
    surface.blit(text_object, text_rect)


# Button class for image buttons
class ImageButton:
    def __init__(self, x, y, image, callback):
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
        self.callback = callback

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def draw(self, screen):
        screen.blit(self.image, self.rect.topleft)

    def update(self):
        pass


# Button class for text buttons
class Button:
    def __init__(self, x, y, w, h, text, color, hover_color, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.hover_color = hover_color
        self.text = text
        self.txt_surface = FONT.render(text, True, WHITE)
        self.callback = callback
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def update(self):
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())

    def draw(self, screen):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        screen.blit(self.txt_surface, (self.rect.x + (self.rect.width - self.txt_surface.get_width()) // 2,
                                       self.rect.y + (self.rect.height - self.txt_surface.get_height()) // 2))


# Input box class for text input
class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = BLACK
        self.text = text
        self.txt_surface = FONT.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = GREY if self.active else BLACK
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    print(self.text)
                    self.text = ''
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                self.txt_surface = FONT.render(self.text, True, self.color)

    def update(self):
        width = max(200, self.txt_surface.get_width() + 10)
        self.rect.w = width

    def draw(self, screen):
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        pygame.draw.rect(screen, self.color, self.rect, 2)


# Function to initialize the game
def init_game():
    global buttons, texts, input_boxes
    texts = ["Connect to host, for localhost press ok"]
    buttons = [button_sethost]
    box = InputBox(300, 200, 200, 50)
    input_boxes = [box]


# Function to exit the game
def exit_game():
    global running
    running = False
    print("DEBUG: Exiting game")


# Function for connecting to the server
def connect():
    global host, player_name, texts, buttons, input_boxes, connection, channel, current_state
    for box in input_boxes:
        player_name = box.text
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


# Function for starting new session
def start_session():
    global input_boxes, buttons, texts, session_id, channel, connection
    for box in input_boxes:
        session_id = box.text

    input_boxes = []
    buttons = []

    try:
        channel.queue_declare(queue='start')
        channel.basic_publish(exchange='',
                              routing_key='start',
                              body=f"{session_id},{player_name}")

        threading.Thread(target=consume_from_queue, args=(f'{player_name}', on_response)).start()

        print("DEBUG: Message to server sent")
        print("DEBUG: Waiting for response...")

    except Exception as e:
        print(f"ERROR: Error starting session: {e}")
        texts = ['Error starting session!']
        buttons = [button_exit]


# Function for handling server response
def on_response(ch, method, properties, body):
    global opponent, p_id, player_name, channel, current_state
    try:
        opponent, p_id = body.decode().split(",")
        print(f"DEBUG: Playing against: {opponent}!")

        # channel.queue_declare(queue=f"{player_name}{session_id}{p_id}")
        # channel.queue_declare(queue=f"{player_name}{p_id}won")

        start_game()
    except Exception as e:
        print(f"ERROR: Error in response: {e}")
        texts = ['Error in response!']
        buttons = [button_exit]


def winner(ch, method, properties, body):
    global connection, channel, texts, buttons, screen, opponent, current_state
    print("recieved result from server")
    try:
        win, mov, y_score, op_score = body.decode().split(",")
        print(f"DEBUG: {opponent} chose: {mov}")
        print(mov)
        if win == 'Tie':
            print("DEBUG: It's a tie!")
            texts = [f"It's a tie!", f"Score: You {y_score} : {op_score} {opponent}",
                     "Do you want to play again?"]
        elif win == opponent:
            print(f"DEBUG: {win} wins!")
            texts = [f"{win} wins!", f"Score: You {y_score} : {op_score} {opponent}",
                     "Do you want to play again?"]
        else:
            print("DEBUG: You win!")
            texts = ["You win!", f"Score: You {y_score} : {op_score} {opponent}",
                     "Do you want to play again?"]

        buttons = [button_no, button_yes]
        current_state = 'end_round'
        main()
    except Exception as e:
        print(f"ERROR: Error in winner callback: {e},{traceback.format_exc()}")


def endof_round():
    global current_state
    try:
        connection.close()
        print("DEBUG: Exiting... Goodbye!")
        exit()
    except:
        return


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
            threading.Thread(target=consume_from_queue, args=(f"{player_name}{p_id}won", winner)).start()
            channel.basic_publish(exchange='',
                                  routing_key=f"{player_name}{session_id}{p_id}",
                                  body=player_input)
            print(f'queue: {player_name}{p_id}won')
            is_clicked = False
    except Exception as e:
        print(f"ERROR: Error in send_input: {e}")


# Starting game
def start_game():
    global buttons, texts, current_state
    print("DEBUG: Entering start_game function")
    texts = ["Your turn!"]
    buttons = [rock_button, paper_button, scissors_button]
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
    box = InputBox(300, 200, 200, 50)
    input_boxes = [box]


# Function to set player name
def set_name():
    global host, texts, buttons, input_boxes
    for box in input_boxes:
        host = box.text

    texts = ["What's your name?"]
    buttons = [button_name]
    box = InputBox(300, 200, 200, 50)
    input_boxes = [box]


# Create buttons
button_start = Button(WIDTH / 4, 200, 150, 50, "Start", BUTTON_COLOR, GREY, init_game)
button_exit = Button(WIDTH / 2, 200, 150, 50, "Exit", BUTTON_COLOR, GREY, exit_game)
rock_button = ImageButton(100, 250, rock_img, on_rock)
paper_button = ImageButton(325, 250, paper_img, on_paper)
scissors_button = ImageButton(550, 250, scissors_img, on_scissors)
button_sethost = Button(350, 300, 100, 50, "Ok", BUTTON_COLOR, GREY, set_name)
button_name = Button(350, 300, 100, 50, "Ok", BUTTON_COLOR, GREY, connect)
button_session = Button(350, 300, 100, 50, "Ok", BUTTON_COLOR, GREY, start_session)
button_no = Button(WIDTH / 4, 400, 150, 50, "No", BUTTON_COLOR, GREY, endof_round)
button_yes = Button(WIDTH / 2, 400, 150, 50, "Yes", BUTTON_COLOR, GREY, start_game)

# Initial texts and buttons
texts = ["Rock Paper Scissors"]
buttons = [button_start, button_exit]
input_boxes = []


# Main function
def main():
    global running, current_state
    running = True
    clock = pygame.time.Clock()

    while running:
        screen.fill(BACKGROUND)

        for text in texts:
            draw_text(screen, text, LARGE_FONT, TEXT_COLOR, (WIDTH / 2, HEIGHT / 4))

        for button in buttons:
            button.update()
            button.draw(screen)

        for box in input_boxes:
            box.update()
            box.draw(screen)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for button in buttons:
                button.handle_event(event)
            for box in input_boxes:
                box.handle_event(event)

        clock.tick(30)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
