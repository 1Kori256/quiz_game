import argparse
from pathlib import Path
import random
import pygame

from quiz import QuizSession, load_countries
from scripts.config import load_config
from widgets import (BACKGROUND_COLOR, CYAN, Button, InputRect,
                     draw_bordered_rounded_rect, rendered_text)

ROOT = Path(__file__).resolve().parent


class Game:
    def __init__(self, seed=None):
        self.config = load_config(ROOT / 'config')
        pygame.init()
        try:
            self.window = pygame.display.set_mode(self.config['window']['resolution'])
            pygame.display.set_caption('Geografia - Quiz')
            self.surface = pygame.Surface((800, 800)).convert()
            self.panel = self.surface.copy()
            self.panel.fill(BACKGROUND_COLOR)
            draw_bordered_rounded_rect(self.panel, pygame.Rect(50, 50, 700, 700),
                                      BACKGROUND_COLOR, (50, 50, 50), 10, 3)
            self.overlay = pygame.Surface((800, 800)).convert()
            self.overlay.fill(BACKGROUND_COLOR)
            self.clock = pygame.time.Clock()
            font = str(ROOT / 'data/font/Mainlux-Light.otf')
            self.font = pygame.font.Font(font, 30)
            self.font_big = pygame.font.Font(font, 60)
            self.font_small = pygame.font.Font(font, 20)
            self.countries = load_countries(ROOT / 'data/countries_svk.txt')
            self.regions = [None] + list(dict.fromkeys(c.region for c in self.countries.values()))
            self.counts = [5, 10, 20, None]
            self.region_index, self.count_index = 0, 1
            self.rng = random.Random(seed)
            self.session = None
            self.state = 'main_menu'
            self.running = True
            self.transition = None
            self.mouse = (-100, -100)
            self.main_buttons = [Button(self.font, label, pos=(100, y)) for label, y in
                                 (('Hrať', 275), ('Nastavenia', 350), ('Vypnúť', 650))]
            self.settings_buttons = [Button(self.font, label, pos=(100, y)) for label, y in
                                     (('Oblasť: Všetky', 275), ('Otázky: 10', 350), ('Späť', 650))]
            self.result_buttons = [Button(self.font, label, pos=(100, y)) for label, y in
                                   (('Hrať znova', 500), ('Hlavné menu', 650))]
            self.input = InputRect(self.font)
            self.suggestion_buttons = []
            self.suggestion_key = None
        except Exception:
            pygame.quit()
            raise

    def start_round(self):
        self.change_state('game')
        self.transition['session'] = QuizSession(
            self.countries, self.counts[self.count_index], self.regions[self.region_index], self.rng)

    def change_state(self, target, delay=0, advance=False):
        self.transition = {'target': target, 'alpha': 0.0, 'delay': delay,
                           'phase': 'out', 'advance': advance}
        self.input.backspace_pressed = False
        for button in self.buttons():
            button.pressed = button.clicked = False

    def buttons(self):
        return {'main_menu': self.main_buttons, 'settings': self.settings_buttons,
                'game': self.suggestion_buttons, 'results': self.result_buttons}[self.state]

    def update_suggestions(self):
        key = self.input.text
        if key != self.suggestion_key:
            self.suggestion_key = key
            choices = self.session.suggestions(key)
            self.suggestion_buttons = [Button(self.font, text, pos=(100, 425 + 75 * i))
                                       for i, text in enumerate(choices)]

    def submit(self, text):
        answer = self.session.submit(text)
        if answer is None:
            return
        self.input.color = (0, 255, 0) if answer.correct else (255, 0, 0)
        for button in self.suggestion_buttons:
            if button.text == text:
                button.color = self.input.color
        self.change_state('game', delay=0.5, advance=True)

    def update_transition(self, elapsed):
        transition = self.transition
        if transition is None:
            return
        seconds = elapsed / 1000
        if transition['delay'] > 0:
            transition['delay'] = max(0, transition['delay'] - seconds)
            return
        direction = 1 if transition['phase'] == 'out' else -1
        transition['alpha'] = max(0, min(255, transition['alpha'] + direction * seconds * 1200))
        if transition['phase'] == 'out' and transition['alpha'] >= 255:
            if 'session' in transition:
                self.session = transition['session']
            if transition['advance']:
                self.session.advance()
                if self.session.finished:
                    transition['target'] = 'results'
            self.state = transition['target']
            transition['phase'] = 'in'
            if self.state == 'game':
                self.input.clear()
                self.suggestion_buttons = []
                self.suggestion_key = None
            else:
                self.input.active = False
                pygame.key.stop_text_input()
        elif transition['phase'] == 'in' and transition['alpha'] <= 0:
            self.transition = None

    def events(self, events, elapsed):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.state == 'main_menu':
                    self.running = False
                elif self.transition is None:
                    self.change_state('main_menu')
        if not self.running or self.transition is not None:
            return
        if self.state == 'game':
            self.input.update(events, elapsed, self.mouse)
            self.update_suggestions()
        for button in self.buttons():
            button.update(events, self.mouse, elapsed)
        if self.state == 'main_menu':
            if self.main_buttons[0].clicked:
                self.start_round()
            elif self.main_buttons[1].clicked:
                self.change_state('settings')
            elif self.main_buttons[2].clicked:
                self.running = False
        elif self.state == 'settings':
            if self.settings_buttons[0].clicked:
                self.region_index = (self.region_index + 1) % len(self.regions)
                region = self.regions[self.region_index] or 'Všetky'
                self.settings_buttons[0].set_text('Oblasť: ' + region)
            elif self.settings_buttons[1].clicked:
                self.count_index = (self.count_index + 1) % len(self.counts)
                count = self.counts[self.count_index] or 'Všetky'
                self.settings_buttons[1].set_text(f'Otázky: {count}')
            elif self.settings_buttons[2].clicked:
                self.change_state('main_menu')
        elif self.state == 'game':
            clicked = next((button for button in self.suggestion_buttons if button.clicked), None)
            if clicked is not None:
                self.submit(clicked.text)
            elif self.input.entered:
                self.submit(self.input.text)
        elif self.state == 'results':
            if self.result_buttons[0].clicked:
                self.start_round()
            elif self.result_buttons[1].clicked:
                self.change_state('main_menu')

    def centered(self, text, y, font=None, color=(255, 255, 255)):
        image = rendered_text(font or self.font, text, tuple(color))
        self.surface.blit(image, image.get_rect(center=(400, y + 2)))

    def render(self):
        self.surface.blit(self.panel, (0, 0))
        if self.state == 'main_menu':
            self.centered('Geografia - Quiz', 165, self.font_big)
        elif self.state == 'settings':
            self.centered('Nastavenia', 165, self.font_big)
        elif self.state == 'results':
            self.centered('Výsledok', 165, self.font_big)
            self.centered(f'{self.session.score} / {len(self.session.questions)}', 325, self.font_big, CYAN)
            self.centered('Správne odpovede', 395)
        elif self.state == 'game':
            self.centered('Hlavné mesto:', 100)
            self.centered(self.session.current.name, 215, self.font_big)
            progress = rendered_text(self.font_small, f'{self.session.index + 1} / {len(self.session.questions)}')
            self.surface.blit(progress, progress.get_rect(topright=(700, 75)))
            self.input.draw(self.surface)
            if self.session.pending is not None:
                answer = self.session.pending
                message = 'Správne' if answer.correct else f'Správna odpoveď: {answer.country.capital}'
                self.centered(message, 395, self.font_small, self.input.color)
        for button in self.buttons():
            button.draw(self.surface)
        if self.transition is not None:
            self.overlay.set_alpha(round(self.transition['alpha']))
            self.surface.blit(self.overlay, (0, 0))

    def frame(self, elapsed):
        elapsed = min(max(elapsed, 0), 250)
        events = pygame.event.get()
        converted = []
        width, height = self.window.get_size()
        for event in events:
            if hasattr(event, 'pos'):
                event = pygame.event.Event(event.type, {**event.dict,
                    'pos': (event.pos[0] * 800 / width, event.pos[1] * 800 / height)})
                self.mouse = event.pos
            converted.append(event)
        self.events(converted, elapsed)
        if not self.running:
            return False
        self.update_transition(elapsed)
        self.render()
        if self.window.get_size() == (800, 800):
            self.window.blit(self.surface, (0, 0))
        else:
            pygame.transform.scale(self.surface, self.window.get_size(), self.window)
        pygame.display.flip()
        return True

    def run(self):
        while self.frame(self.clock.tick(self.config['window']['fps'])):
            pass

    def close(self):
        pygame.key.stop_text_input()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description='Slovenský geografický kvíz')
    parser.add_argument('--seed', type=int, help='repeat a question order for testing')
    args = parser.parse_args()
    game = None
    try:
        game = Game(seed=args.seed)
        game.run()
    except (OSError, ValueError, pygame.error) as error:
        parser.exit(1, f'Cannot start quiz: {error}\n')
    finally:
        if game is not None:
            game.close()


if __name__ == '__main__':
    main()
