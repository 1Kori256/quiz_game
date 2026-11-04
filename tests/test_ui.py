import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import tempfile
import unittest
from unittest.mock import patch
import pygame
from main import Game
from quiz import Country, QuizSession
from widgets import Button


class UITests(unittest.TestCase):
    def setUp(self):
        self.game = Game(seed=1)
        pygame.event.clear()

    def tearDown(self):
        self.game.close()

    def settle(self):
        for _ in range(60):
            if self.game.transition is None:
                return
            self.game.frame(1000 / 60)
        self.fail('Transition did not finish')

    def start(self, count=10):
        self.game.count_index = self.game.counts.index(count)
        self.game.start_round()
        self.settle()
        self.assertEqual(self.game.state, 'game')

    def enter(self, answer):
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=answer))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.game.frame(1000 / 60)

    def test_complete_round_shows_final_score_and_replay_resets(self):
        self.start(5)
        for _ in range(5):
            self.enter(self.game.session.current.capital)
            self.settle()
        self.assertEqual(self.game.state, 'results')
        self.assertEqual(self.game.session.score, 5)
        old_session = self.game.session
        self.game.start_round()
        self.assertIs(self.game.session, old_session)
        self.assertEqual(self.game.session.score, 5)
        self.settle()
        self.assertEqual(self.game.state, 'game')
        self.assertEqual(self.game.session.score, 0)
        self.assertEqual(self.game.input.text, '')
        self.assertTrue(self.game.input.active)

    def test_repeated_enter_during_feedback_cannot_double_score(self):
        self.start(5)
        self.enter(self.game.session.current.capital)
        for _ in range(5):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.game.frame(20)
        self.assertEqual(len(self.game.session.answers), 1)
        self.assertEqual(self.game.session.score, 1)
        self.settle()
        self.assertEqual(self.game.session.index, 1)

    def test_wrong_typed_answer_shows_feedback(self):
        self.start(5)
        self.enter('wrong')
        self.assertFalse(self.game.session.pending.correct)
        self.assertEqual(self.game.input.color, (255, 0, 0))
        self.assertEqual(len(self.game.session.answers), 1)

    def test_suggestion_click_submits_once(self):
        self.start(5)
        capital = self.game.session.current.capital
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=capital))
        self.game.frame(16)
        button = next(button for button in self.game.suggestion_buttons if button.text == capital)
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(event_type, button=1, pos=button.rect.center))
            self.game.frame(16)
        self.assertEqual(self.game.session.score, 1)
        self.settle()
        self.assertEqual(len(self.game.session.answers), 1)

    def test_long_capital_and_exact_input_limit(self):
        self.start(5)
        capital = 'Šrí Džajavardanapura Kotte'
        self.game.session.questions = [Country('Srí Lanka', 'Ázia', capital)]
        self.enter(capital)
        self.assertTrue(self.game.session.pending.correct)
        self.settle()
        self.game.input.clear()
        event = pygame.event.Event(pygame.TEXTINPUT, text='a' * 100)
        self.game.input.update([event], 0, (0, 0))
        self.assertEqual(len(self.game.input.text), self.game.input.max_characters)

    def test_inactive_input_does_not_repeat_backspace(self):
        self.start(5)
        self.game.input.text = 'Bratislava'
        events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0)]
        self.game.input.update(events, 0, (0, 0))
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))]
        self.game.input.update(events, 200, (0, 0))
        self.assertEqual(self.game.input.text, 'Bratislav')
        self.assertFalse(self.game.input.backspace_pressed)

    def test_focus_loss_releases_backspace(self):
        self.start(5)
        self.game.input.text = 'Bratislava'
        self.game.input.backspace_pressed = True
        event = pygame.event.Event(pygame.WINDOWFOCUSLOST)
        self.game.input.update([event], 200, (0, 0))
        self.assertEqual(self.game.input.text, 'Bratislava')

    def test_ctrl_backspace_clears_text(self):
        self.start(5)
        self.game.input.text = 'Bratislava'
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=pygame.KMOD_CTRL)
        self.game.input.update([event], 0, (0, 0))
        self.assertEqual(self.game.input.text, '')

    def test_settings_change_the_question_pool(self):
        self.game.region_index = self.game.regions.index('Európa')
        self.start(20)
        self.assertTrue(all(country.region == 'Európa' for country in self.game.session.questions))
        self.assertEqual(len(self.game.session.questions), 20)

    def test_settings_buttons_work_through_click_events(self):
        def click(point):
            for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                pygame.event.post(pygame.event.Event(event_type, button=1, pos=point))
            self.game.frame(16)
        click((400, 375))
        self.settle()
        self.assertEqual(self.game.state, 'settings')
        click((400, 300))
        click((400, 375))
        self.assertEqual(self.game.regions[self.game.region_index], 'Afrika')
        self.assertEqual(self.game.counts[self.game.count_index], 20)
        click((400, 675))
        self.settle()
        click((400, 300))
        self.settle()
        self.assertEqual(len(self.game.session.questions), 20)
        self.assertTrue(all(country.region == 'Afrika' for country in self.game.session.questions))

    def test_button_needs_matching_press_and_release(self):
        button = Button(self.game.font, 'Test')
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)),
                  pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=button.rect.center)]
        button.update(events, button.rect.center, 16)
        self.assertFalse(button.clicked)
        events[0].pos = button.rect.center
        button.update(events, button.rect.center, 16)
        self.assertTrue(button.clicked)
        button.update([], button.rect.center, 16, enabled=False)
        self.assertFalse(button.clicked)

    def test_quit_during_transition_does_not_render(self):
        self.game.start_round()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        with patch.object(self.game, 'render') as render:
            self.assertFalse(self.game.frame(16))
            render.assert_not_called()

    def test_assets_resolve_from_another_directory(self):
        previous = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                game = Game()
                game.frame(16)
                game.close()
        finally:
            os.chdir(previous)

    def test_static_render_does_not_allocate_control_surfaces(self):
        self.game.render()
        with patch('pygame.Surface', side_effect=AssertionError('unexpected allocation')):
            self.game.render()

    def test_scaled_window_maps_button_events(self):
        self.game.window = pygame.display.set_mode((400, 400))
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(event_type, button=1, pos=(200, 150)))
        self.game.frame(16)
        self.assertIsNotNone(self.game.transition)
        self.assertEqual(self.game.transition['target'], 'game')
