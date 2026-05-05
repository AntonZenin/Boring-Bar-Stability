import sys
import os

# Добавляем папку с .pyd в путь поиска Python (на всякий случай)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QLineEdit, QMessageBox
)

# Импорт нашего C++ модуля
try:
    import boring_bar_core
    CORE_AVAILABLE = True
    CORE_ERROR = None
except ImportError as e:
    CORE_AVAILABLE = False
    CORE_ERROR = str(e)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Boring Bar Stability — Stage 1 Test")
        self.setGeometry(200, 200, 500, 200)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Статус C++ модуля
        if CORE_AVAILABLE:
            status_text = f"✓ C++ module loaded. {boring_bar_core.hello()}"
            status_color = "color: green;"
        else:
            status_text = f"✗ C++ module not loaded: {CORE_ERROR}"
            status_color = "color: red;"

        status_label = QLabel(status_text)
        status_label.setStyleSheet(status_color + " font-weight: bold;")
        layout.addWidget(status_label)

        # Поля для двух чисел
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("a ="))
        self.input_a = QLineEdit("2.5")
        input_layout.addWidget(self.input_a)
        input_layout.addWidget(QLabel("b ="))
        self.input_b = QLineEdit("3.7")
        input_layout.addWidget(self.input_b)
        layout.addLayout(input_layout)

        # Кнопка
        self.button = QPushButton("Compute a + b in C++")
        self.button.clicked.connect(self.on_compute)
        layout.addWidget(self.button)

        # Результат
        self.result_label = QLabel("Result: —")
        self.result_label.setStyleSheet("font-size: 14pt;")
        layout.addWidget(self.result_label)

    def on_compute(self):
        if not CORE_AVAILABLE:
            QMessageBox.critical(self, "Error", f"C++ module not available:\n{CORE_ERROR}")
            return

        try:
            a = float(self.input_a.text())
            b = float(self.input_b.text())
        except ValueError:
            QMessageBox.warning(self, "Input error", "Please enter valid numbers.")
            return

        result = boring_bar_core.add(a, b)
        self.result_label.setText(f"Result: {a} + {b} = {result}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
