import unittest

from board import Board
from fleet import FleetConfig
from ship import ShipSpec


class FleetConfigTests(unittest.TestCase):
    def test_requires_at_least_one_ship_type(self):
        with self.assertRaises(ValueError):
            FleetConfig(3, 3, [])

    def test_rejects_non_ship_specs(self):
        with self.assertRaises(TypeError):
            FleetConfig(3, 3, [(2, 1)])

    def test_rejects_ship_that_cannot_fit_on_board(self):
        with self.assertRaises(ValueError):
            FleetConfig(2, 2, [ShipSpec(3, 1)])

    def test_rejects_fleet_exceeding_board_capacity(self):
        with self.assertRaises(ValueError):
            FleetConfig(2, 2, [ShipSpec(2, 3)])

    def test_rejects_board_dimensions_above_maximum(self):
        with self.assertRaises(ValueError):
            FleetConfig(Board.MAXIMUM_WIDTH + 1, 1, [ShipSpec(1, 1)])

    def test_stores_ship_specs_as_tuple(self):
        spec = ShipSpec(2, 1)

        config = FleetConfig(3, 3, [spec])

        self.assertEqual(config.ships, (spec,))

