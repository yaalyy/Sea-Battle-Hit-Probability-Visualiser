class Board:
    MAXIMUM_WIDTH = 15
    MAXIMUM_HEIGHT = 15

    def __init__(self, width, height):
        if width <= 0 or height <= 0:
            raise ValueError("Board dimensions must be positive.")

        if width > self.MAXIMUM_WIDTH or height > self.MAXIMUM_HEIGHT:
            raise ValueError(
                "Board size exceeds maximum allowed dimensions of "
                f"{self.MAXIMUM_WIDTH}x{self.MAXIMUM_HEIGHT}."
            )

        self.width = width
        self.height = height
        self.grid = [[" " for _ in range(width)] for _ in range(height)]

    def is_valid_coordinate(self, row, col):
        return 0 <= row < self.height and 0 <= col < self.width

    def require_valid_coordinate(self, row, col):
        if not self.is_valid_coordinate(row, col):
            raise ValueError(f"Coordinates ({row}, {col}) out of bounds")



class BattleBoard(Board):
    """
    This board records the player's hits and misses against the opponent.
    """

    UNKNOWN = " "
    HIT = "x"
    MISS = "m"
    SUNK = "s"

    def __init__(self, width, height):
        super().__init__(width, height)
        self.miss_list = []
        self.hit_list = []

    def get_state(self, row, col):
        self.require_valid_coordinate(row, col)
        return self.grid[row][col]

    def clear_mark(self, row, col):
        self.require_valid_coordinate(row, col)
        coordinate = (row, col)
        self.grid[row][col] = self.UNKNOWN
        
        
        if coordinate in self.hit_list:
            self.hit_list.remove(coordinate)
        if coordinate in self.miss_list:
            self.miss_list.remove(coordinate)

    def set_state(self, row, col, state):
        self.require_valid_coordinate(row, col)
        if state not in {self.UNKNOWN, self.HIT, self.MISS, self.SUNK}:
            raise ValueError(f"Unsupported cell state: {state!r}")

        self.clear_mark(row, col)
        
        if state == self.HIT:
            self.mark_hit(row, col)
        elif state == self.MISS:
            self.mark_miss(row, col)
        elif state == self.SUNK:
            self.mark_sunk(row, col)
    
    def mark_hit(self, row, col):
        self.require_valid_coordinate(row, col)
        coordinate = (row, col)
        
        if self.grid[row][col] == self.HIT:
            return
        
        self.grid[row][col] = self.HIT
        
        if coordinate in self.miss_list:
            self.miss_list.remove(coordinate)
        if coordinate not in self.hit_list:
            self.hit_list.append(coordinate)


    def mark_miss(self, row, col):
        self.require_valid_coordinate(row, col)
        coordinate = (row, col)
        
        if self.grid[row][col] == self.MISS:
            return
        self.grid[row][col] = self.MISS
        
        if coordinate in self.hit_list:
            self.hit_list.remove(coordinate)
        
        if coordinate not in self.miss_list:
            self.miss_list.append(coordinate)

    def mark_sunk(self, row, col):
        self.require_valid_coordinate(row, col)
        coordinate = (row, col)
        
        if coordinate in self.miss_list:
            self.miss_list.remove(coordinate)
            
        self.grid[row][col] = self.SUNK
        
        if coordinate not in self.hit_list:
            self.hit_list.append(coordinate)
            
    def cycle_state(self, row, col):
        state = self.get_state(row, col)
        
        if state == self.UNKNOWN:
            self.mark_hit(row, col)
            return self.HIT
        
        if state == self.HIT:
            self.mark_miss(row, col)
            return self.MISS

        self.clear_mark(row, col)
        return self.UNKNOWN

    def states(self):
        return [row[:] for row in self.grid]
