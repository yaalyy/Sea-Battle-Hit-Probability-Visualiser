class ShipSpec:
    """ config of a ship type, defined by its length and count in the fleet """
    def __init__(self, length, count):
        if length <= 0:
            raise ValueError("Ship length must be positive.")
        if count <= 0:
            raise ValueError("Ship count must be positive.")
        self.length = length
        self.count = count

    def __repr__(self):
        return f"ShipSpec(length={self.length!r}, count={self.count!r})"

    def __eq__(self, other):
        return (
            isinstance(other, ShipSpec)
            and self.length == other.length
            and self.count == other.count
        )


class ConfirmedSunkShip:
    def __init__(self, cells):
        self.cells = tuple(sorted(cells))
        self._validate_shape()

    @property
    def length(self):
        return len(self.cells)

    def __repr__(self):
        return f"ConfirmedSunkShip(cells={self.cells!r})"

    def __eq__(self, other):
        return isinstance(other, ConfirmedSunkShip) and self.cells == other.cells

    def _validate_shape(self):
        """ check if ship shape is a straight line of contiguous cells """
        
        if not self.cells:
            raise ValueError("A sunk ship must contain at least one cell.")

        rows = {row for row, _ in self.cells}
        cols = {col for _, col in self.cells}
        if len(rows) != 1 and len(cols) != 1:
            #  check if all cells are in the same row or same column
            raise ValueError("Sunk ship cells must be in one straight line.")

        if len(rows) == 1:
            ordered = sorted(col for _, col in self.cells)
        else:
            ordered = sorted(row for row, _ in self.cells)

        # check if cells are contiguous 
        expected = list(range(ordered[0], ordered[0] + len(ordered)))
        if ordered != expected:
            raise ValueError("Sunk ship cells must be contiguous.")