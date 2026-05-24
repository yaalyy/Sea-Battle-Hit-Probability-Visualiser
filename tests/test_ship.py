import unittest

from ship import ConfirmedSunkShip, ShipSpec


class ShipSpecTests(unittest.TestCase):
    def test_rejects_non_positive_length_or_count(self):
        with self.assertRaises(ValueError):
            ShipSpec(0, 1)
        with self.assertRaises(ValueError):
            ShipSpec(1, 0)

    def test_equality_uses_length_and_count(self):
        self.assertEqual(ShipSpec(3, 2), ShipSpec(3, 2))
        self.assertNotEqual(ShipSpec(3, 2), ShipSpec(2, 3))


class ConfirmedSunkShipTests(unittest.TestCase):
    def test_sorts_cells_and_reports_length(self):
        ship = ConfirmedSunkShip([(0, 2), (0, 0), (0, 1)])

        self.assertEqual(ship.cells, ((0, 0), (0, 1), (0, 2)))
        self.assertEqual(ship.length, 3)

    def test_rejects_empty_ship(self):
        with self.assertRaises(ValueError):
            ConfirmedSunkShip([])

    def test_rejects_bent_ship(self):
        with self.assertRaises(ValueError):
            ConfirmedSunkShip([(0, 0), (0, 1), (1, 1)])

    def test_rejects_non_contiguous_ship(self):
        with self.assertRaises(ValueError):
            ConfirmedSunkShip([(0, 0), (0, 2)])
