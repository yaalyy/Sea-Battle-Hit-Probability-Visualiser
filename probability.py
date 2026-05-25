import random
from collections import Counter
from ship import ConfirmedSunkShip
from fleet import FleetConfig, CellState, Cell


class EvaluationResult:
    """Used to store the result of a probability evaluation."""
    def __init__(
        self,
        remaining_arrangements: int,
        total_arrangements: int | None,
        probabilities: list[list[float]],
        best_cell: Cell | None,
        best_probability: float,
        exact: bool,
        limit_reached: bool,
    ):
        self.remaining_arrangements = remaining_arrangements
        self.total_arrangements = total_arrangements
        self.probabilities = probabilities
        self.best_cell = best_cell
        self.best_probability = best_probability
        self.exact = exact
        self.limit_reached = limit_reached

    def __repr__(self):
        return (
            "EvaluationResult("
            f"remaining_arrangements={self.remaining_arrangements!r}, "
            f"total_arrangements={self.total_arrangements!r}, "
            f"probabilities={self.probabilities!r}, "
            f"best_cell={self.best_cell!r}, "
            f"best_probability={self.best_probability!r}, "
            f"exact={self.exact!r}, "
            f"limit_reached={self.limit_reached!r})"
        )

    def __eq__(self, other):
        return (
            isinstance(other, EvaluationResult)
            and self.remaining_arrangements == other.remaining_arrangements
            and self.total_arrangements == other.total_arrangements
            and self.probabilities == other.probabilities
            and self.best_cell == other.best_cell
            and self.best_probability == other.best_probability
            and self.exact == other.exact
            and self.limit_reached == other.limit_reached
        )


class PlacementInfo:
    """Used to store the bitmask and cell coordinates of a possible ship placement."""
    def __init__(self, mask: int, cells: tuple[Cell, ...]):
        self.mask = mask
        self.cells = cells

    def __repr__(self):
        return f"PlacementInfo(mask={self.mask!r}, cells={self.cells!r})"

    def __eq__(self, other):
        return (
            isinstance(other, PlacementInfo)
            and self.mask == other.mask
            and self.cells == other.cells
        )

class _ArrangementLimitReached(Exception):
    """This exception is used to label the state when the number of valid fleet arrangements exceeds the defined limit for exact calculation, triggering the switch to sampling-based estimation."""
    
    
