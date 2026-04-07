import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QDialogButtonBox


class OCRDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowContextHelpButtonHint)
        screen = QApplication.primaryScreen()
        if sys.platform.startswith("darwin"):
            zoom_factor = screen.devicePixelRatio()
        else:
            zoom_factor = screen.logicalDotsPerInch() / 96
        font_size = round(14 * zoom_factor)
        self.setStyleSheet(f"font-size: {font_size}px;")
        layout = QVBoxLayout()
        self.label = QLabel("Do you want to run OCR model to recognize table of content?")
        layout.addWidget(self.label)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)
        layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = OCRDialog()
    print(dialog.exec() == QDialog.DialogCode.Accepted)
