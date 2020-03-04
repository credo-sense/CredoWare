from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel


class CustomDialog(QDialog):

    def __init__(self, *args, **kwargs):
        super(CustomDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("Message")

        self.lbl = QLabel("Reading logger data...")
        self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setFont(QFont('Arial', 15))

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.lbl)
        self.setLayout(self.layout)
        self.resize(300, 100)