import unittest

from ecosystem.evals.runner import check_answer, keyword_check


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

    def test_word_limit_counts_as_one_requirement(self):
        task = {"must_contain": ["391"], "max_words": 5}
        self.assertEqual(check_answer(task, "391"), 1.0)                       # keyword ok, short enough
        self.assertEqual(check_answer(task, "391 " + "word " * 10), 0.5)        # keyword ok, too long
        self.assertEqual(check_answer(task, "no number here"), 0.5)             # short, keyword missing
        self.assertEqual(check_answer(task, "nothing " * 10), 0.0)

    def test_limit_only_and_neither(self):
        self.assertEqual(check_answer({"max_words": 3}, "a b"), 1.0)
        self.assertEqual(check_answer({"max_words": 3}, "a b c d"), 0.0)
        self.assertEqual(check_answer({}, "anything"), 1.0)

    def test_fragmented_answer_is_caught_by_paragraph_limit(self):
        # the live 17*23 answer: correct (391) and short (9 words) but chopped into 3 joined steps.
        # The word limit alone does not flag it; the paragraph limit does.
        live = "340 + 51 = 391\n\n51\n\n391"
        self.assertEqual(check_answer({"must_contain": ["391"], "max_words": 20}, live), 1.0)
        both = {"must_contain": ["391"], "max_words": 20, "max_paragraphs": 1}
        self.assertAlmostEqual(check_answer(both, live), 2 / 3)
        self.assertEqual(check_answer(both, "17 * 23 = 391."), 1.0)

    def test_padded_answer_is_caught_by_word_limit(self):
        task = {"must_contain": ["391"], "max_words": 20}
        padded = "391 " + "blah " * 40
        self.assertEqual(check_answer(task, padded), 0.5)

    def test_paragraph_counting(self):
        task = {"max_paragraphs": 2}
        self.assertEqual(check_answer(task, "one\n\ntwo"), 1.0)
        self.assertEqual(check_answer(task, "one\n\ntwo\n\nthree"), 0.0)
        self.assertEqual(check_answer(task, "one\ntwo\nthree"), 1.0)   # single newlines stay one block
        self.assertEqual(check_answer(task, "one\n \n\n  two"), 1.0)  # whitespace-only gaps still separate


if __name__ == "__main__":
    unittest.main()
