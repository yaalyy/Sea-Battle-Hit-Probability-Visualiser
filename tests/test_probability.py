import unittest
from unittest.mock import patch
from probability import ProbabilityEngine
from fleet import CellState, FleetConfig
from ship import ShipSpec, ConfirmedSunkShip


class ProbabilityEngineTests(unittest.TestCase):
    def test_single_ship_placements_on_small_board(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

        result = engine.evaluate(
            [
                [CellState.UNKNOWN, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN],
            ]
        )

        self.assertEqual(result.remaining_arrangements, 4)
        self.assertEqual(result.total_arrangements, 4)
        self.assertEqual(result.probabilities, [[0.5, 0.5], [0.5, 0.5]])

    def test_multiple_ships_cannot_overlap_but_can_touch(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(1, 2)]))

        result = engine.evaluate(
            [
                [CellState.UNKNOWN, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN],
            ]
        )

        self.assertEqual(result.remaining_arrangements, 6)
        self.assertEqual(result.total_arrangements, 6)
        self.assertEqual(result.probabilities, [[0.5, 0.5], [0.5, 0.5]])

    def test_best_cell_uses_configured_probability_when_probabilities_tie(self):
        original_probability = ProbabilityEngine.RANDOM_SELECTION_PROBABILITY
        ProbabilityEngine.RANDOM_SELECTION_PROBABILITY = 0.75

        try:
            engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

            with patch("probability.random.random", side_effect=[0.8, 0.2, 0.9]):
                result = engine.evaluate(
                    [
                        [CellState.UNKNOWN, CellState.UNKNOWN],
                        [CellState.UNKNOWN, CellState.UNKNOWN],
                    ]
                )
        finally:
            ProbabilityEngine.RANDOM_SELECTION_PROBABILITY = original_probability

        self.assertEqual(result.probabilities, [[0.5, 0.5], [0.5, 0.5]])
        self.assertEqual(result.best_cell, (1, 0))

    def test_zero_tie_break_probability_keeps_first_matching_best_cell(self):
        original_probability = ProbabilityEngine.RANDOM_SELECTION_PROBABILITY
        ProbabilityEngine.RANDOM_SELECTION_PROBABILITY = 0.0

        try:
            engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

            result = engine.evaluate(
                [
                    [CellState.UNKNOWN, CellState.UNKNOWN],
                    [CellState.UNKNOWN, CellState.UNKNOWN],
                ]
            )
        finally:
            ProbabilityEngine.RANDOM_SELECTION_PROBABILITY = original_probability

        self.assertEqual(result.best_cell, (0, 0))

    def test_full_tie_break_probability_keeps_last_matching_best_cell(self):
        original_probability = ProbabilityEngine.RANDOM_SELECTION_PROBABILITY
        ProbabilityEngine.RANDOM_SELECTION_PROBABILITY = 1.0

        try:
            engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

            result = engine.evaluate(
                [
                    [CellState.UNKNOWN, CellState.UNKNOWN],
                    [CellState.UNKNOWN, CellState.UNKNOWN],
                ]
            )
        finally:
            ProbabilityEngine.RANDOM_SELECTION_PROBABILITY = original_probability

        self.assertEqual(result.best_cell, (1, 1))

    def test_miss_excludes_arrangements_containing_that_cell(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

        result = engine.evaluate(
            [
                [CellState.MISS, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN],
            ]
        )

        self.assertEqual(result.remaining_arrangements, 2)
        self.assertEqual(result.probabilities[0][0], 0.0)
        self.assertEqual(result.probabilities[0][1], 0.5)
        self.assertEqual(result.probabilities[1][0], 0.5)
        self.assertEqual(result.probabilities[1][1], 1.0)
        self.assertEqual(result.best_cell, (1, 1))

    def test_hit_keeps_only_arrangements_covering_that_cell(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

        result = engine.evaluate(
            [
                [CellState.HIT, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN],
            ]
        )

        self.assertEqual(result.remaining_arrangements, 2)
        self.assertEqual(result.probabilities[0][0], 1.0)
        self.assertEqual(result.probabilities[0][1], 0.5)
        self.assertEqual(result.probabilities[1][0], 0.5)
        self.assertEqual(result.probabilities[1][1], 0.0)

    def test_combined_hits_and_misses_filter_to_single_arrangement(self):
        engine = ProbabilityEngine(FleetConfig(3, 3, [ShipSpec(2, 1)]))

        result = engine.evaluate(
            [
                [CellState.HIT, CellState.MISS, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
            ]
        )

        self.assertEqual(result.remaining_arrangements, 1)
        self.assertEqual(result.probabilities[0][0], 1.0)
        self.assertEqual(result.probabilities[1][0], 1.0)
        self.assertEqual(result.best_cell, (1, 0))

    def test_dict_input_treats_unspecified_cells_as_unknown(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

        result = engine.evaluate({(0, 0): CellState.MISS})

        self.assertEqual(result.remaining_arrangements, 2)
        self.assertEqual(result.probabilities[0][0], 0.0)
        self.assertEqual(result.probabilities[1][1], 1.0)
        self.assertEqual(result.best_cell, (1, 1))

    def test_string_cell_states_are_normalized(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

        result = engine.evaluate(
            [
                ["x", " "],
                ["m", ""],
            ]
        )

        self.assertEqual(result.remaining_arrangements, 1)
        self.assertEqual(result.probabilities, [[1.0, 1.0], [0.0, 0.0]])

    def test_no_legal_arrangements_returns_empty_result(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

        result = engine.evaluate(
            [
                [CellState.HIT, CellState.MISS],
                [CellState.MISS, CellState.UNKNOWN],
            ]
        )

        self.assertEqual(result.remaining_arrangements, 0)
        self.assertIsNone(result.best_cell)
        self.assertEqual(result.best_probability, 0.0)
        self.assertEqual(result.probabilities, [[0.0, 0.0], [0.0, 0.0]])

    def test_rejects_cell_state_matrix_with_wrong_shape(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

        with self.assertRaises(ValueError):
            engine.evaluate([[CellState.UNKNOWN]])

        with self.assertRaises(ValueError):
            engine.evaluate(
                [
                    [CellState.UNKNOWN, CellState.UNKNOWN],
                    [CellState.UNKNOWN],
                ]
            )

    def test_rejects_unsupported_cell_state(self):
        engine = ProbabilityEngine(FleetConfig(2, 2, [ShipSpec(2, 1)]))

        with self.assertRaises(ValueError):
            engine.evaluate(
                [
                    [CellState.UNKNOWN, "bad"],
                    [CellState.UNKNOWN, CellState.UNKNOWN],
                ]
            )

    def test_confirmed_sunk_ship_is_removed_from_remaining_fleet(self):
        engine = ProbabilityEngine(FleetConfig(6, 1, [ShipSpec(3, 1), ShipSpec(2, 1)]))

        result = engine.evaluate(
            [
                [
                    CellState.SUNK,
                    CellState.SUNK,
                    CellState.SUNK,
                    CellState.HIT,
                    CellState.UNKNOWN,
                    CellState.UNKNOWN,
                ],
            ],
            sunk_ships=[ConfirmedSunkShip([(0, 0), (0, 1), (0, 2)])],
        )

        self.assertEqual(result.remaining_arrangements, 1)
        self.assertEqual(result.probabilities[0][0], 1.0)
        self.assertEqual(result.probabilities[0][1], 1.0)
        self.assertEqual(result.probabilities[0][2], 1.0)
        self.assertEqual(result.probabilities[0][3], 1.0)
        self.assertEqual(result.probabilities[0][4], 1.0)
        self.assertEqual(result.probabilities[0][5], 0.0)
        self.assertEqual(result.best_cell, (0, 4))

    def test_confirmed_sunk_ship_can_be_supplied_as_cells(self):
        engine = ProbabilityEngine(FleetConfig(3, 1, [ShipSpec(2, 1), ShipSpec(1, 1)]))

        result = engine.evaluate(
            [[CellState.SUNK, CellState.SUNK, CellState.UNKNOWN]],
            sunk_ships=[[(0, 0), (0, 1)]],
        )

        self.assertEqual(result.remaining_arrangements, 1)
        self.assertEqual(result.probabilities[0], [1.0, 1.0, 1.0])
        self.assertEqual(result.best_cell, (0, 2))

    def test_rejects_sunk_ship_overlapping_a_miss(self):
        engine = ProbabilityEngine(FleetConfig(3, 1, [ShipSpec(2, 1)]))

        with self.assertRaises(ValueError):
            engine.evaluate(
                [[CellState.MISS, CellState.SUNK, CellState.UNKNOWN]],
                sunk_ships=[ConfirmedSunkShip([(0, 0), (0, 1)])],
            )

    def test_rejects_more_confirmed_sunk_ships_than_fleet_contains(self):
        engine = ProbabilityEngine(FleetConfig(3, 1, [ShipSpec(1, 1)]))

        with self.assertRaises(ValueError):
            engine.evaluate(
                [[CellState.SUNK, CellState.SUNK, CellState.UNKNOWN]],
                sunk_ships=[
                    ConfirmedSunkShip([(0, 0)]),
                    ConfirmedSunkShip([(0, 1)]),
                ],
            )

    def test_rejects_overlapping_confirmed_sunk_ships(self):
        engine = ProbabilityEngine(FleetConfig(4, 1, [ShipSpec(2, 2)]))

        with self.assertRaises(ValueError):
            engine.evaluate(
                [[CellState.SUNK, CellState.SUNK, CellState.SUNK, CellState.UNKNOWN]],
                sunk_ships=[
                    ConfirmedSunkShip([(0, 0), (0, 1)]),
                    ConfirmedSunkShip([(0, 1), (0, 2)]),
                ],
            )

    def test_exact_limit_falls_back_to_sampling(self):
        original_limit = ProbabilityEngine.MAX_EXACT_ARRANGEMENTS
        original_sample_target = ProbabilityEngine.SAMPLE_TARGET
        original_sample_attempts = ProbabilityEngine.SAMPLE_ATTEMPTS
        ProbabilityEngine.MAX_EXACT_ARRANGEMENTS = 1
        ProbabilityEngine.SAMPLE_TARGET = 5
        ProbabilityEngine.SAMPLE_ATTEMPTS = 50
        try:
            engine = ProbabilityEngine(FleetConfig(3, 3, [ShipSpec(2, 1), ShipSpec(1, 1)]))
            result = engine.evaluate(
                [
                    [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
                    [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
                    [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
                ],
            )
        finally:
            ProbabilityEngine.MAX_EXACT_ARRANGEMENTS = original_limit
            ProbabilityEngine.SAMPLE_TARGET = original_sample_target
            ProbabilityEngine.SAMPLE_ATTEMPTS = original_sample_attempts

        self.assertFalse(result.exact)
        self.assertTrue(result.limit_reached)
        self.assertEqual(result.remaining_arrangements, 5)
        self.assertIsNone(result.total_arrangements)

    def test_cached_arrangements_are_reused_across_cell_updates(self):
        engine = ProbabilityEngine(FleetConfig(3, 3, [ShipSpec(2, 1)]))

        first = engine.evaluate(
            [
                [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
            ],
        )
        cached_masks = engine._fleet_mask_cache

        second = engine.evaluate(
            [
                [CellState.MISS, CellState.UNKNOWN, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
                [CellState.UNKNOWN, CellState.UNKNOWN, CellState.UNKNOWN],
            ],
        )

        self.assertIs(engine._fleet_mask_cache, cached_masks)
        self.assertEqual(first.total_arrangements, 12)
        self.assertEqual(second.total_arrangements, 12)
        self.assertLess(second.remaining_arrangements, first.remaining_arrangements)


if __name__ == "__main__":
    unittest.main()
