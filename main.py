import pygame
import pygame.gfxdraw
import sys
import unidecode
import random

from scripts.config import load_config


def draw_rounded_rect(surface, rect, color, corner_radius):

    if rect.width < 2 * corner_radius or rect.height < 2 * corner_radius:
        raise ValueError(f"Both height (rect.height) and width (rect.width) must be > 2 * corner radius ({corner_radius})")

    pygame.gfxdraw.aacircle(surface, rect.left+corner_radius, rect.top+corner_radius, corner_radius, color)
    pygame.gfxdraw.aacircle(surface, rect.right-corner_radius-1, rect.top+corner_radius, corner_radius, color)
    pygame.gfxdraw.aacircle(surface, rect.left+corner_radius, rect.bottom-corner_radius-1, corner_radius, color)
    pygame.gfxdraw.aacircle(surface, rect.right-corner_radius-1, rect.bottom-corner_radius-1, corner_radius, color)

    pygame.gfxdraw.filled_circle(surface, rect.left+corner_radius, rect.top+corner_radius, corner_radius, color)
    pygame.gfxdraw.filled_circle(surface, rect.right-corner_radius-1, rect.top+corner_radius, corner_radius, color)
    pygame.gfxdraw.filled_circle(surface, rect.left+corner_radius, rect.bottom-corner_radius-1, corner_radius, color)
    pygame.gfxdraw.filled_circle(surface, rect.right-corner_radius-1, rect.bottom-corner_radius-1, corner_radius, color)

    rect_tmp = pygame.Rect(rect)

    rect_tmp.width -= 2 * corner_radius
    rect_tmp.center = rect.center
    pygame.draw.rect(surface, color, rect_tmp)

    rect_tmp.width = rect.width
    rect_tmp.height -= 2 * corner_radius
    rect_tmp.center = rect.center
    pygame.draw.rect(surface, color, rect_tmp)


def draw_bordered_rounded_rect(surface, rect, color, border_color, corner_radius, border_thickness):
    if corner_radius < 0:
        raise ValueError(f"border radius ({corner_radius}) must be >= 0")
    
    rect_tmp = pygame.Rect(rect)

    if border_thickness:
        if corner_radius <= 0:
            pygame.draw.rect(surface, border_color, rect_tmp)
        else:
            draw_rounded_rect(surface, rect_tmp, border_color, corner_radius)

        rect_tmp.inflate_ip(-2*border_thickness, -2*border_thickness)
        inner_radius = corner_radius - border_thickness + 1
    else:
        inner_radius = corner_radius

    if inner_radius <= 0:
        pygame.draw.rect(surface, color, rect_tmp)
    else:
        draw_rounded_rect(surface, rect_tmp, color, inner_radius)
    

def rgba2rgb(background_color, color):
    alpha = color[3]
    
    return (
        (1 - alpha) * background_color[0] + alpha * color[0],
        (1 - alpha) * background_color[1] + alpha * color[1],
        (1 - alpha) * background_color[2] + alpha * color[2],
    )


class Button:
    def __init__(self, font, text, width, height, pos):
        self.pressed = False
        self.clickable = True
        self.clicked = False
        
        self.font = font
        self.text = text
        self.real_text = unidecode.unidecode(self.text).lower()
        
        self.width = width
        self.height = height
        self.pos = pos
        self.rect = pygame.Rect(self.pos, (self.width, self.height))
        self.color = [0, 191, 255]
        self.alpha = 0.1
        
        self.text_surf = self.font.render(text, True, (255, 255, 255))
        self.text_rect = self.text_surf.get_rect(center = [self.rect.center[0], self.rect.center[1] + 1])
        
    def draw(self, surface):
        draw_bordered_rounded_rect(surface, self.rect, rgba2rgb(BACKGROUND_COLOR, self.color + [self.alpha]), self.color, 10, 3)
        surface.blit(self.text_surf, self.text_rect)
        self.check_click()

    def check_click(self):

        if self.clickable:
            self.clicked = False        
            mouse_pos = pygame.mouse.get_pos()
            if self.rect.collidepoint(mouse_pos):
                self.alpha = min(self.alpha + 0.05, 1)
                if pygame.mouse.get_pressed()[0]:
                    self.pressed = True
                else:
                    if self.pressed == True:
                        self.clicked = True
                        self.pressed = False                
            else:
                self.pressed = False
                self.alpha = max(self.alpha - 0.07, 0.1)


