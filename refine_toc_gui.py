import os
import sys

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QFileDialog,
    QMessageBox
)


class EditDialog(QDialog):
    def __init__(self, level, title, page_number, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Row")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        screen = QApplication.primaryScreen()
        if sys.platform.startswith("darwin"):
            zoom_factor = screen.devicePixelRatio()
        else:
            zoom_factor = screen.logicalDotsPerInch() / 96
        font_size = round(14 * zoom_factor)
        self.setStyleSheet(f"font-size: {font_size}px;")

        self.level_input = QSpinBox()
        self.level_input.setMinimum(1)
        if level is not None:
            self.level_input.setValue(level)
        self.title_input = QLineEdit(title)
        self.page_input = QSpinBox()
        self.page_input.setMinimum(1)
        self.page_input.setMaximum(2**31 - 1)  # cancel default 99
        if page_number is not None:
            self.page_input.setValue(page_number)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QFormLayout()
        layout.addRow("Level:", self.level_input)
        layout.addRow("Title:", self.title_input)
        layout.addRow("Page Number:", self.page_input)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    def get_values(self):
        return self.level_input.value(), self.title_input.text(), self.page_input.value()


class TocRefinement(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("TOC Refinement")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        screen = QApplication.primaryScreen()
        if sys.platform.startswith("darwin"):  # macOS
            self.zoom_pct = screen.devicePixelRatio()
        else:  # Windows, Linux
            self.zoom_pct = screen.logicalDotsPerInch() / 96
        font_size = round(14 * self.zoom_pct)
        self.screen_height = screen.geometry().height()
        self.screen_width = screen.geometry().width()

        # Create UI elements
        # Left column
        self.table = QTableWidget(0, 3)
        self.table.setStyleSheet(f"font-size: {font_size}px;")
        self.table.setHorizontalHeaderLabels(["Level", "Title", "#Page"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        # Prevent last column from stretching
        self.table.horizontalHeader().setStretchLastSection(False)

        # Right column
        import_button = QPushButton("Import")
        import_button.setStyleSheet(f"font-size: {font_size}px;")
        import_button.clicked.connect(self.import_from_file)
        export_button = QPushButton("Export")
        export_button.setStyleSheet(f"font-size: {font_size}px;")
        export_button.clicked.connect(self.export_to_file)
        move_up_button = QPushButton("Move Up")
        move_up_button.setStyleSheet(f"font-size: {font_size}px;")
        move_up_button.clicked.connect(self.move_up)
        move_down_button = QPushButton("Move Down")
        move_down_button.setStyleSheet(f"font-size: {font_size}px;")
        move_down_button.clicked.connect(self.move_down)
        increase_indent_button = QPushButton("Increase Level")
        increase_indent_button.setStyleSheet(f"font-size: {font_size}px;")
        increase_indent_button.clicked.connect(self.increase_indents)
        decrease_indent_button = QPushButton("Decrease Level")
        decrease_indent_button.setStyleSheet(f"font-size: {font_size}px;")
        decrease_indent_button.clicked.connect(self.decrease_indents)
        add_button = QPushButton("Add")
        add_button.setStyleSheet(f"font-size: {font_size}px;")
        add_button.clicked.connect(self.add_row)
        edit_button = QPushButton("Edit")
        edit_button.setStyleSheet(f"font-size: {font_size}px;")
        edit_button.clicked.connect(self.edit_row)
        delete_button = QPushButton("Delete")
        delete_button.setStyleSheet(f"font-size: {font_size}px;")
        delete_button.clicked.connect(self.delete_rows)
        done_button = QPushButton("Done")
        done_button.setStyleSheet(f"font-size: {font_size}px;")
        done_button.clicked.connect(self.close)

        # Layouts
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.table)
        right_layout = QVBoxLayout()
        right_layout.addWidget(import_button)
        right_layout.addWidget(export_button)
        right_layout.addWidget(move_up_button)
        right_layout.addWidget(move_down_button)
        right_layout.addWidget(increase_indent_button)
        right_layout.addWidget(decrease_indent_button)
        right_layout.addWidget(add_button)
        right_layout.addWidget(edit_button)
        right_layout.addWidget(delete_button)
        right_layout.addStretch()
        right_layout.addWidget(done_button)
        layout = QHBoxLayout()
        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        self.setLayout(layout)

        # Set window dimensions
        window_width = round(self.screen_width / 2)
        window_height = round(self.screen_height / 2)
        x = round((self.screen_width - window_width) / 2)
        y = round((self.screen_height - window_height) / 2)
        self.setGeometry(x, y, window_width, window_height)

    def selected_rows(self, single=False):
        model = self.table.selectionModel()
        rows = [index.row() for index in model.selectedRows()]
        if single:
            return rows[0] if len(rows) > 0 else None
        else:
            return rows

    def add_row(self):
        row = self.selected_rows(single=True)
        if row:
            row += 1  # insert below selected row
        else:
            row = self.table.rowCount()
        dialog = EditDialog(1, "", 1, self)
        if dialog.exec_():
            new_level, new_title, new_page_number = dialog.get_values()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(new_level)))
            self.table.setItem(row, 1,
                               QTableWidgetItem(" " * (new_level - 1) + new_title))
            self.table.setItem(row, 2, QTableWidgetItem(str(new_page_number)))

    def move_up(self):
        row = self.selected_rows(single=True)
        if row is not None and row > 0:
            self.swap_rows(row, row - 1)

    def move_down(self):
        row = self.selected_rows(single=True)
        if row is not None and row < self.table.rowCount() - 1:
            self.swap_rows(row, row + 1)

    def increase_indents(self):
        for row in self.selected_rows():
            level, title, _ = self.clean_row(row)
            if level is not None:
                level += 1
                item_level = QTableWidgetItem(str(level))
                item_title = QTableWidgetItem(" " * (level - 1) + title)
                self.table.setItem(row, 0, item_level)
                self.table.setItem(row, 1, item_title)

    def decrease_indents(self):
        for row in self.selected_rows():
            level, title, _ = self.clean_row(row)
            if (level is not None) and level > 1:
                level -= 1
                item_level = QTableWidgetItem(str(level))
                item_title = QTableWidgetItem(" " * (level - 1) + title)
                self.table.setItem(row, 0, item_level)
                self.table.setItem(row, 1, item_title)

    def delete_rows(self):
        rows = self.selected_rows()
        rows = sorted(rows, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def swap_rows(self, row_1, row_2):
        level_1 = self.table.item(row_1, 0).text()
        title_1 = self.table.item(row_1, 1).text()
        page_number_1 = self.table.item(row_1, 2).text()
        level_2 = QTableWidgetItem(self.table.item(row_2, 0).text())
        title_2 = QTableWidgetItem(self.table.item(row_2, 1).text())
        page_number_2 = QTableWidgetItem(self.table.item(row_2, 2).text())
        self.table.setItem(row_1, 0, level_2)
        self.table.setItem(row_1, 1, title_2)
        self.table.setItem(row_1, 2, page_number_2)
        self.table.setItem(row_2, 0, QTableWidgetItem(level_1))
        self.table.setItem(row_2, 1, QTableWidgetItem(title_1))
        self.table.setItem(row_2, 2, QTableWidgetItem(page_number_1))

    def clean_row(self, row_id):
        level = self.table.item(row_id, 0).text()
        if level:
            try:
                level = int(level)
            except ValueError:
                level = None
        else:
            level = None
        title = self.table.item(row_id, 1).text()
        if level:
            title = title.removeprefix(" " * (level - 1))
        page_number = self.table.item(row_id, 2).text()
        if page_number:
            try:
                page_number = int(page_number)
            except ValueError:
                page_number = None
        else:
            page_number = None
        return level, title, page_number

    def edit_row(self):
        row = self.selected_rows(single=True)
        if row is not None:
            dialog = EditDialog(*self.clean_row(row), self)
            if dialog.exec_():
                new_level, new_title, new_page_number = dialog.get_values()
                self.table.setItem(row, 0, QTableWidgetItem(str(new_level)))
                self.table.setItem(row, 1, QTableWidgetItem(
                    " " * (new_level - 1) + new_title))
                self.table.setItem(row, 2, QTableWidgetItem(str(new_page_number)))

    def show(self):
        super().show()
        # simulate stretch "title" column width
        self.table.resizeColumnsToContents()
        width = self.table.width()
        for i in range(self.table.columnCount()):
            if i == 1: continue  # skip "title" column itself
            width -= self.table.columnWidth(i)
        self.table.setColumnWidth(1, width - 2)

    def import_from_file(self):
        fp = get_file()
        if os.path.isfile(fp):
            toc = pd.read_pickle(fp)
            assert toc.columns.tolist() == ['level', 'title', 'page_number'], (
                "The format of imported TOC is invalid."
            )
            self.set_table(toc)

    def export_to_file(self):
        base_dir = QFileDialog.getExistingDirectory()
        if os.path.isdir(base_dir):
            fn = os.path.join(base_dir, "toc_refined.pkl")
            toc = self.get_table()
            toc.to_pickle(fn)

    def get_table(self):
        toc = []
        for row in range(self.table.rowCount()):
            level, title, page_number = self.clean_row(row)
            toc.append({
                "level": level or pd.NA,
                "title": title or pd.NA,
                "page_number": page_number or pd.NA,
            })
        toc = pd.DataFrame(toc)
        return toc

    def set_table(self, df):
        df['level'] = pd.to_numeric(df['level'], errors='coerce')
        df['level'] = df['level'].astype('Int64')
        df['page_number'] = pd.to_numeric(df['page_number'], errors='coerce')
        df['page_number'] = df['page_number'].astype('Int64')
        self.table.setRowCount(df.shape[0])
        for i, (level, title, page_number) in df.iterrows():
            if pd.isna(level):
                item_level = QTableWidgetItem()
            else:
                item_level = QTableWidgetItem(str(level))
            self.table.setItem(i, 0, item_level)
            if pd.isna(title):
                item_title = QTableWidgetItem()
            else:
                if pd.isna(level):
                    item_title_text = str(title)
                else:
                    item_title_text = " " * (level - 1) + str(title)
                item_title = QTableWidgetItem(item_title_text)
            self.table.setItem(i, 1, item_title)
            if pd.isna(page_number):
                item_page_number = QTableWidgetItem()
            else:
                item_page_number = QTableWidgetItem(str(page_number))
            self.table.setItem(i, 2, item_page_number)


def get_file():
    fp, _ = QFileDialog.getOpenFileName(
        parent=None,
        caption="Select TOC",
        directory=rf"C:\Users\{os.environ['USERNAME']}\Desktop",
        filter="Pickled File (*.pkl)",
    )
    if fp and os.path.isfile(fp):
        return fp
    else:
        # Display an error message box
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("Error")
        error_box.setText("The selected file path is invalid.")
        error_box.setStandardButtons(QMessageBox.Ok)
        return None
