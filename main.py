import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
        QApplication,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QListWidget,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSpinBox,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
from board import BattleBoard, Board
from ship import ShipSpec, ConfirmedSunkShip
from fleet import FleetConfig, CellState
from probability import ProbabilityEngine


DEFAULT_SHIPS = (
    ShipSpec(3, 2),
    ShipSpec(2, 1),
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sea Battle Hit Probability Visualiser")
        self.board = BattleBoard(6, 6)
        self.engine = None
        self.cell_buttons = {}
        self.sunk_ships = []
        self.sunk_selection = set()
        self.last_result = None

        central = QWidget()
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(14)

        root_layout.addWidget(self._build_config_panel())
        root_layout.addWidget(self._build_board_panel(), stretch=1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.rebuild_board()

    def _build_config_panel(self):
        panel = QWidget()
        panel.setFixedWidth(280)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        board_group = QGroupBox("Board")
        board_layout = QGridLayout(board_group)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, Board.MAXIMUM_WIDTH)
        self.width_spin.setValue(6)
        self.width_spin.setToolTip("Board column count")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, Board.MAXIMUM_HEIGHT)
        self.height_spin.setValue(6)
        self.height_spin.setToolTip("Board row count")

        board_layout.addWidget(QLabel("Width"), 0, 0)
        board_layout.addWidget(self.width_spin, 0, 1)
        board_layout.addWidget(QLabel("Height"), 1, 0)
        board_layout.addWidget(self.height_spin, 1, 1)
        layout.addWidget(board_group)

        ships_group = QGroupBox("Ships")
        ships_layout = QVBoxLayout(ships_group)

        self.ship_table = QTableWidget(0, 2)
        self.ship_table.setHorizontalHeaderLabels(["Length", "Count"])
        self.ship_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ship_table.verticalHeader().setVisible(False)
        self.ship_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ship_table.setSelectionMode(QTableWidget.SingleSelection)
        self.ship_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ships_layout.addWidget(self.ship_table)

        table_buttons = QHBoxLayout()
        add_button = QPushButton("+")
        add_button.setToolTip("Add ship type")
        add_button.clicked.connect(lambda: self._add_ship_row(3, 1))
        
        remove_button = QPushButton("-")
        remove_button.setToolTip("Remove selected ship type")
        remove_button.clicked.connect(self._remove_selected_ship_row)
        
        table_buttons.addWidget(add_button)
        table_buttons.addWidget(remove_button)
        ships_layout.addLayout(table_buttons)
        layout.addWidget(ships_group, stretch=1)
        
        layout.addWidget(self._build_sunk_panel())

        rebuild_button = QPushButton("Rebuild Board")
        rebuild_button.clicked.connect(self.rebuild_board)
        layout.addWidget(rebuild_button)

        for spec in DEFAULT_SHIPS:
            self._add_ship_row(spec.length, spec.count)

        return panel

    def _build_sunk_panel(self):
        sunk_group = QGroupBox("Confirmed Sunk Ships")
        sunk_layout = QVBoxLayout(sunk_group)

        self.sunk_mode_button = QPushButton("Mark Sunk Mode")
        self.sunk_mode_button.setCheckable(True)
        self.sunk_mode_button.setToolTip("Select hit cells that form one sunk ship")
        sunk_layout.addWidget(self.sunk_mode_button)

        sunk_buttons = QHBoxLayout()
        confirm_button = QPushButton("Confirm")
        confirm_button.setToolTip("Confirm selected hit cells as one sunk ship")
        confirm_button.clicked.connect(self._confirm_sunk_selection)
        remove_button = QPushButton("Remove")
        remove_button.setToolTip("Remove selected sunk ship record")
        remove_button.clicked.connect(self._remove_selected_sunk_ship)
        sunk_buttons.addWidget(confirm_button)
        sunk_buttons.addWidget(remove_button)
        sunk_layout.addLayout(sunk_buttons)

        self.sunk_list = QListWidget()
        self.sunk_list.setMaximumHeight(96)
        sunk_layout.addWidget(self.sunk_list)
        return sunk_group

    def _build_board_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.summary_label.setMinimumHeight(28)
        layout.addWidget(self.summary_label)

        self.grid_host = QWidget()
        self.grid_layout = QGridLayout(self.grid_host)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(3)
        layout.addWidget(self.grid_host, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addStretch(1)
        return panel

    def _add_ship_row(self, length, count):
        row = self.ship_table.rowCount()
        self.ship_table.insertRow(row)

        length_spin = QSpinBox()
        length_spin.setRange(1, Board.MAXIMUM_WIDTH)
        length_spin.setValue(length)
        length_spin.setToolTip("Ship length")

        count_spin = QSpinBox()
        count_spin.setRange(1, Board.MAXIMUM_WIDTH * Board.MAXIMUM_HEIGHT)
        count_spin.setValue(count)
        count_spin.setToolTip("Number of ships with this length")

        self.ship_table.setCellWidget(row, 0, length_spin)
        self.ship_table.setCellWidget(row, 1, count_spin)

        for column in range(2):
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.ship_table.setItem(row, column, item)

    def _remove_selected_ship_row(self):
        row = self.ship_table.currentRow()
        if row >= 0:
            self.ship_table.removeRow(row)
            
    def _read_config(self):
        width = self.width_spin.value()
        height = self.height_spin.value()
        ships = []

        for row in range(self.ship_table.rowCount()):
            length_widget = self.ship_table.cellWidget(row, 0)
            count_widget = self.ship_table.cellWidget(row, 1)
            if length_widget is None or count_widget is None:
                continue
            ships.append(ShipSpec(length_widget.value(), count_widget.value()))

        return FleetConfig(width=width, height=height, ships=ships)

    def rebuild_board(self):
        try:
            config = self._read_config()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid configuration", str(exc))
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.engine = ProbabilityEngine(config)
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid configuration", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.board = BattleBoard(config.width, config.height)
        self.sunk_ships = []
        self.sunk_selection = set()
        self._refresh_sunk_list()
        self._rebuild_grid_buttons()
        self.refresh_probabilities()

    def refresh_probabilities(self):
        if self.engine is None:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.last_result = self.engine.evaluate(
                self._cell_state_matrix(),
                sunk_ships=self.sunk_ships,
            )
        except ValueError as exc:
            self.last_result = None
            QMessageBox.warning(self, "Invalid sunk ship state", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._paint_board()
        self._update_summary()



    def _rebuild_grid_buttons(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.cell_buttons = {}
        for row in range(self.board.height):
            row_label = QLabel(str(self.board.height - row))
            row_label.setAlignment(Qt.AlignCenter)
            row_label.setFixedSize(28, 54)
            row_label.setStyleSheet("color: #374151; font-weight: 600;")
            self.grid_layout.addWidget(row_label, row, 0)

            for col in range(self.board.width):
                button = QPushButton()
                button.setFixedSize(64, 54)
                button.setFont(QFont("Arial", 9))
                button.setToolTip(self._display_coordinate(row, col))
                button.clicked.connect(
                    lambda checked=False, r=row, c=col: self._cycle_cell(r, c)
                )
                self.grid_layout.addWidget(button, row, col + 1)
                self.cell_buttons[(row, col)] = button

        for col in range(self.board.width):
            col_label = QLabel(self._column_name(col))
            col_label.setAlignment(Qt.AlignCenter)
            col_label.setFixedSize(64, 28)
            col_label.setStyleSheet("color: #374151; font-weight: 600;")
            self.grid_layout.addWidget(col_label, self.board.height, col + 1)

    def _cycle_cell(self, row, col):
        if self.sunk_mode_button.isChecked():
            self._toggle_sunk_selection(row, col)
            return

        if self.board.get_state(row, col) == BattleBoard.SUNK:
            QMessageBox.information(
                self,
                "Confirmed sunk ship",
                "Remove the sunk ship record before changing this cell.",
            )
            return

        self.board.cycle_state(row, col)
        self.refresh_probabilities()

    def _toggle_sunk_selection(self, row, col):
        state = self.board.get_state(row, col)
        if state != BattleBoard.HIT:
            QMessageBox.information(
                self,
                "Select hit cells",
                "Only hit cells can be selected for a confirmed sunk ship.",
            )
            return

        coordinate = (row, col)
        if coordinate in self.sunk_selection:
            self.sunk_selection.remove(coordinate)
        else:
            self.sunk_selection.add(coordinate)
        self._paint_board()

    def _confirm_sunk_selection(self):
        if not self.sunk_selection:
            QMessageBox.information(
                self,
                "No cells selected",
                "Turn on Mark Sunk Mode and select hit cells first.",
            )
            return

        try:
            sunk_ship = ConfirmedSunkShip(self.sunk_selection)
            self.engine.evaluate(self._cell_state_matrix(), self.sunk_ships + [sunk_ship])
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid sunk ship", str(exc))
            return

        for row, col in sunk_ship.cells:
            self.board.mark_sunk(row, col)
        self.sunk_ships.append(sunk_ship)
        self.sunk_selection = set()
        self.sunk_mode_button.setChecked(False)
        self._refresh_sunk_list()
        self.refresh_probabilities()

    def _remove_selected_sunk_ship(self):
        row = self.sunk_list.currentRow()
        if row < 0:
            return

        sunk_ship = self.sunk_ships.pop(row)
        for cell_row, cell_col in sunk_ship.cells:
            self.board.set_state(cell_row, cell_col, BattleBoard.HIT)
        self._refresh_sunk_list()
        self.refresh_probabilities()

    def _refresh_sunk_list(self):
        if not hasattr(self, "sunk_list"):
            return

        self.sunk_list.clear()
        for sunk_ship in self.sunk_ships:
            cells = ", ".join(
                self._display_coordinate(row, col)
                for row, col in sunk_ship.cells
            )
            self.sunk_list.addItem(f"Length {sunk_ship.length}: {cells}")

    def _cell_state_matrix(self):
        values = []
        for row in range(self.board.height):
            current_row = []
            for col in range(self.board.width):
                state = self.board.get_state(row, col)
                if state == BattleBoard.HIT:
                    current_row.append(CellState.HIT)
                elif state == BattleBoard.MISS:
                    current_row.append(CellState.MISS)
                elif state == BattleBoard.SUNK:
                    current_row.append(CellState.SUNK)
                else:
                    current_row.append(CellState.UNKNOWN)
            values.append(current_row)
        return values

    def _paint_board(self):
        result = self.last_result
        if result is None:
            return

        for row in range(self.board.height):
            for col in range(self.board.width):
                button = self.cell_buttons[(row, col)]
                state = self.board.get_state(row, col)
                probability = result.probabilities[row][col]
                is_best = result.best_cell == (row, col)
                is_selected = (row, col) in self.sunk_selection
                button.setText(self._cell_text(state, probability))
                button.setStyleSheet(
                    self._cell_style(state, probability, is_best, is_selected)
                )

    def _cell_text(self, state, probability):
        if state == BattleBoard.HIT:
            return f"HIT\n{probability:.0%}"
        if state == BattleBoard.SUNK:
            return "SUNK"
        if state == BattleBoard.MISS:
            return "MISS"
        if probability <= 0:
            return ""
        return f"{probability:.0%}"

    def _cell_style(self, state, probability, is_best, is_selected):
        if state == BattleBoard.HIT:
            background = "#2563eb"
            color = "#ffffff"
        elif state == BattleBoard.SUNK:
            background = "#111827"
            color = "#ffffff"
        elif state == BattleBoard.MISS:
            background = "#6b7280"
            color = "#ffffff"
        else:
            background = self._heat_color(probability)
            color = "#111827" if probability < 0.62 else "#ffffff"

        if is_selected:
            border = "3px solid #f59e0b"
        elif is_best:
            border = "3px solid #16a34a"
        else:
            border = "1px solid #d1d5db"
        return (
            "QPushButton {"
            f"background-color: {background};"
            f"color: {color};"
            f"border: {border};"
            "border-radius: 4px;"
            "font-weight: 600;"
            "padding: 2px;"
            "}"
        )

    def _heat_color(self, probability):
        probability = max(0.0, min(1.0, probability))
        low = (248, 250, 252)
        high = (185, 28, 28)
        red = round(low[0] + (high[0] - low[0]) * probability)
        green = round(low[1] + (high[1] - low[1]) * probability)
        blue = round(low[2] + (high[2] - low[2]) * probability)
        return f"#{red:02x}{green:02x}{blue:02x}"

    def _update_summary(self):
        result = self.last_result
        if result is None:
            return

        if result.remaining_arrangements == 0:
            total_text = (
                f"{result.total_arrangements:,}"
                if result.total_arrangements is not None
                else "not fully counted"
            )
            message = (
                f"No legal arrangements. Total arrangements: "
                f"{total_text}."
            )
            self.summary_label.setText(message)
            self.statusBar().showMessage(message)
            return

        if result.best_cell is None:
            best_text = "No unknown target remains"
        else:
            row, col = result.best_cell
            best_text = (
                f"Best target: {self._display_coordinate(row, col)} "
                f"({result.best_probability:.1%})"
            )

        if result.exact:
            message = (
                f"Remaining arrangements: {result.remaining_arrangements:,} / "
                f"{result.total_arrangements:,}. {best_text}."
            )
        else:
            message = (
                f"Sampled legal arrangements: {result.remaining_arrangements:,}. "
                f"Exact limit reached. {best_text}."
            )
        self.summary_label.setText(message)
        self.statusBar().showMessage(message)

    def _display_coordinate(self, row, col):
        return f"{self._column_name(col)}{self.board.height - row}"

    def _column_name(self, col):
        name = ""
        col += 1
        while col:
            col, remainder = divmod(col - 1, 26)
            name = chr(ord("A") + remainder) + name
        return name


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(980, 720)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
