"""Measure cached UI drawing, excluding display updates and the frame cap."""

import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import Game


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=600)
    args = parser.parse_args()
    if args.frames < 1:
        parser.error('--frames must be positive')
    game = Game(seed=1)
    try:
        samples = []
        for frame in range(args.frames + 30):
            start = time.perf_counter()
            game.render()
            if frame >= 30:
                samples.append((time.perf_counter() - start) * 1000)
        print(json.dumps({'frames': args.frames, 'menu_draw_median_ms':
                          round(statistics.median(samples), 3)}, indent=2))
    finally:
        game.close()


if __name__ == '__main__':
    main()
