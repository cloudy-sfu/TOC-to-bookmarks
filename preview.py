import os
import sys

import cv2
import fitz  # PyMuPDF
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLineEdit, QHBoxLayout,
    QVBoxLayout, QLabel, QWidget, QMessageBox, QFileDialog
)


class PDFViewer(QMainWindow):
    def __init__(self, filepath):
        super().__init__()

        self.setWindowTitle("PDF Viewer")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.filepath = filepath
        self.current_page = 1
        screen = QApplication.primaryScreen()
        if sys.platform.startswith("darwin"):  # macOS
            self.zoom_pct = screen.devicePixelRatio()
        else:  # Windows, Linux
            self.zoom_pct = screen.logicalDotsPerInch() / 96
        font_size = round(14 * self.zoom_pct)
        self.screen_height = screen.geometry().height()
        self.screen_width = screen.geometry().width()

        # Load PDF document
        try:
            self.document = fitz.open(self.filepath)
            self.total_pages = self.document.page_count
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF. [Details] {e}")
            self.close()

        # Create UI elements
        # Layouts
        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Buttons and input
        self.page_input = QLineEdit()
        self.page_input.setStyleSheet(f"font-size: {font_size}px;")
        self.page_input.setPlaceholderText("Enter page number")

        total_pages_label = QLabel(f"[Total pages: {self.total_pages}]")
        total_pages_label.setStyleSheet(f"font-size: {font_size}px;")

        jump_button = QPushButton("Jump to")
        jump_button.setStyleSheet(f"font-size: {font_size}px;")
        jump_button.clicked.connect(self.jump_to_page)

        prev_button = QPushButton("Previous")
        prev_button.setStyleSheet(f"font-size: {font_size}px;")
        prev_button.clicked.connect(self.previous_page)

        next_button = QPushButton("Next")
        next_button.setStyleSheet(f"font-size: {font_size}px;")
        next_button.clicked.connect(self.next_page)

        done_button = QPushButton("Done")
        done_button.setStyleSheet(f"font-size: {font_size}px;")
        done_button.clicked.connect(self.close)

        # Add widgets to button layout
        button_layout.addWidget(total_pages_label)
        button_layout.addWidget(self.page_input)
        button_layout.addWidget(jump_button)
        button_layout.addWidget(prev_button)
        button_layout.addWidget(next_button)
        button_layout.addWidget(done_button)

        # Task name
        self.task_name_label = QLabel()
        self.task_name_label.setStyleSheet(f"font-size: {font_size}px;")
        text_height = self.task_name_label.fontMetrics().height()
        self.task_name_label.setFixedHeight(round(text_height * 1.2))

        # PDF Preview Area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        # forbid to set border, otherwise "preview_label" will gradually enlarge (2 *
        # border width) pixels when turning pages
        self.preview_label.setStyleSheet(f"font-size: {font_size}px;")

        # Add button layout and preview to main layout
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.task_name_label)
        main_layout.addWidget(self.preview_label)

        # Create a central widget and set layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Set window dimensions
        y = round(28 * self.zoom_pct)  # title bar height
        window_height = self.screen_height - y
        window_width = round(window_height / 11 * 8.5)  # Letter aspect-ratio
        x = round((self.screen_width - window_width) / 2)
        self.setGeometry(x, y, window_width, window_height)

    def set_text_name(self, task_name):
        self.task_name_label.setText(task_name)

    def render_page(self, targeted_page):
        if not (1 <= targeted_page <= self.total_pages):
            self.show_error_window("Page out of range")
            return
        self.current_page = targeted_page
        page = self.document[self.current_page - 1]
        pix = page.get_pixmap(dpi=400)
        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride,
                        QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        # Scale the pixmap to fit the label with "letter" aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.preview_label.width(), self.preview_label.height(), Qt.KeepAspectRatio)
        self.preview_label.setPixmap(scaled_pixmap)

    def to_cv2_array(self, targeted_page):
        page = self.document[targeted_page - 1]
        # Render the page to a pixmap
        pix = page.get_pixmap()
        image_array = (np.frombuffer(pix.samples, dtype=np.uint8)
                       .reshape(pix.height, pix.width, pix.n))
        if pix.n == 4:  # RGBA to BGR
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:  # RGB to BGR
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        return image_array

    def jump_to_page(self):
        try:
            page_number = int(self.page_input.text())
        except ValueError:
            self.show_error_window("Invalid page number")
            return
        self.render_page(page_number)

    def previous_page(self):
        self.render_page(self.current_page - 1)

    def next_page(self):
        self.render_page(self.current_page + 1)

    def show_error_window(self, message):
        error_dialog = QMessageBox(self)
        error_dialog.setText(message)
        error_dialog.setIcon(QMessageBox.Warning)
        error_dialog.setStandardButtons(QMessageBox.Ok)
        # Block interaction with main window until this dialog is closed
        error_dialog.setModal(True)
        error_dialog.exec_()


def get_file():
    fp, _ = QFileDialog.getOpenFileName(
        parent=None,
        caption="Select the book",
        directory=rf"C:\Users\{os.environ['USERNAME']}\Desktop",
        filter="PDF File (*.pdf)",
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
