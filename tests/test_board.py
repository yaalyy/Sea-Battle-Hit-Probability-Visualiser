import unittest

from board import BattleBoard, Board


class BoardTests(unittest.TestCase):
    def test_board_rejects_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            Board(0, 1)
        with self.assertRaises(ValueError):
            Board(1, 0)
        with self.assertRaises(ValueError):
            Board(Board.MAXIMUM_WIDTH + 1, 1)
        with self.assertRaises(ValueError):
            Board(1, Board.MAXIMUM_HEIGHT + 1)

    def test_valid_coordinate_checks_board_bounds(self):
        board = Board(3, 2)

        self.assertTrue(board.is_valid_coordinate(0, 0))
        self.assertTrue(board.is_valid_coordinate(1, 2))
        self.assertFalse(board.is_valid_coordinate(-1, 0))
        self.assertFalse(board.is_valid_coordinate(2, 0))
        self.assertFalse(board.is_valid_coordinate(0, 3))

        with self.assertRaises(ValueError):
            board.require_valid_coordinate(2, 0)


class BattleBoardTests(unittest.TestCase):
    def test_marking_hit_and_miss_updates_state_lists(self):
        board = BattleBoard(2, 2)

        board.mark_hit(0, 1)
        self.assertEqual(board.get_state(0, 1), BattleBoard.HIT)
        self.assertEqual(board.hit_list, [(0, 1)])
        self.assertEqual(board.miss_list, [])

        board.mark_miss(0, 1)
        self.assertEqual(board.get_state(0, 1), BattleBoard.MISS)
        self.assertEqual(board.hit_list, [])
        self.assertEqual(board.miss_list, [(0, 1)])

    def test_mark_sunk_counts_as_hit_and_removes_miss(self):
        board = BattleBoard(2, 2)

        board.mark_miss(1, 1)
        board.mark_sunk(1, 1)

        self.assertEqual(board.get_state(1, 1), BattleBoard.SUNK)
        self.assertEqual(board.hit_list, [(1, 1)])
        self.assertEqual(board.miss_list, [])

    def test_clear_mark_resets_state_and_tracking_lists(self):
        board = BattleBoard(2, 2)

        board.mark_hit(0, 0)
        board.clear_mark(0, 0)

        self.assertEqual(board.get_state(0, 0), BattleBoard.UNKNOWN)
        self.assertEqual(board.hit_list, [])
        self.assertEqual(board.miss_list, [])

    def test_cycle_state_rotates_unknown_hit_miss_unknown(self):
        board = BattleBoard(2, 2)

        self.assertEqual(board.cycle_state(0, 0), BattleBoard.HIT)
        self.assertEqual(board.cycle_state(0, 0), BattleBoard.MISS)
        self.assertEqual(board.cycle_state(0, 0), BattleBoard.UNKNOWN)
        self.assertEqual(board.get_state(0, 0), BattleBoard.UNKNOWN)

    def test_set_state_rejects_unsupported_state(self):
        board = BattleBoard(2, 2)

        with self.assertRaises(ValueError):
            board.set_state(0, 0, "bad")

