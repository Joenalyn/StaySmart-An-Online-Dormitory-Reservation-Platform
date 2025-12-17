from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QPushButton
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
from database import DatabaseManager
import os

class TenantDetailsWindow(QWidget):
    def __init__(self, tenant_id):
        super().__init__()
        self.tenant_id = tenant_id
        self.db = DatabaseManager()

        self.setWindowTitle("Tenant Details")
        self.resize(600, 520)

        self._build_ui()
        self._apply_styles()
        self.load_data()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(15)

        title = QLabel("Tenant Profile")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        main.addWidget(title)

        self.card = QFrame()
        self.card.setObjectName("card")
        layout = QVBoxLayout(self.card)
        layout.setSpacing(10)

        self.lbl_photo = QLabel()
        self.lbl_photo.setFixedSize(120, 120)
        self.lbl_photo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_photo, alignment=Qt.AlignCenter)

        self.lbl_name = QLabel()
        self.lbl_gender = QLabel()
        self.lbl_email = QLabel()
        self.lbl_phone = QLabel()
        self.lbl_guardian = QLabel()
        self.lbl_guardian_contact = QLabel()

        for lbl in [
            self.lbl_name, self.lbl_gender, self.lbl_email,
            self.lbl_phone, self.lbl_guardian, self.lbl_guardian_contact
        ]:
            lbl.setFont(QFont("Segoe UI", 11))
            layout.addWidget(lbl)

        main.addWidget(self.card)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        main.addWidget(btn_close, alignment=Qt.AlignRight)

    def load_data(self):
        profile = self.db.get_tenant_profile(self.tenant_id)

        if not profile:
            user = self.db.fetchone(
                "SELECT fullname, email, contact_no FROM users WHERE user_id=%s",
                (self.tenant_id,)
            )
            if user:
                self.lbl_name.setText(f"Name: {user['fullname']}")
                self.lbl_email.setText(f"Email: {user['email']}")
                self.lbl_phone.setText(f"Phone: {user['contact_no']}")
                self.lbl_gender.setText("Gender: —")
                self.lbl_guardian.setText("Guardian: —")
                self.lbl_guardian_contact.setText("Guardian Contact: —")
            else:
                self.lbl_name.setText("No data found.")
            return

        self.lbl_name.setText(f"Name: {profile['first_name']} {profile['last_name']}")
        self.lbl_gender.setText(f"Gender: {profile['gender']}")
        self.lbl_email.setText(f"Email: {profile['email']}")
        self.lbl_phone.setText(f"Phone: {profile['phone']}")
        self.lbl_guardian.setText(f"Guardian: {profile['guardian_name']}")
        self.lbl_guardian_contact.setText(
            f"📱 Guardian Contact: {profile['guardian_contact']}"
        )

        photo_path = profile.get("photo_path")
        if photo_path:
            abs_path = os.path.abspath(photo_path)
            if os.path.exists(abs_path):
                pix = QPixmap(abs_path).scaled(
                    120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.lbl_photo.setPixmap(pix)
            else:
                self.lbl_photo.setText("No Photo")

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background:#f2f5f3;
                font-family: Segoe UI;
            }
            QFrame#card {
                background:white;
                border-radius:14px;
                border:1px solid #d6e4db;
                padding:16px;
            }
            QPushButton {
                background:#0f7a3a;
                color:white;
                padding:6px 14px;
                border-radius:8px;
            }
            QPushButton:hover { background:#0c5d30; }
        """)
