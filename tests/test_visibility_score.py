"""Regression coverage for the canonical visibility-score model."""
import unittest
from unittest.mock import patch

from antek_geo_core.scoring import composite_score


class VisibilityScoreTests(unittest.TestCase):
    def test_recommendation_rate_does_not_overstate_binary_engine_coverage(self):
        engines = ["e1", "e2", "e3", "e4", "e5"]
        queries = [f"q{i}" for i in range(8)]
        grid = {e: {q: False for q in queries} for e in engines}
        for engine, query in zip(engines[:4], queries[:4]):
            grid[engine][query] = True
        grid["e1"]["q4"] = True

        result = composite_score(grid, engines, queries)
        self.assertEqual(result, {
            "composite": 12.5,
            "platforms_tested": 5,
            "platforms_mentioned": 4,
            "prompts_total": 40,
            "prompts_mentioned": 5,
        })

    def test_recommendation_rate_extremes(self):
        engines, queries = ["e1", "e2"], ["q1", "q2"]
        all_hits = {e: {q: True for q in queries} for e in engines}
        no_hits = {e: {q: False for q in queries} for e in engines}
        self.assertEqual(composite_score(all_hits, engines, queries)["composite"], 100.0)
        self.assertEqual(composite_score(no_hits, engines, queries)["composite"], 0.0)

    def test_proportional_breadth_blend_handles_uneven_answer_counts(self):
        engines = ["A", "B"]
        queries = list(range(10))
        grid = {
            "A": {q: (True if q < 2 else None) for q in queries},
            "B": {q: (False if q >= 2 else None) for q in queries},
        }
        with patch("antek_geo_core.scoring.DEPTH_WEIGHT", 0.5), patch(
            "antek_geo_core.scoring.BREADTH_WEIGHT", 0.5
        ):
            # cell rate = 2/10; proportional breadth = mean(2/2, 0/8) = 1/2.
            self.assertEqual(composite_score(grid, engines, queries)["composite"], 35.0)

    def test_repository_call_sites_match_core_for_the_same_grid(self):
        import sys
        sys.path.insert(0, "/data/workspaces/worker/geo-prospecting")
        sys.path.insert(0, "/data/workspaces/worker/geo-slab/scripts")
        from src.visibility.score import _score_grid as prospecting_score
        from visibility_check import _score_grid as slab_score

        engines, queries = ["A", "B"], ["q1", "q2"]
        grid = {
            "A": {"q1": True, "q2": False},
            "B": {"q1": False, "q2": None},
        }
        expected = composite_score(grid, engines, queries)
        self.assertEqual(prospecting_score(grid, engines, queries), expected)
        self.assertEqual(slab_score(grid, engines, queries), expected)

    def test_no_tested_platforms_raises(self):
        with self.assertRaisesRegex(ValueError, "No engine returned an answer"):
            composite_score({"e1": {"q1": None}}, ["e1"], ["q1"])


if __name__ == "__main__":
    unittest.main()
