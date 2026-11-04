import random
from pathlib import Path
import tempfile
import unittest
from quiz import Country, QuizSession, load_countries, normalize

ROOT = Path(__file__).resolve().parents[1]


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.countries = load_countries(ROOT / 'data/countries_svk.txt')

    def test_normalization(self):
        for a, b in (('  PARÍŽ ', 'pariz'), ('Washington D.C.', 'Washington DC'),
                     ('Port-au-Prince', 'port au prince'), ('N’Djamena', 'ndjamena')):
            self.assertEqual(normalize(a), normalize(b))

    def test_unique_repeatable_questions(self):
        a = QuizSession(self.countries, rng=random.Random(3))
        b = QuizSession(self.countries, rng=random.Random(3))
        self.assertEqual(a.questions, b.questions)
        self.assertEqual(len({country.name for country in a.questions}), 10)

    def test_region_filter_and_all_questions(self):
        session = QuizSession(self.countries, count=None, region='Európa')
        self.assertTrue(all(country.region == 'Európa' for country in session.questions))
        self.assertEqual(len(session.questions), sum(c.region == 'Európa' for c in self.countries.values()))

    def test_small_dataset_does_not_crash(self):
        session = QuizSession({'test': Country('Test', 'Region', 'Capital')}, count=10)
        self.assertEqual(len(session.questions), 1)
        for count, region in ((0, None), (-1, None), (10, 'Missing')):
            with self.assertRaises(ValueError):
                QuizSession(self.countries, count, region)

    def test_duplicate_submission_is_ignored_until_advance(self):
        session = QuizSession(self.countries, count=2)
        answer = session.current.capital
        self.assertTrue(session.submit(answer).correct)
        for _ in range(10):
            self.assertIsNone(session.submit(answer))
        self.assertEqual(session.score, 1)
        self.assertEqual(len(session.answers), 1)
        session.advance()
        self.assertIsNotNone(session.submit(session.current.capital))
        self.assertEqual(session.score, 2)

    def test_wrong_answer_counts_once(self):
        session = QuizSession(self.countries, count=1)
        self.assertFalse(session.submit('definitely wrong').correct)
        self.assertEqual((session.score, len(session.answers)), (0, 1))
        session.advance()
        self.assertTrue(session.finished)
        self.assertIsNone(session.current)
        self.assertIsNone(session.submit('anything'))
        session.advance()
        self.assertEqual(session.index, 1)

    def test_empty_answer_is_not_scored(self):
        session = QuizSession(self.countries)
        for text in ('', '   ', '...'):
            self.assertIsNone(session.submit(text))
        self.assertEqual(session.answers, [])
        session.advance()
        self.assertEqual(session.index, 0)

    def test_suggestions_are_unique_and_prefixes_come_first(self):
        pool = {name: Country(name, 'Region', capital) for name, capital in
                (('A', 'New Town'), ('B', 'Townsville'), ('C', 'Townsville'), ('D', 'Tównsville'))}
        session = QuizSession(pool)
        self.assertEqual(session.suggestions('town'), ['Townsville', 'New Town'])
        self.assertEqual(session.suggestions('to'), [])
        self.assertEqual(session.suggestions('town', limit=1), ['Townsville'])

    def test_typed_answer_works_when_several_suggestions_match(self):
        pool = {name: Country(name, 'Region', capital) for name, capital in
                (('A', 'Port'), ('B', 'Port Louis'), ('C', 'Porto-Novo'))}
        session = QuizSession(pool)
        session.questions = [pool['A']]
        self.assertGreater(len(session.suggestions('Port')), 1)
        self.assertTrue(session.submit('Port').correct)

    def test_scores_are_independent_between_rounds(self):
        first = QuizSession(self.countries, count=1)
        first.submit(first.current.capital)
        first.advance()
        second = QuizSession(self.countries, count=1)
        self.assertEqual(first.score, 1)
        self.assertEqual((second.score, len(second.answers)), (0, 0))


class DataTests(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'countries.txt'
            path.write_text(text, encoding='utf-8')
            return load_countries(path)

    def test_blank_lines_and_hyphenated_names(self):
        data = self.load('\ufeffAfrika\n\nGuinea-Bissau - Bissau\nČad - N\'Djamena\n')
        self.assertEqual(data['Guinea-Bissau'].capital, 'Bissau')
        self.assertEqual(data['Čad'].region, 'Afrika')

    def test_invalid_or_duplicate_records(self):
        for text in ('', 'Country - Capital', 'Region\nCountry - ',
                     'Region\n - Capital', 'Region\nCountry - A\nCountry - B'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.load(text)

    def test_bundled_data_loads_all_regions(self):
        data = load_countries(ROOT / 'data/countries_svk.txt')
        self.assertEqual(len({c.region for c in data.values()}), 5)
        self.assertGreater(len(data), 190)
        self.assertEqual(data['Kazachstan'].capital, 'Astana')
