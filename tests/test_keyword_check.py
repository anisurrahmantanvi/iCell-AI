import unittest

from ecosystem.evals.runner import keyword_check


class KeywordCheckTests(unittest.TestCase):
    def test_plain_words(self):
        self.assertEqual(keyword_check(["risk", "code"], "A risk in the CODE"), 1.0)
        self.assertEqual(keyword_check(["risk", "code"], "only a risk"), 0.5)

    def test_alternatives_any_one_counts(self):
        req = [["stop", "halt"]]
        self.assertEqual(keyword_check(req, "It will halt the system"), 1.0)
        self.assertEqual(keyword_check(req, "It pauses things"), 0.0)

    def test_stem_matches_longer_word(self):
        self.assertEqual(keyword_check([["compar"]], "make a comparison"), 1.0)

    def test_no_requirements_is_full_score(self):
        self.assertEqual(keyword_check([], "anything"), 1.0)


if __name__ == "__main__":
    unittest.main()
