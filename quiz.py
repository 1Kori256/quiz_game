"""Question selection and scoring, independent of the UI."""

from dataclasses import dataclass
from pathlib import Path
import random
from unidecode import unidecode


def normalize(text):
    return ''.join(char for char in unidecode(text).casefold() if char.isalnum())


@dataclass(frozen=True)
class Country:
    name: str
    region: str
    capital: str

    @property
    def answer_key(self):
        return normalize(self.capital)


def load_countries(path):
    countries = {}
    region = None
    for number, raw in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if ' - ' not in raw:
            region = line
            continue
        name, capital = (part.strip() for part in raw.split(' - ', 1))
        if not region or not name or not capital or name in countries:
            raise ValueError(f'Invalid or duplicate country on line {number}')
        countries[name] = Country(name, region, capital)
    if not countries:
        raise ValueError('No countries found')
    return countries


@dataclass(frozen=True)
class Answer:
    country: Country
    given: str
    correct: bool


class QuizSession:
    def __init__(self, countries, count=10, region=None, rng=None):
        pool = [country for country in countries.values() if region is None or country.region == region]
        if not pool or (count is not None and count < 1):
            raise ValueError('Select a nonempty region and a positive question count')
        self.questions = (rng or random.Random()).sample(pool, min(count or len(pool), len(pool)))
        capitals = {}
        for country in pool:
            capitals.setdefault(country.answer_key, country.capital)
        self.search_index = [(capital, key) for key, capital in capitals.items()]
        self.index = 0
        self.answers = []
        self.pending = None

    @property
    def finished(self):
        return self.index >= len(self.questions)

    @property
    def current(self):
        return None if self.finished else self.questions[self.index]

    @property
    def score(self):
        return sum(answer.correct for answer in self.answers)

    def suggestions(self, text, limit=4):
        key = normalize(text)
        if len(key) < 3:
            return []
        matches = [(capital, candidate) for capital, candidate in self.search_index if key in candidate]
        matches.sort(key=lambda item: not item[1].startswith(key))
        return [capital for capital, _ in matches[:limit]]

    def submit(self, answer):
        if self.finished or self.pending is not None or not normalize(answer):
            return None
        self.pending = Answer(self.current, answer, normalize(answer) == self.current.answer_key)
        self.answers.append(self.pending)
        return self.pending

    def advance(self):
        if self.pending is not None:
            self.index += 1
            self.pending = None
