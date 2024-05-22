import sys
import pygame
import pika

pygame.init()

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


# Function to draw text on screen
def draw_text(surface, text, font, color, pos):
    text_object = font.render(text, True, color)
    text_rect = text_object.get_rect(center=pos)
    surface.blit(text_object, text_rect)

# random variable
is_clicked = False

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
        return


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


# Starting game
def start_game():
    global buttons, texts
    print("DEBUG: Entering start_game function")
    texts = ["Your turn!"]
    buttons = [rock_button, paper_button, scissors_button]
    screen.fill(BACKGROUND)
    for text in texts:
        draw_text(screen, text, LARGE_FONT, TEXT_COLOR, (WIDTH / 2, HEIGHT / 4))

    for button in buttons:
        button.update()
        button.draw(screen)
    pygame.display.flip()

    print("DEBUG: listenning to actions")
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        for button in buttons:
            button.handle_event(event)




# Function for connecting to the server
def connect():
    global host, player_name, texts, buttons, input_boxes, connection, channel
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


# function for starting new session
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
        channel.queue_declare(queue=player_name)
        channel.basic_consume(queue=player_name, on_message_callback=on_response, auto_ack=True)
        print("DEBUG: Message to server sent")
        print("DEBUG: Waiting for response...")
        channel.start_consuming()

    except Exception as e:
        print(f"ERROR: Error starting session: {e}")
        texts = ['Error starting session!']
        buttons = [button_exit]


# Function for handling server response
def on_response(ch, method, properties, body):
    global opponent, p_id, player_name, channel
    try:
        opponent, p_id = body.decode().split(",")
        print(f"DEBUG: Playing against: {opponent}!")

        channel.queue_declare(queue=f"{player_name}{session_id}{p_id}")
        channel.queue_declare(queue=f"{player_name}{p_id}won")

        start_game()

    except Exception as e:
        print(f"ERROR: Error in response: {e}")
        texts = ['Error in response!']
        buttons = [button_exit]


# Function for playing a round

def send_input():
    global connection, player_input, opponent, texts, buttons, channel
    try:
        if is_clicked:
            channel.basic_publish(exchange='',
                              routing_key=f"{player_name}{session_id}{p_id}",
                              body=player_input)
            channel.basic_consume(queue=f"{player_name}{p_id}won", on_message_callback=winner, auto_ack=True)
    except Exception as e:
        print(f"ERROR: Error in play_round: {e}")


def winner(ch, method, properties, body):
    try:
        win, mov, y_score, op_score = body.decode().split(",")
        print(f"DEBUG: {opponent} chose: {mov}")
        if win == "Tie":
            print("DEBUG: It's a tie!")
        elif win == opponent:
            print(f"DEBUG: {win} wins!")
        else:
            print("DEBUG: You win!")
        print(f"DEBUG: ---Score--- \nYou  {y_score} : {op_score}  {opponent}")
        play_again = input('Do you want to play again? y/n: ')
        if play_again == 'n':
            connection.close()
            print("DEBUG: Exiting... Goodbye!")
            exit()
        else:
            send_input()
    except Exception as e:
        print(f"ERROR: Error in winner callback: {e}")

# Functions for handling player choices
def on_rock():
    global player_input
    player_input = 'r'
    print("DEBUG: Player chose rock")
    is_clicked = True
    send_input()



def on_paper():
    global player_input
    player_input = 'p'
    print("DEBUG: Player chose paper")
    is_clicked = True
    send_input()



def on_scissors():
    global player_input
    player_input = 's'
    print("DEBUG: Player chose scissors")
    is_clicked = True
    send_input()



# Function to initialize the game
def init_game():
    global buttons, texts, input_boxes
    texts = ["Connect to host, for localhost press enter"]
    buttons = [button_sethost]
    box = InputBox(300, 200, 200, 50)
    input_boxes = [box]


# Function to exit the game
def exit_game():
    global running
    running = False
    print("DEBUG: Exiting game")


# Function to define a session
def define_session():
    global input_boxes, buttons, texts
    buttons = [button_session]
    texts = ["Connect to session:"]
    box = InputBox(300, 200, 200, 50)
    input_boxes = [box]


# Function to set player name
def set_name():
    global host
    global texts, buttons, input_boxes
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

# Initial texts and buttons
texts = ["Rock Paper Scissors"]
buttons = [button_start, button_exit]
input_boxes = []


# Main function
def main():
    global running
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


def play():
    #print('Welcome to simple online "ROCK PAPER SCISSORS" game!')
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
        opponent, p_id = body.decode().split(",")
        print(f"Playing against: {opponent}!")
        #ch.basic_ack(delivery_tag=method.delivery_tag)
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
                print(f"{opponent} chose: {mov}")
                #ch.basic_ack(delivery_tag=method.delivery_tag)
                if win == "Tie":
                    print("It's a tie!")
                elif win == opponent:
                    print(f"{win} wins!")
                else:
                    print("You win!")
                print(f"---Score--- \nYou  {y_score} : {op_score}  {opponent}")
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


if __name__ == "__main__":
    #play()
    main()
