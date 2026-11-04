"""Original rounded controls with cached drawing and event-based input."""

from functools import lru_cache
import pygame
import pygame.gfxdraw

BACKGROUND_COLOR = [22, 22, 22]
CYAN = (0, 191, 255)

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


@lru_cache(maxsize=128)
def control_image(size, color, alpha):
    surface = pygame.Surface(size)
    surface.fill(BACKGROUND_COLOR)
    draw_bordered_rounded_rect(surface, surface.get_rect(),
                              rgba2rgb(BACKGROUND_COLOR, list(color) + [alpha]), color, 10, 3)
    return surface


@lru_cache(maxsize=256)
def rendered_text(font, text, color=(255, 255, 255), width=600):
    image = font.render(text, True, color)
    if image.get_width() > width:
        image = pygame.transform.smoothscale(image,
            (width, max(1, round(image.get_height() * width / image.get_width()))))
    return image


class Button:
    def __init__(self, font, text, width=600, height=50, pos=(100, 325)):
        self.font = font
        self.rect = pygame.Rect(pos, (width, height))
        self.color = CYAN
        self.alpha = 0.1
        self.pressed = self.clicked = False
        self.set_text(text)

    def set_text(self, text):
        self.text = text
        self.text_image = rendered_text(self.font, text, width=self.rect.width - 20)

    def update(self, events, mouse, elapsed, enabled=True):
        self.clicked = False
        if not enabled:
            self.pressed = False
            return
        hovering = self.rect.collidepoint(mouse)
        self.alpha = (min(1, self.alpha + 0.05 * elapsed / (1000 / 60)) if hovering
                      else max(0.1, self.alpha - 0.07 * elapsed / (1000 / 60)))
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.pressed = self.rect.collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.clicked = self.pressed and self.rect.collidepoint(event.pos)
                self.pressed = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.pressed = False

    def draw(self, surface):
        surface.blit(control_image(self.rect.size, tuple(self.color), round(self.alpha, 2)), self.rect)
        surface.blit(self.text_image, self.text_image.get_rect(center=(self.rect.centerx, self.rect.centery + 1)))


class InputRect:
    def __init__(self, font, width=600, height=50, pos=(100, 325)):
        self.font = font
        self.hitbox = pygame.Rect(pos, (width, height))
        self.max_characters = 64
        self.alpha = 0.1
        self.color = CYAN
        self.active = self.entered = False
        self.text = ''
        self.backspace_pressed = False
        self.repeat_after = 0

    def clear(self):
        self.text = ''
        self.color = CYAN
        self.entered = self.backspace_pressed = False
        self.active = True
        pygame.key.start_text_input()

    def update(self, events, elapsed, mouse, enabled=True):
        self.entered = False
        if not enabled:
            self.backspace_pressed = False
            return
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.active = self.hitbox.collidepoint(event.pos)
                if self.active:
                    pygame.key.start_text_input()
                else:
                    self.backspace_pressed = False
                    pygame.key.stop_text_input()
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.backspace_pressed = False
            elif event.type == pygame.KEYUP and event.key == pygame.K_BACKSPACE:
                self.backspace_pressed = False
            elif self.active and event.type == pygame.TEXTINPUT:
                for letter in event.text:
                    if len(self.text) >= self.max_characters:
                        break
                    if letter.isprintable():
                        letter = letter.upper() if not self.text or self.text.endswith(' ') else letter
                        self.text = (self.text + letter)[:self.max_characters]
            elif self.active and event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.entered = True
                elif event.key == pygame.K_BACKSPACE:
                    if getattr(event, 'mod', 0) & pygame.KMOD_CTRL:
                        self.text = ''
                        self.backspace_pressed = False
                    else:
                        self.text = self.text[:-1]
                        self.backspace_pressed = True
                        self.repeat_after = 120
        if self.active and self.backspace_pressed:
            self.repeat_after -= elapsed
            while self.repeat_after <= 0:
                self.text = self.text[:-1]
                self.repeat_after += 30
        hovering = self.active or self.hitbox.collidepoint(mouse)
        self.alpha = (min(1, self.alpha + 0.05 * elapsed / (1000 / 60)) if hovering
                      else max(0.1, self.alpha - 0.07 * elapsed / (1000 / 60)))

    def draw(self, surface):
        surface.blit(control_image(self.hitbox.size, tuple(self.color), round(self.alpha, 2)), self.hitbox)
        color = ((255, 255, 255) if self.text else
                 tuple(int(v) for v in rgba2rgb(BACKGROUND_COLOR, list(CYAN) + [max(0.2, self.alpha)])))
        image = rendered_text(self.font, self.text or 'Napíšte text sem', color, self.hitbox.width - 20)
        surface.blit(image, image.get_rect(center=(self.hitbox.centerx, self.hitbox.centery + 2)))
