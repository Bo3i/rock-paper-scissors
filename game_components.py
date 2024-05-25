import pygame

# Constants
# WIDTH = 800
# HEIGHT = 600
WHITE = (255, 255, 255)
# BACKGROUND = (245, 235, 224)
# BUTTON_COLOR = (154, 154, 132)
TEXT_COLOR = (79, 79, 64)
BLACK = (0, 0, 0)
GREY = (133, 117, 110)
# FONT = pygame.font.Font(None, 32)
# LARGE_FONT = pygame.font.Font(None, 56)


def draw_text(surface, text, font, color, pos):
    text_object = font.render(text, True, color)
    text_rect = text_object.get_rect(center=pos)
    surface.blit(text_object, text_rect)


# Button class for image buttons

class ImageButton:
    def __init__(self, x, y, image, callback, border_color=TEXT_COLOR, border_width=2):
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
        self.callback = callback
        self.border_color = border_color
        self.border_width = border_width
        self.hovered = False

    def handle_event(self, event, is_clicked):
        # global is_clicked
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos) and not is_clicked:
                self.callback()

    def update(self, is_clicked):
        # global is_clicked
        if not is_clicked:
            self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())


    def draw(self, screen):
        if self.hovered:
            # Draw the border when hovered
            pygame.draw.rect(screen, self.border_color,
                                self.rect.inflate(self.border_width * 2, self.border_width * 2), self.border_width)
        # Draw the image
        screen.blit(self.image, self.rect.topleft)


# Button class for text buttons
class Button:
    def __init__(self, x, y, w, h, text, font, color, hover_color, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.hover_color = hover_color
        self.text = text
        self.txt_surface = font.render(text, True, WHITE)
        self.callback = callback
        self.hovered = False

    def handle_event(self, event, is_clicked):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def update(self, is_clicked):
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())

    def draw(self, screen):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        screen.blit(self.txt_surface, (self.rect.x + (self.rect.width - self.txt_surface.get_width()) // 2,
                                       self.rect.y + (self.rect.height - self.txt_surface.get_height()) // 2))


# Input box class for text input
class InputBox:
    def __init__(self, x, y, w, h, font, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = BLACK
        self.text = text
        self.txt_surface = font.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):

        FONT = pygame.font.Font(None, 32)
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

