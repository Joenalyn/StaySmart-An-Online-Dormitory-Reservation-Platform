from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QComboBox, QCheckBox,
    QTextEdit
)
from PyQt5.QtGui import QPixmap, QFont, QCursor
from PyQt5.QtCore import Qt
from database import DatabaseManager
import os

class TenantRegistrationForm(QWidget):
    def __init__(self, tenant_id):
        super().__init__()
        self.setWindowTitle("Tenant Registration")
        self.resize(1000, 720)

        self.tenant_id = tenant_id 
        self.db = DatabaseManager()

        self.photo_path = None
        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(35, 25, 35, 25)
        root.setSpacing(15)

        # ---------------- HEADER ----------------
        header = QHBoxLayout()
        title = QLabel("Tenant Registration")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        top = QHBoxLayout()
        top.setSpacing(20)

        left = QFrame()
        left.setObjectName("card")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(12)

        lbl_pi = QLabel("Personal Information")
        lbl_pi.setFont(QFont("Segoe UI", 14, QFont.Bold))
        left_layout.addWidget(lbl_pi)

        self.inp_fname = self._input("First Name")
        self.inp_lname = self._input("Last Name")
        self.inp_email = self._input("Email")
        self.inp_phone = self._input("Phone Number")
        self.inp_gender = self._combo("Gender", ["Male", "Female", "Prefer not to say"])

        for w in [self.inp_fname, self.inp_lname, self.inp_email, self.inp_phone, self.inp_gender]:
            left_layout.addWidget(w)

        top.addWidget(left, 60)

        right = QFrame()
        right.setObjectName("card")
        r_layout = QVBoxLayout(right)
        r_layout.setContentsMargins(20, 20, 20, 20)
        r_layout.setSpacing(12)

        lbl_pp = QLabel("Profile Picture")
        lbl_pp.setFont(QFont("Segoe UI", 14, QFont.Bold))
        r_layout.addWidget(lbl_pp)

        self.photo = QLabel()
        self.photo.setFixedSize(180, 180)
        self.photo.setStyleSheet("background:#e8efe8; border-radius:12px;")
        self.photo.setAlignment(Qt.AlignCenter)
        self.photo.setText("No Photo")
        r_layout.addWidget(self.photo, alignment=Qt.AlignCenter)

        btn_upload = QPushButton("Upload Photo")
        btn_upload.clicked.connect(self.upload_photo)
        r_layout.addWidget(btn_upload)

        btn_remove = QPushButton("Remove Photo")
        btn_remove.clicked.connect(self.remove_photo)
        r_layout.addWidget(btn_remove)

        r_layout.addStretch()
        top.addWidget(right, 40)

        root.addLayout(top)

        # ---------------- PARENT / GUARDIAN INFORMATION ----------------
        parent = QFrame()
        parent.setObjectName("card")
        p_layout = QVBoxLayout(parent)
        p_layout.setContentsMargins(20, 20, 20, 20)
        p_layout.setSpacing(12)

        lbl_pg = QLabel("Parent / Guardian Information")
        lbl_pg.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p_layout.addWidget(lbl_pg)

        self.inp_pname = self._input("Full Name")
        self.inp_pcontact = self._input("Contact Number")
        self.inp_pemail = self._input("Email")

        for w in [self.inp_pname, self.inp_pcontact, self.inp_pemail]:
            p_layout.addWidget(w)

        root.addWidget(parent)

        # ---------------- TERMS & CONDITIONS ----------------
        terms = QFrame()
        terms.setObjectName("card")
        t_layout = QVBoxLayout(terms)
        t_layout.setContentsMargins(20, 20, 20, 20)
        t_layout.setSpacing(12)

        lbl_t = QLabel("Terms & Conditions")
        lbl_t.setFont(QFont("Segoe UI", 14, QFont.Bold))
        t_layout.addWidget(lbl_t)

        self.terms_text = QTextEdit()
        self.terms_text.setReadOnly(True)
        self.terms_text.setText(
            "By submitting this registration, I confirm that all information provided is true and complete.\n"
            "I agree to follow the dormitory rules, payment policies, and code of conduct."
        )
        t_layout.addWidget(self.terms_text)

        self.chk_agree = QCheckBox("I agree to the terms and conditions")
        t_layout.addWidget(self.chk_agree)

        root.addWidget(terms)

        # ---------------- SUBMIT BUTTON ----------------
        btn_submit = QPushButton("Submit Registration")
        btn_submit.clicked.connect(self.submit_form)
        btn_submit.setFixedHeight(45)
        root.addWidget(btn_submit)

        root.addStretch()

    def _input(self, placeholder):
        box = QLineEdit()
        box.setPlaceholderText(placeholder)
        box.setFixedHeight(36)
        return box

    def _combo(self, placeholder, items):
        combo = QComboBox()
        combo.addItem(placeholder)
        combo.addItems(items)
        combo.setFixedHeight(36)
        return combo

    # --------------------------------------------------
    # PROFILE PHOTO HANDLERS
    # --------------------------------------------------
    def upload_photo(self):
        file, _ = QFileDialog.getOpenFileName(self, "Upload Photo", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            pix = QPixmap(file).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.photo.setPixmap(pix)
            uploads = os.path.join("uploads", "tenant_profiles")
            os.makedirs(uploads, exist_ok=True)

            filename = f"tenant_{self.tenant_id}.png"
            dest = os.path.join(uploads, filename)

            QPixmap(file).save(dest)
            self.photo_path = dest.replace("\\", "/")


    def remove_photo(self):
        self.photo.setPixmap(QPixmap())
        self.photo.setText("No Photo")
        self.photo_path = None


    def submit_form(self):
        if not self.inp_fname.text().strip():
            return QMessageBox.warning(self, "Error", "First Name is required")
        if not self.inp_lname.text().strip():
            return QMessageBox.warning(self, "Error", "Last Name is required")
        if not self.inp_email.text().strip():
            return QMessageBox.warning(self, "Error", "Email is required")
        if not self.inp_phone.text().strip():
            return QMessageBox.warning(self, "Error", "Phone Number is required")
        if self.inp_gender.currentIndex() == 0:
            return QMessageBox.warning(self, "Error", "Select a gender")
        if not self.chk_agree.isChecked():
            return QMessageBox.warning(self, "Error", "You must agree to the terms")

        self.db.save_tenant_profile(
            tenant_id=self.tenant_id,
            first_name=self.inp_fname.text().strip(),
            last_name=self.inp_lname.text().strip(),
            gender=self.inp_gender.currentText(),
            guardian_name=self.inp_pname.text().strip(),
            guardian_contact=self.inp_pcontact.text().strip(),
            guardian_email=self.inp_pemail.text().strip(),
            photo_path=self.photo_path,
            agreed_terms=self.chk_agree.isChecked()
        )

        QMessageBox.information(self, "Success", "Tenant registration saved successfully.")
        self.close()

    # --------------------------------------------------
    # STYLING
    # --------------------------------------------------
    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: #f4f7f5; font-family: Segoe UI; }
            QLabel { color: #1d1d1d; }
            QLineEdit, QComboBox, QTextEdit {
                background: white;
                border: 1px solid #c8d9cc;
                border-radius: 8px;
                padding-left: 8px;
            }
            QFrame#card {
                background: white;
                border-radius: 12px;
                border: 1px solid #d8e8dd;
            }
            QPushButton {
                background: #0f7a3a;
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:hover { background: #0c5d30; }
            QCheckBox { font-size: 13px; }
        """)
