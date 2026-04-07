import os
import sys

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox,
    QFileDialog, QMessageBox, QAbstractItemView, QMenuBar, QMenu
)


class EditDialog(QDialog):
    def __init__(self, level, title, page_number, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Row")
        self.setWindowFlags(self.windowFlags()
                            & ~Qt.WindowType.WindowContextHelpButtonHint)

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
        self.page_input.setMaximum(2**31 - 1)
        if page_number is not None:
            self.page_input.setValue(page_number)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
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


class TocRefinement(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("TOC Refinement")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        screen = QApplication.primaryScreen()
        if sys.platform.startswith("darwin"):  # macOS
            self.zoom_pct = screen.devicePixelRatio()
        else:  # Windows, Linux
            self.zoom_pct = screen.logicalDotsPerInch() / 96
        font_size = round(14 * self.zoom_pct)
        self.screen_height = screen.geometry().height()
        self.screen_width = screen.geometry().width()

        # --- Tree widget ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Title", "Page"])
        self.tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.tree.setColumnCount(2)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(
            0, self.tree.header().ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(
            1, self.tree.header().ResizeMode.ResizeToContents)
        self.tree.setStyleSheet(
            f"font-family: 'Microsoft YaHei', sans-serif; font-size: {font_size}px;"
        )

        # --- Menu bar actions ---
        # File menu
        import_act = QAction("&Import", self)
        import_act.triggered.connect(self.import_from_file)

        export_act = QAction("&Export", self)
        export_act.setShortcut("Ctrl+S")
        export_act.triggered.connect(self.export_to_file)

        self.accept_ = False
        done_act = QAction("&Accept", self)
        done_act.triggered.connect(self.accept)

        discard_act = QAction("&Discard", self)
        discard_act.setShortcut("Ctrl+W")
        discard_act.triggered.connect(self.close)

        # Edit menu
        add_act = QAction("&Add", self)
        add_act.setShortcut("T")
        add_act.triggered.connect(self.add_row)

        edit_act = QAction("&Edit", self)
        edit_act.setShortcut("F2")
        edit_act.triggered.connect(self.edit_row)

        delete_act = QAction("&Delete", self)
        delete_act.setShortcut("Del")
        delete_act.triggered.connect(self.delete_rows)

        move_up_act = QAction("Move &up", self)
        move_up_act.setShortcut("W")
        move_up_act.triggered.connect(self.move_up)

        move_down_act = QAction("Move &down", self)
        move_down_act.setShortcut("S")
        move_down_act.triggered.connect(self.move_down)

        increase_level_act = QAction("D&owngrade", self)
        increase_level_act.setShortcut("D")
        increase_level_act.triggered.connect(self.increase_level)

        decrease_level_act = QAction("&Promote", self)
        decrease_level_act.setShortcut("A")
        decrease_level_act.triggered.connect(self.decrease_level)

        # Assemble menus
        file_menu = QMenu("&File", self)
        file_menu.addActions([import_act, export_act, done_act])

        edit_menu = QMenu("&Edit", self)
        edit_menu.addActions([
            add_act, edit_act, delete_act,
            move_up_act, move_down_act,
            increase_level_act, decrease_level_act,
        ])

        menu_bar = QMenuBar(self)
        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(edit_menu)
        self.setMenuBar(menu_bar)

        # --- Central widget ---
        central = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        central.setLayout(layout)
        self.setCentralWidget(central)

        # Window geometry
        window_width = round(self.screen_width / 3)
        window_height = round(min(window_width * 1.5, self.screen_height))
        x = round((self.screen_width - window_width) / 2)
        y = round((self.screen_height - window_height) / 2)
        self.setGeometry(x, y, window_width, window_height)


    def accept(self):
        self.accept_ = True
        self.export_to_file()
        self.close()

    # ------------------------------------------------------------------
    # Tree helpers
    # ------------------------------------------------------------------

    def _all_top_level_items(self):
        """Iterate all items via flat DFS traversal, yielding (item, level)."""
        result = []
        def _walk(item, level):
            result.append((item, level))
            for i in range(item.childCount()):
                _walk(item.child(i), level + 1)
        for i in range(self.tree.topLevelItemCount()):
            _walk(self.tree.topLevelItem(i), 1)
        return result

    def _flatten(self):
        """Return list of dicts with level/title/page_number for every node."""
        rows = []
        for item, level in self._all_top_level_items():
            title = item.text(0)
            page_str = item.text(1)
            try:
                page = int(page_str)
            except (ValueError, TypeError):
                page = None
            rows.append({"level": level, "title": title, "page_number": page})
        return rows

    def _get_expanded_states(self):
        """Return a set of flat indices that are currently expanded."""
        expanded = set()
        for idx, (item, _) in enumerate(self._all_top_level_items()):
            if item.isExpanded():
                expanded.add(idx)
        return expanded

    def _rebuild_tree(self, rows, expanded=None):
        """Rebuild the tree from a flat list of {level, title, page_number}."""
        if expanded is None:
            expanded = self._get_expanded_states()

        self.tree.clear()
        stack = []
        for row in rows:
            level = row["level"] or 1
            title = row["title"] or ""
            page = row["page_number"]
            page_str = str(page) if page is not None else ""

            node = QTreeWidgetItem([title, page_str])

            while stack and stack[-1][0] >= level:
                stack.pop()

            if stack:
                stack[-1][1].addChild(node)
            else:
                self.tree.addTopLevelItem(node)

            stack.append((level, node))

        # Restore expanded states
        all_items = self._all_top_level_items()
        for idx, (item, _) in enumerate(all_items):
            if idx in expanded:
                item.setExpanded(True)

        self.tree.resizeColumnToContents(1)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(
            0, self.tree.header().ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(
            1, self.tree.header().ResizeMode.ResizeToContents)

    def _selected_flat_indices(self):
        """Return flat-order indices of selected items."""
        selected = set(id(item) for item in self.tree.selectedItems())
        indices = []
        for idx, (item, _) in enumerate(self._all_top_level_items()):
            if id(item) in selected:
                indices.append(idx)
        return sorted(indices)

    # ------------------------------------------------------------------
    # Slot implementations
    # ------------------------------------------------------------------

    def selected_rows(self, single=False):
        indices = self._selected_flat_indices()
        if single:
            return indices[0] if indices else None
        return indices

    def add_row(self):
        idx = self.selected_rows(single=True)
        rows = self._flatten()
        if idx is not None:
            current_level = rows[idx]["level"] or 1
            insert_at = idx + 1
            while insert_at < len(rows) and (
                    rows[insert_at]["level"] or 1) > current_level:
                insert_at += 1
        else:
            current_level = 1
            insert_at = len(rows)
        dialog = EditDialog(current_level, "", 1, self)
        if dialog.exec():
            lv, title, pn = dialog.get_values()
            rows.insert(insert_at, {
                "level": lv, "title": title, "page_number": pn
            })
            self._rebuild_tree(rows)


    def edit_row(self):
        idx = self.selected_rows(single=True)
        if idx is None:
            return
        rows = self._flatten()
        r = rows[idx]
        dialog = EditDialog(r["level"], r["title"], r["page_number"], self)
        if dialog.exec():
            lv, title, pn = dialog.get_values()
            rows[idx] = {"level": lv, "title": title, "page_number": pn}
            self._rebuild_tree(rows)

    def delete_rows(self):
        indices = set(self.selected_rows())
        if not indices:
            return
        rows = self._flatten()
        rows = [r for i, r in enumerate(rows) if i not in indices]
        self._rebuild_tree(rows)

    def move_up(self):
        idx = self.selected_rows(single=True)
        if idx is not None and idx > 0:
            rows = self._flatten()
            rows[idx], rows[idx - 1] = rows[idx - 1], rows[idx]
            self._rebuild_tree(rows)
            self._select_by_flat_index(idx - 1)

    def move_down(self):
        idx = self.selected_rows(single=True)
        rows = self._flatten()
        if idx is not None and idx < len(rows) - 1:
            rows[idx], rows[idx + 1] = rows[idx + 1], rows[idx]
            self._rebuild_tree(rows)
            self._select_by_flat_index(idx + 1)

    def _select_by_flat_index(self, flat_idx):
        """Select the item at the given flat-order index."""
        items = self._all_top_level_items()
        if 0 <= flat_idx < len(items):
            item, _ = items[flat_idx]
            self.tree.setCurrentItem(item)

    def increase_level(self):
        indices = set(self.selected_rows())
        if not indices:
            return
        rows = self._flatten()
        visited = set()
        for i in indices:
            if i in visited:
                continue
            visited.add(i)
            rows[i]["level"] = (rows[i]["level"] or 1) + 1
            # Cascade to children (all subsequent rows with level > original level)
            parent_level = rows[i]["level"] - 1  # original level before increase
            for j in range(i + 1, len(rows)):
                if (rows[j]["level"] or 1) > parent_level:
                    if j not in indices:  # only auto-cascade non-selected
                        rows[j]["level"] = (rows[j]["level"] or 1) + 1
                        visited.add(j)
                else:
                    break
        self._rebuild_tree(rows)

    def decrease_level(self):
        indices = set(self.selected_rows())
        if not indices:
            return
        rows = self._flatten()
        visited = set()
        for i in indices:
            if i in visited:
                continue
            visited.add(i)
            lv = rows[i]["level"] or 1
            if lv <= 1:
                continue
            rows[i]["level"] = lv - 1
            # Cascade to children
            for j in range(i + 1, len(rows)):
                if (rows[j]["level"] or 1) > lv:
                    child_lv = rows[j]["level"] or 1
                    if child_lv > 1:
                        rows[j]["level"] = child_lv - 1
                        visited.add(j)
                else:
                    break
        self._rebuild_tree(rows)

    def show(self):
        super().show()
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)

    def import_from_file(self):
        fp = get_file()
        if fp and os.path.isfile(fp):
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
        rows = self._flatten()
        if not rows:
            raise Exception("TOC is empty.")
        for r in rows:
            if r["level"] is None:
                r["level"] = pd.NA
            if not r["title"]:
                r["title"] = pd.NA
            if r["page_number"] is None:
                r["page_number"] = pd.NA
        return pd.DataFrame(rows)

    def set_table(self, df):
        df = df.copy()
        df['level'] = pd.to_numeric(df['level'], errors='coerce').round()
        df['page_number'] = pd.to_numeric(df['page_number'], errors='coerce').round()
        df = df.convert_dtypes()
        rows = []
        for _, (level, title, page_number) in df.iterrows():
            lv = None if pd.isna(level) else int(level)
            t = "" if pd.isna(title) else str(title)
            pn = None if pd.isna(page_number) else int(page_number)
            rows.append({"level": lv, "title": t, "page_number": pn})
        self._rebuild_tree(rows)


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
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setWindowTitle("Error")
        error_box.setText("The selected file path is invalid.")
        error_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_box.setWindowFlags(
            error_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        error_box.exec()
        return None


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = TocRefinement()
    w.show()
    sys.exit(app.exec())