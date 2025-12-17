import sys
from PyQt5.QtWidgets import QApplication
from login import LoginWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # optional but good
    window = LoginWindow()   # ENTRY POINT
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