class ProbabilityEngine:
    MAX_EXACT_ARRANGEMENTS = 1_000_000  # upper limit for exact arrangements
    SAMPLE_TARGET = 30_000   # if upper limit is exceeded, target number of samples to generate
    SAMPLE_ATTEMPTS = 30_000  # maximum attempts to generate valid samples when limit is exceeded

    def __init__(self, config: FleetConfig):
        self.config = config
        self._ship_placements_by_length: dict[int, list[PlacementInfo]] = {}   # all possible placements for each ship length
        self._all_cells_mask = (1 << (config.width * config.height)) - 1  # bitmask for whole board
        self._fleet_mask_cache = []  # cache for valid fleet arrangements
        self._cache_key = None  # key to identify if cache is still valid based on sunk ships
        self._cache_exact = True  # label indicating if current mode is exact or sampling-based
        self.rebuild()
        
        
    def rebuild(self):
        # precompute placements for each ship length to speed up arrangement generation later
        self._ship_placements_by_length = {
            length: self._enumerate_ship_placements(length)
            for length in {spec.length for spec in self.config.ships}
        }
        
        # clear cache
        self._fleet_mask_cache = []
        self._cache_key = None
        self._cache_exact = True
        
        

    def _cell_bit(self, row, col):
        """convert (row, col) coordinate to bitmask with single bit set for that cell"""
        return 1 << self._cell_index(row, col)
    
    def _cell_index(self, row, col):
        """convert (row, col) 2D coordinate to bit index in mask representation"""
        if not (0 <= row < self.config.height and 0 <= col < self.config.width):
            raise ValueError(f"Coordinates ({row}, {col}) out of bounds.")
        return row * self.config.width + col


    def _cells_to_mask(self, cells):
        """convert a tuple of (row, col) coordinates to a bitmask with bits set for those cells"""
        mask = 0
        for row, col in cells:
            mask |= self._cell_bit(row, col)
        return mask
    
    def _iter_mask_indices(self, mask):
        """Yield the indices of set bits in the given mask."""
        while mask:
            bit = mask & -mask
            yield bit.bit_length() - 1
            mask ^= bit


    def _enumerate_ship_placements(self, length: int) -> list[PlacementInfo]:
        """ generate all possible placements for single ship of given length, represented as bitmask and cell coordinates """
        placements = {}

        # horizontal placements
        for row in range(self.config.height):
            for col in range(self.config.width - length + 1):
                cells = tuple((row, c) for c in range(col, col + length))
                placements[self._cells_to_mask(cells)] = cells

        # vertical placements
        for row in range(self.config.height - length + 1):
            for col in range(self.config.width):
                cells = tuple((r, col) for r in range(row, row + length))
                placements[self._cells_to_mask(cells)] = cells

        return [
            PlacementInfo(mask=mask, cells=cells)
            for mask, cells in sorted(placements.items(), key=lambda item: item[1])
        ]
        
        
    def _normalize_state_value(self, state):
        """convert various cell state input to standard CellState enum"""
        if isinstance(state, CellState):
            return state
        if state in {"x", "X", "hit", "HIT"}:
            return CellState.HIT
        if state in {"m", "M", "miss", "MISS"}:
            return CellState.MISS
        if state in {"s", "S", "sunk", "SUNK"}:
            return CellState.SUNK
        if state in {" ", "", None, "unknown", "UNKNOWN"}:
            return CellState.UNKNOWN
        raise ValueError(f"Unsupported cell state: {state!r}")
        
    def _normalize_cell_states(self, cell_states):
        """Given the board states, compute bitmasks for hits, misses, and unknown cells."""
        hits_mask = 0
        misses_mask = 0
        unknown_mask = 0

        if isinstance(cell_states, dict):
            for (row, col), state in cell_states.items():
                normalized_state = self._normalize_state_value(state)
                bit = self._cell_bit(row, col)
                if normalized_state in {CellState.HIT, CellState.SUNK}:
                    hits_mask |= bit
                elif normalized_state == CellState.MISS:
                    misses_mask |= bit
                else:
                    unknown_mask |= bit
        else:
            # assume 2D list input
            if len(cell_states) != self.config.height:
                raise ValueError("Cell state row count does not match board height.")
            for row, values in enumerate(cell_states):
                if len(values) != self.config.width:
                    raise ValueError("Cell state column count does not match board width.")
                for col, state in enumerate(values):
                    normalized_state = self._normalize_state_value(state)
                    bit = self._cell_bit(row, col)
                    if normalized_state in {CellState.HIT, CellState.SUNK}:
                        hits_mask |= bit
                    elif normalized_state == CellState.MISS:
                        misses_mask |= bit
                    else:
                        unknown_mask |= bit

        if hits_mask & misses_mask:
            raise ValueError("A cell cannot be both hit and miss.")

        unknown_mask |= self._all_cells_mask & ~(hits_mask | misses_mask)
        return hits_mask, misses_mask, unknown_mask


    def _apply_sunk_ships(self, sunk_ships, misses_mask):
        """Apply constraints from confirmed sunk ships by updating the fixed_mask to include their cells and calculating the remaining ship lengths that need to be placed. Also checks for consistency with misses and overlapping sunk ships. Returns the updated fixed_mask and list of remaining ship lengths. """
        available_by_length = Counter()
        for spec in self.config.ships:
            available_by_length[spec.length] += spec.count

        fixed_mask = 0
        for sunk_ship in sunk_ships:
            if not isinstance(sunk_ship, ConfirmedSunkShip):
                sunk_ship = ConfirmedSunkShip(sunk_ship)

            if available_by_length[sunk_ship.length] <= 0:
                raise ValueError(f"No remaining ship of length {sunk_ship.length} exists.")
            available_by_length[sunk_ship.length] -= 1

            sunk_mask = self._cells_to_mask(sunk_ship.cells)
            if fixed_mask & sunk_mask:
                raise ValueError("Confirmed sunk ships cannot overlap.")
            if misses_mask & sunk_mask:
                raise ValueError("A sunk ship cannot include a missed cell.")
            fixed_mask |= sunk_mask

        remaining_lengths = sorted(available_by_length.elements(), reverse=True)
        return fixed_mask, remaining_lengths
    
    def _sunk_cache_key(self, sunk_ships):
        """Obtain a cache key for the current sunk ship configuration by converting each sunk ship to a tuple of its cell coordinates. This is used to identify when the cache of valid fleet arrangements can be reused or not """
        return tuple(
            tuple(sunk_ship.cells if isinstance(sunk_ship, ConfirmedSunkShip) else sunk_ship)
            for sunk_ship in sunk_ships
        )
    
    

    
    def _ensure_fleet_mask_cache(self, remaining_lengths, fixed_mask, cache_key):
        """ Check if the cache of valid fleet arrangements is still valid for the current sunk ship configuration (identified by cache_key). If not, regenerate the cache by building valid arrangements recursively. """
        if self._cache_key == cache_key:
            return

        masks = []

        try:
            # exact probability
            self._collect_fleet_masks(
                ship_lengths=remaining_lengths,
                index=0,
                occupied_mask=0,
                same_length_start={},
                forbidden_mask=fixed_mask,
                fixed_mask=fixed_mask,
                masks=masks,
            )
            self._cache_exact = True
        except _ArrangementLimitReached:
            # sampled probability
            masks = self._sample_fleet_masks(remaining_lengths, fixed_mask)
            self._cache_exact = False

        self._fleet_mask_cache = masks
        self._cache_key = cache_key

    def _collect_fleet_masks(
        self,
        ship_lengths,
        index,
        occupied_mask,
        same_length_start,
        forbidden_mask,
        fixed_mask,
        masks,
    ):
        """ Recursively build valid fleet arrangements by placing ships one by one."""
        if index == len(ship_lengths):
            if len(masks) >= self.MAX_EXACT_ARRANGEMENTS:
                raise _ArrangementLimitReached
            masks.append(occupied_mask | fixed_mask)
            return

        length = ship_lengths[index]
        placements = self._ship_placements_by_length[length]
        start = same_length_start.get(length, 0)

        for placement_index in range(start, len(placements)):
            placement = placements[placement_index]
            if placement.mask & (occupied_mask | forbidden_mask):
                continue

            next_starts = dict(same_length_start)
            next_starts[length] = placement_index + 1
            self._collect_fleet_masks(
                ship_lengths,
                index + 1,
                occupied_mask | placement.mask,
                next_starts,
                forbidden_mask,
                fixed_mask,
                masks,
            )


    def _sample_fleet_masks(self, remaining_lengths, fixed_mask):
        """ Generate random valid fleet arrangements by randomly placing ships one by one, up to a target number of samples or maximum attempts. This is used when the exact arrangement count exceeds the defined limit. """
        rng = random.Random(8675309)
        masks = []
        attempts = 0

        while len(masks) < self.SAMPLE_TARGET and attempts < self.SAMPLE_ATTEMPTS:
            attempts += 1
            occupied_mask = 0
            failed = False

            for length in remaining_lengths:
                candidates = [
                    placement
                    for placement in self._ship_placements_by_length[length]
                    if not placement.mask & (occupied_mask | fixed_mask)
                ]
                if not candidates:
                    failed = True
                    break
                occupied_mask |= rng.choice(candidates).mask

            if not failed:
                masks.append(occupied_mask | fixed_mask)

        return masks
    
    
    def _build_result(self, counts, remaining, total, unknown_mask, exact):
        """Compute EvaluationResult including probabilities and best cell based on counts of valid arrangements for each cell and total remaining arrangements. 
        
        Parameters:
            counts: list of counts of valid arrangements for each cell index
        
            remaining: total number of valid arrangements remaining after applying hits, misses, and sunk ship constraints
        
            total: total number of arrangements considered (exact or sampled)
        
            unknown_mask: bitmask indicating which cells are still unknown (not hit or miss)
        
            exact: boolean indicating if total is an exact count or a sample-based estimate

        Returns:
            EvaluationResult: Evaluation result containing probabilities for each cell, best cell to target, and metadata about the evaluation
        """
        
        # initialise probability table with zeros
        probabilities = [
            [0.0 for _ in range(self.config.width)]
            for _ in range(self.config.height)
        ]
        
        if remaining == 0:
            return EvaluationResult(
                remaining_arrangements=0,
                total_arrangements=total,
                probabilities=probabilities,
                best_cell=None,
                best_probability=0.0,
                exact=exact,
                limit_reached=not exact,
            )

        best_cell = None
        best_probability = 0.0
        for row in range(self.config.height):
            for col in range(self.config.width):
                index = self._cell_index(row, col)
                probability = counts[index] / remaining
                probabilities[row][col] = probability
                bit = 1 << index
                if unknown_mask & bit and probability > best_probability:
                    best_cell = (row, col)
                    best_probability = probability

        return EvaluationResult(
            remaining_arrangements=remaining,
            total_arrangements=total,
            probabilities=probabilities,
            best_cell=best_cell,
            best_probability=best_probability,
            exact=exact,
            limit_reached=not exact,
        )


    def evaluate(self, cell_states, sunk_ships=None) -> EvaluationResult:
        """Evaluate the board to calculate hit probabilities for each cell.

        Args:
            cell_states (dict): The current state of each cell on the board.
            sunk_ships (iterable, optional): The collection of ships already sunk. Defaults to None.

        Returns:
            EvaluationResult: The result of the probability calculations.
        """
        sunk_ships = tuple(sunk_ships or ())
        hits_mask, misses_mask, unknown_mask = self._normalize_cell_states(cell_states) # get bitmasks for hits, misses, and unknowns
        
        fixed_mask, remaining_lengths = self._apply_sunk_ships(sunk_ships, misses_mask)
        required_mask = hits_mask & ~fixed_mask # hits but not in sunk ships
        
        self._ensure_fleet_mask_cache(
            remaining_lengths=remaining_lengths,
            fixed_mask=fixed_mask,
            cache_key=self._sunk_cache_key(sunk_ships),
        )

        counts = [0 for _ in range(self.config.width * self.config.height)]
        remaining = 0
        for fleet_mask in self._fleet_mask_cache:
            if misses_mask & fleet_mask:
                continue
            if required_mask & ~fleet_mask:
                continue

            remaining += 1
            for cell_index in self._iter_mask_indices(fleet_mask):
                counts[cell_index] += 1

        total = len(self._fleet_mask_cache) if self._cache_exact else None
        return self._build_result(
            counts=counts,
            remaining=remaining,
            total=total,
            unknown_mask=unknown_mask,
            exact=self._cache_exact,
        )