class InputRect:
    def __init__(self, font, width, height, pos):
        
        self.font = font
        self.width = width
        self.height = height
        self.pos = pos
        
        self.auto_capital_letter = True
        
        self.text_color = (255, 255, 255)
        self.color = [0, 191, 255]
        self.alpha = 0.1
        
        self.active = False
        self.entered = False
        
        self.hitbox = pygame.Rect(self.pos, (self.width, self.height))
        
        self.text = ""
        self.real_text = ""
        self.max_characters = 25
        
        self.backspace_pressed = False
        self.backspace_wait = 120
        self.backspace_counter = 0
        
        self.render_text()

    def render_text(self):
        
        if len(self.text) > 0:
            text_surface = self.font.render(self.text, True, self.text_color)
            if text_surface.get_width() > self.width:
                text_surface = pygame.transform.smoothscale(text_surface, (self.width, int(text_surface.get_height() * (self.width / text_surface.get_width()))))
        
        else:
            text_surface = self.font.render("Napíšte text sem", True, rgba2rgb(BACKGROUND_COLOR, self.color + [max(0.2, self.alpha)]))
        
        self.text_image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.text_image.blit(text_surface, ((self.width - text_surface.get_width()) // 2, (self.height - text_surface.get_height()) // 2 + 2))

    def update(self, surface, event_list, elapsed_time):
        
        self.entered = False
        
        for event in event_list:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.active = self.hitbox.collidepoint(event.pos)
                
            if event.type == pygame.KEYDOWN and self.active:
                if event.key == pygame.K_BACKSPACE:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.text = ""
                        self.backspace_counter = 0
                    else:
                        self.backspace_pressed = True
                        self.text = self.text[:-1]
                        self.backspace_counter = 0
                    
                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    #self.active = False
                    self.entered = True
                    
                else:
                    if len(self.text) <= self.max_characters:
                        letter = event.unicode
                        if self.auto_capital_letter and (len(self.text) == 0 or self.text[-1] == " "):
                            letter = letter.upper()
                        self.text += letter
                    
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_BACKSPACE:
                    self.backspace_pressed = False
                    self.backspace_counter = 0
        
        if self.backspace_pressed:
            self.backspace_counter += elapsed_time
            if self.backspace_counter >= self.backspace_wait:
                self.text = self.text[:-1]
                self.backspace_counter = self.backspace_wait - 30
        
        if self.hitbox.collidepoint(pygame.mouse.get_pos()) or self.active:
            self.alpha = min(self.alpha + 0.05, 1)
            
        else:
            self.alpha = max(self.alpha - 0.07, 0.1)
        
        self.real_text = unidecode.unidecode(self.text).lower()
        self.render_text()
        
        draw_bordered_rounded_rect(surface, pygame.Rect(self.pos, (self.width, self.height)), rgba2rgb(BACKGROUND_COLOR, self.color + [self.alpha]), self.color, 10, 3)
        surface.blit(self.text_image, self.pos)


def load_countries(path) -> dict:
    
    with open(path, encoding="utf8") as file:
        raw_data = file.readlines()
        
    data = {}
    for line in raw_data:
        if "-" not in line:
            current_region = line.strip()
        else:
            data[line.split(" - ")[0].strip()] = {
                "region": current_region, 
                "capital": [line.split(" - ")[1].strip(), unidecode.unidecode(line.split(" - ")[1].strip()).lower()], 
                "flag": unidecode.unidecode(line.split(" - ")[0].strip()).lower() + ".png",
                "blindmap": unidecode.unidecode(line.split(" - ")[0].strip()).lower() + ".png"}
            
    return data


class Game:
    def __init__(self):
        
        self.config = load_config("config")
        
        pygame.init()
        self.surface = pygame.display.set_mode(self.config["window"]["resolution"], pygame.SRCALPHA, 32)
        pygame.display.set_caption("Geografia - Quiz")
        self.clock = pygame.time.Clock()
        
        self.countries_data = load_countries("data/countries_svk.txt")
        
        self.state = "main_menu"
        self.prev_state = "main_menu"
        self.transition = [False, 0]
        self.wait = 0
        self.sign = 1
        
        self.font = pygame.font.Font("data/font/Mainlux-Light.otf", 30)
        self.font_big = pygame.font.Font("data/font/Mainlux-Light.otf", 60)
        
        self.main_menu_buttons = [
            Button(self.font, "Hrať", 600, 50, (100, 275)),
            Button(self.font, "Nastavenia", 600, 50, (100, 350)),
            Button(self.font, "Vypnúť", 600, 50, (100, 650))
        ]
        
        self.settings_buttons = [
            Button(self.font, "Späť", 600, 50, (100, 650))
        ]
        
        self.current_country = "Mexiko"
        self.game_buttons = []
        self.current_countries = [0] * 4
        self.possible_countries = []
        
        self.questions = []
        self.questions_answered = 0
        self.corrent_answers = 0
        
        self.input_rects = [
            InputRect(self.font, 600, 50, (100, 325))
        ]
        
        self.elapsed_time = 0
        
    def run(self):
        while True:
            if self.transition[0]:
                if self.prev_state == "main_menu":
                    self.main_menu()
                if self.prev_state == "settings":
                    self.settings()
                if self.prev_state == "game":
                    self.run_game()
                
                if self.wait > 0:
                    self.wait -= self.elapsed_time / 1000
                    self.transition[1] = 1
                else:
                    self.transition[1] = max(min(self.transition[1] + self.sign * 20, 255), 0)
                    
                transition_surface = pygame.Surface(self.config["window"]["resolution"], pygame.SRCALPHA, 32)
                transition_surface.fill(BACKGROUND_COLOR + [self.transition[1]])
                self.surface.blit(transition_surface, (0, 0))
                
                if self.transition[1] >= 255:
                    self.prev_state = self.state
                    self.sign *= -1
                    
                    if self.state == "game":
                        self.game_buttons = []
                        self.current_country = self.questions[self.questions_answered]
                        self.input_rects[0].text = ""
                    
                if self.transition[1] <= 0:
                    self.sign *= -1
                    self.transition = [False, 0]
                
            else:
                if self.state == "main_menu":
                    self.main_menu()
                elif self.state == "settings":
                    self.settings()
                elif self.state == "game":
                    self.run_game()
                    
            pygame.display.update()
            self.elapsed_time = self.clock.tick(self.config["window"]["fps"])
            
    def main_menu(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        self.surface.fill(BACKGROUND_COLOR)
        draw_bordered_rounded_rect(self.surface, pygame.Rect((50, 50), (700, 700)), BACKGROUND_COLOR, (50, 50, 50), 10, 3)
        
        for button in self.main_menu_buttons:
            button.draw(self.surface)
    
        if self.main_menu_buttons[0].clicked:
            self.transition = [True, 1]
            self.questions = random.sample(list(self.countries_data.keys()), 10)
            self.state = "game"
            
        if self.main_menu_buttons[1].clicked:
            self.transition = [True, 1]
            self.state = "settings"
            
        if self.main_menu_buttons[2].clicked:
            pygame.quit()
            sys.exit()
            
            
        text_surface = self.font_big.render("Geografia - Quiz", True, (255, 255, 255))
        self.surface.blit(text_surface, ((800 - text_surface.get_width()) // 2, 165 - text_surface.get_height() // 2 + 2))

    def settings(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        self.surface.fill(BACKGROUND_COLOR)
        draw_bordered_rounded_rect(self.surface, pygame.Rect((50, 50), (700, 700)), BACKGROUND_COLOR, (50, 50, 50), 10, 3)
        
        for button in self.settings_buttons:
            button.draw(self.surface)
            
        if self.settings_buttons[0].clicked:
            self.transition = [True, 1]
            self.state = "main_menu"
            
        text_surface = self.font_big.render("Nastavenia", True, (255, 255, 255))
        self.surface.blit(text_surface, ((800 - text_surface.get_width()) // 2, 165 - text_surface.get_height() // 2 + 2))


    def run_game(self):
        event_list = pygame.event.get()
        for event in event_list:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        self.surface.fill(BACKGROUND_COLOR)
        draw_bordered_rounded_rect(self.surface, pygame.Rect((50, 50), (700, 700)), BACKGROUND_COLOR    , (50, 50, 50), 10, 3)
        
        for button in self.game_buttons:
            button.draw(self.surface)
        
        text_surface = self.font.render("Hlavné mesto:", True, (255, 255, 255))
        self.surface.blit(text_surface, ((800 - text_surface.get_width()) // 2, (200 - text_surface.get_height()) // 2 + 2))
        
        text_surface = self.font_big.render(self.current_country, True, (255, 255, 255))
        if text_surface.get_width() > 600:
                text_surface = pygame.transform.smoothscale(text_surface, (600, int(text_surface.get_height() * (600 / text_surface.get_width()))))
        self.surface.blit(text_surface, ((800 - text_surface.get_width()) // 2, 215 - text_surface.get_height() // 2 + 2))

        for input_rect in self.input_rects:
            input_rect.update(self.surface, event_list, self.elapsed_time)
        
        if len(self.input_rects[0].real_text) >= 3:
            self.possible_countries = list(filter(lambda x: self.input_rects[0].real_text in x[1], [[country, data["capital"][1]] for country, data in self.countries_data.items()]))
        else:
            self.possible_countries = []
                  
        for i in range(4):
            if i < len(self.possible_countries):
                if self.possible_countries[i] == self.current_countries[i]:
                    pass
                else:
                    try:
                        self.game_buttons.pop(i)
                    except:
                        pass
                    
                    self.current_countries[i] = self.possible_countries[i]
                    self.game_buttons.insert(i, Button(self.font, self.countries_data[self.possible_countries[i][0]]["capital"][0], 600, 50, (100, 425 + 75 * i)))
            else:
                try:
                    self.game_buttons.pop(i)
                except:
                    pass
                self.current_countries[i] = 0
                
        
        for button in self.game_buttons:        
            if button.clicked or (self.input_rects[0].entered and len(self.game_buttons) == 1):
                self.questions_answered += 1
                
                if button.real_text == self.countries_data[self.current_country]["capital"][1]:
                    button.color = [0, 255, 0]
                    self.corrent_answers += 1
                else:
                    button.color = [255, 0, 0]
                
                self.transition = [True, 1]
                self.wait = 0.5
                if self.questions_answered < len(self.questions):
                    self.state = "game"
                else:
                    print(self.corrent_answers, self.questions_answered)
                    self.corrent_answers = 0
                    self.questions_answered = 0
                    self.state = "main_menu"
                
        
if __name__ == "__main__":
    BACKGROUND_COLOR = [22, 22, 22]
    game = Game()
    game.run()