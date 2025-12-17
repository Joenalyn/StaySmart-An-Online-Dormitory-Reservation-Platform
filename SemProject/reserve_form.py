# reserve_form.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QLineEdit,
    QPushButton, QMessageBox, QTextEdit, QCheckBox, QComboBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal

from database import DatabaseManager
from registrationform import TenantRegistrationForm



class ReserveForm(QWidget):
    """
    Reservation form opened from RoomDetailsDialog.
    After submit, creates a WAITING rental application
    that appears in Owner Dashboard -> Pending Requests.
    """
    submitted = pyqtSignal(int)

    def __init__(self, tenant_id, dorm_id, room_id, host_id=None):
        super().__init__()
        self.setWindowTitle("Reserve Room")
        self.resize(700, 520)

        self.db = DatabaseManager()
        self.tenant_id = tenant_id
        self.dorm_id = dorm_id
        self.room_id = room_id
        self.host_id = host_id

        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(25, 20, 25, 20)
        root.setSpacing(12)

        title = QLabel("Room Reservation Form")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        root.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        c = QVBoxLayout(card)
        c.setContentsMargins(16, 16, 16, 16)
        c.setSpacing(8)

        lbl_info = QLabel("Your Information")
        lbl_info.setFont(QFont("Segoe UI", 12, QFont.Bold))
        c.addWidget(lbl_info)

        self.inp_fname = QLineEdit()
        self.inp_fname.setPlaceholderText("First Name")

        self.inp_lname = QLineEdit()
        self.inp_lname.setPlaceholderText("Last Name")

        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("Email")

        self.inp_phone = QLineEdit()
        self.inp_phone.setPlaceholderText("Phone Number")

        self.inp_gender = QComboBox()
        self.inp_gender.addItems(["Select Gender", "Male", "Female", "Prefer not to say"])

        for w in [self.inp_fname, self.inp_lname, self.inp_email, self.inp_phone, self.inp_gender]:
            w.setFixedHeight(34)
            c.addWidget(w)

        root.addWidget(card)

        notes_card = QFrame()
        notes_card.setObjectName("card")
        n = QVBoxLayout(notes_card)
        n.setContentsMargins(16, 16, 16, 16)
        n.setSpacing(8)

        lbl_notes = QLabel("Notes to Owner (optional)")
        lbl_notes.setFont(QFont("Segoe UI", 12, QFont.Bold))
        n.addWidget(lbl_notes)

        self.inp_notes = QTextEdit()
        self.inp_notes.setPlaceholderText("Message or special requests...")
        n.addWidget(self.inp_notes)

        root.addWidget(notes_card)

        # ---- Terms ----
        self.chk_agree = QCheckBox("I confirm that all details are correct and I agree to the dorm rules.")
        root.addWidget(self.chk_agree)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("ghostBtn")
        btn_cancel.clicked.connect(self.close)

        btn_submit = QPushButton("Submit Reservation")
        btn_submit.clicked.connect(self.submit_reservation)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_submit)

        root.addLayout(btn_row)

    # --------------------------------------------------
    # SUBMIT
    # --------------------------------------------------
    def submit_reservation(self):
        # validations
        if not self.inp_fname.text().strip():
            QMessageBox.warning(self, "Error", "First Name is required.")
            return
        if not self.inp_lname.text().strip():
            QMessageBox.warning(self, "Error", "Last Name is required.")
            return
        if not self.inp_email.text().strip():
            QMessageBox.warning(self, "Error", "Email is required.")
            return
        if not self.inp_phone.text().strip():
            QMessageBox.warning(self, "Error", "Phone Number is required.")
            return
        if self.inp_gender.currentIndex() == 0:
            QMessageBox.warning(self, "Error", "Please select a gender.")
            return
        if not self.chk_agree.isChecked():
            QMessageBox.warning(self, "Error", "You must agree before submitting.")
            return

        notes = self.inp_notes.toPlainText().strip() or None

        fullname = f"{self.inp_fname.text().strip()} {self.inp_lname.text().strip()}".strip()
        email = self.inp_email.text().strip()
        phone = self.inp_phone.text().strip()
        gender = self.inp_gender.currentText()

        app_id = self.db.create_rental_application(
            tenant_id=self.tenant_id,
            dorm_id=self.dorm_id,
            room_id=self.room_id,
            notes=notes,
            tenant_fullname=fullname,
            tenant_email=email,
            tenant_phone=phone,
            tenant_gender=gender
        )

        if app_id:
            QMessageBox.information(
                self, "Submitted",
                "Reservation sent! Please complete your tenant registration."
            )

            self.reg_form = TenantRegistrationForm(tenant_id=self.tenant_id)
            self.reg_form.setWindowModality(Qt.ApplicationModal)
            self.reg_form.show()
            self.reg_form.raise_()
            self.reg_form.activateWindow()

            # keep existing signal (important)
            self.submitted.emit(app_id)

            self.close()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background:#f4f7f5;
                font-family:Segoe UI;
            }
            QFrame#card {
                background:white;
                border-radius:12px;
                border:1px solid #d8e8dd;
            }
            QLineEdit, QTextEdit, QComboBox {
                background:white;
                border:1px solid #c8d9cc;
                border-radius:8px;
                padding-left:8px;
                font-size:12px;
            }
            QTextEdit {
                min-height:90px;
                padding:8px;
            }
            QPushButton {
                background:#0f7a3a;
                color:white;
                padding:8px 14px;
                border-radius:8px;
                font-size:12px;
            }
            QPushButton:hover { background:#0c5d30; }

            QPushButton#ghostBtn {
                background:#e6e6e6;
                color:#333;
            }
            QPushButton#ghostBtn:hover {
                background:#d0d0d0;
            }
            QCheckBox {
                font-size:12px;
            }
        """)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    w = ReserveForm(tenant_id=1, dorm_id=1, room_id=1, host_id=1)
    w.show()
    sys.exit(app.exec_())
