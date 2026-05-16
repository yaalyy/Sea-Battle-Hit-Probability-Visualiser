from enum import Enum
from board import Board
from ship import ShipSpec


Cell = tuple[int, int]

class CellState(Enum):
    UNKNOWN = "unknown"
    HIT = "hit"
    MISS = "miss"
    SUNK = "sunk"

class FleetConfig:
    """ Used to check if the provided fleet configuration is valid and can contain all ships"""
    def __init__(self, width: int, height: int, ships):
        self.width = width
        self.height = height
        self.ships = tuple(ships)
        self._validate()

    def __repr__(self):
        return (
            "FleetConfig("
            f"width={self.width!r}, "
            f"height={self.height!r}, "
            f"ships={self.ships!r})"
        )

    def __eq__(self, other):
        return (
            isinstance(other, FleetConfig)
            and self.width == other.width
            and self.height == other.height
            and self.ships == other.ships
        )

    def _validate(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Board dimensions must be positive.")
        
        if self.width > Board.MAXIMUM_WIDTH or self.height > Board.MAXIMUM_HEIGHT:
            raise ValueError(
                "Board size exceeds maximum allowed dimensions of "
                f"{Board.MAXIMUM_WIDTH}x{Board.MAXIMUM_HEIGHT}."
            )
        if not self.ships:
            raise ValueError("At least one ship type is required.")

        total_ship_cells = 0
        for spec in self.ships:
            if not isinstance(spec, ShipSpec):
                raise TypeError("FleetConfig ships must contain ShipSpec instances.")
            
            if spec.length > max(self.width, self.height):
                raise ValueError(
                    f"Ship length {spec.length} cannot fit on a "
                    f"{self.width}x{self.height} board."
                )
            total_ship_cells += spec.length * spec.count

        if total_ship_cells > self.width * self.height:
            raise ValueError("Total ship cells exceed board capacity.")