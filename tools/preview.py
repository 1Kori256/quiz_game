"""Save menu, question, and results screenshots from the actual UI."""

import argparse
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
from main import Game


def settle(game):
    for _ in range(120):
        if game.transition is None:
            return
        game.frame(1000 / 60)
    raise RuntimeError('Transition did not finish')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    game = Game(seed=1)
    try:
        game.render()
        pygame.image.save(game.surface, str(args.output / 'menu.png'))
        game.start_round()
        settle(game)
        game.input.text = game.session.current.capital[:3]
        game.update_suggestions()
        game.render()
        pygame.image.save(game.surface, str(args.output / 'preview.png'))
        total = len(game.session.questions)
        for index in range(total):
            answer = game.session.current.capital if index % 2 == 0 else 'Neviem'
            game.submit(answer)
            settle(game)
        game.render()
        pygame.image.save(game.surface, str(args.output / 'results.png'))
        print(args.output)
    finally:
        game.close()


if __name__ == '__main__':
    main()
