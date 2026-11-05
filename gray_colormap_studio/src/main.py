"""Gray Colormap Studio のエントリーポイント。"""
import sys
from PyQt6.QtWidgets import QApplication
from src.package.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Gray Colormap Studio")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
