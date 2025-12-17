import sys
import os
from auth import Auth
from login import LoginWindow

import re
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QRect, QRectF, pyqtSlot, QPropertyAnimation, QEasingCurve, QSize, QParallelAnimationGroup, pyqtProperty
)
from PyQt5.QtGui import QFont, QPixmap, QPainter, QPainterPath, QIcon

from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QMessageBox, QFrame, QStackedWidget, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QGraphicsProxyWidget, QGraphicsScale, QGraphicsTransform
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE_DIR, "assets")

def load_pixmap(path):
    if os.path.exists(path):
        return QPixmap(path)
    else:
        print(f"Warning: Asset {path} not found. Using placeholder.")
        return QPixmap()

class RoundedImageLabel(QLabel):
    """QLabel that draws a pixmap with rounded corners and keeps aspect ratio."""
    def __init__(self, pixmap: QPixmap, radius=20, parent=None):
        super().__init__(parent)
        self._pix = pixmap
        self.radius = radius
        self.setScaledContents(False)
        self.setMinimumSize(120, 80)
        self.setMaximumHeight(260)
        self._scale_factor = 1.0
        self.anim = None

    def setPixmap(self, pixmap: QPixmap):
        self._pix = pixmap
        super().setPixmap(pixmap)

    def paintEvent(self, event):
        if not self._pix or self._pix.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.radius, self.radius)
        painter.setClipPath(path)

        scaled_size = QSize(int(rect.width() * self._scale_factor), int(rect.height() * self._scale_factor))
        scaled = self._pix.scaled(scaled_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        x = (rect.width() - scaled.width()) // 2
        y = (rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

    def scale_factor(self):
        return self._scale_factor

    def set_scale_factor(self, value):
        self._scale_factor = value
        self.update()

    scale_factor = pyqtProperty(float, scale_factor, set_scale_factor)

    def enterEvent(self, event):
        self.raise_()
        self.animate_scale(1.0, 1.06)

    def leaveEvent(self, event):
        self.animate_scale(1.06, 1.0)

    def animate_scale(self, start, end):
        if self.anim and getattr(self.anim, 'state', None) == QPropertyAnimation.Running:
            try:
                self.anim.stop()
            except Exception:
                pass
        self.anim = QPropertyAnimation(self, b"scale_factor")
        self.anim.setDuration(240)
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.start()


class HoverRoundedImageLabel(RoundedImageLabel):
    """Responsive rounded image label with shadow + fade on hover.

    Behavior:
      - Keeps original QPixmap in self._orig_pix
      - Rescales rounded pixmap on resizeEvent or when set_base_size() is called
      - On hover: fade to full opacity; on leave: fade to 0.85 opacity
      - Slight scale handled by base class scale property
    """

    def __init__(self, pixmap: QPixmap, radius=30, parent=None):
        super().__init__(pixmap, radius, parent)
        self._orig_pix = pixmap
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._opacity_eff.setOpacity(1.0)
        self._base_size = QSize(200, 200)


        self._fade_anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(28)
        self._shadow.setOffset(0, 10)
        self._shadow.setColor(Qt.black)

        self.update_rounded_pixmap()

    def update_rounded_pixmap(self):
        if self._orig_pix is None or self._orig_pix.isNull():
            return
        w = max(1, self._base_size.width())
        h = max(1, self._base_size.height())
        scaled = self._orig_pix.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        rounded = QPixmap(scaled.size())
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, scaled.width(), scaled.height(), self.radius, self.radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        super().setPixmap(rounded)

    def set_base_size(self, w, h):
        self._base_size = QSize(w, h)
        self.setFixedSize(w, h)
        self.update_rounded_pixmap()

    def enterEvent(self, event):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_eff.opacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

        super().enterEvent(event)

    def leaveEvent(self, event):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_eff.opacity())
        self._fade_anim.setEndValue(0.85)
        self._fade_anim.start()
        super().leaveEvent(event)

class SignupOwnerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StaySmart")
        self.setMinimumSize(900, 560)
        self.auth = Auth()
        self.init_ui()
        self._first_show_done = False

    def handle_signup(self):
        fullname = self.name.text().strip()
        username = self.username.text().strip()
        contact = self.contact.text().strip()
        email = self.email.text().strip()
        password = self.password.text().strip()
        confirm_password = self.conpassword.text().strip()

        required_fields = [fullname, username, contact, email, password, confirm_password]
        if any(field == "" for field in required_fields):
            QMessageBox.warning(self, "Missing Information", "Please fill in all required fields.")
            return

        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email):
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return

        contact_regex = r"^09\d{9}$"
        if not re.match(contact_regex, contact):
            QMessageBox.warning(self, "Invalid Contact", "Phone number must be 11 digits, start with 09, and contain numbers only.")
            return

        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password):
            QMessageBox.warning(self, "Weak Password", "Password should contain upper, lower, number, and be at least 8 chars.")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
            return

        try:
            success, message = self.auth.admin_signup(
                fullname,
                username,
                contact,
                email,
                password
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
            return

        if success:
            QMessageBox.information(self, "Success!", "Admin account created successfully!")
            self.back_to_login()
        else:
            QMessageBox.critical(self, "Sign Up Failed", str(message))


    def handle_nav_click(self, link):
        print("Navigation clicked:", link)

        if link == "HOME":
            print("Go to Home Page")
        elif link == "AVAILABLE ROOMS":
            print("Go to Rooms Page")
        elif link == "ABOUT US":
            print("Go to About Us Page")

    def back_to_login(self):
        self.next_window = LoginWindow()
        self.next_window.show()
        self.close()

    def init_ui(self):
        self.setup_fonts()
        self.setup_layout()
        self.setup_left_panel()
        self.setup_right_panel()
        self.connect_signals()

    def setup_fonts(self):
        self.font_title = QFont("Poppins", 30, QFont.Bold)
        self.font_lbl = QFont("Poppins", 10)
        self.font_nav = QFont("Poppins", 10)

    def setup_layout(self):
        self.root = QHBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

    def setup_left_panel(self):
        self.left = QFrame()
        self.left.setObjectName("leftPanel")
        self.left.setStyleSheet("""
            QFrame#leftPanel {
                background: #FFFFFF;
                border-right: 1px solid #E6E6E6;
            }
        """)
        left_layout = QVBoxLayout(self.left)
        left_layout.setContentsMargins(48, 28, 48, 28)
        left_layout.setSpacing(14)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(6)

        # Logo
        logo_pix = load_pixmap(os.path.join(ASSETS, "logo.png"))
        logo = QLabel()
        logo.setPixmap(logo_pix.scaled(65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Title
        title_label = QLabel("STAYSMART")
        title_label.setFont(QFont("Poppins", 19, QFont.Bold))
        title_label.setStyleSheet("color: #0A3B2E;")
        title_label.setAlignment(Qt.AlignVCenter)

        logo_row.addWidget(logo)
        logo_row.addWidget(title_label)
        logo_row.addStretch()

        left_layout.addLayout(logo_row)

        # SIGN UP title
        title = QLabel("SIGN UP")
        title.setFont(self.font_title)
        title.setStyleSheet("color: #123C24; padding-top: 5px;")
        left_layout.addWidget(title, alignment=Qt.AlignCenter)

        # Create + Create now row
        left_layout.addSpacing(2)
        create = QLabel("Already have an account?")
        createlink = QLabel("<a href='#'>Login</a>")
        create.setFont(self.font_lbl)
        create.setStyleSheet("color: #718096;")
        createlink.setTextFormat(Qt.RichText)
        createlink.setOpenExternalLinks(False)
        createlink.setText("<a style='color:#0A3B2E; font-weight: Bold; text-decoration:underline;' href='#'>Login</a>")
        createlink.setTextFormat(Qt.RichText)
        createlink.setOpenExternalLinks(False)
        createlink.linkActivated.connect(self.back_to_login)  # Added handler

        logo_row = QHBoxLayout()
        logo_row.addStretch()
        logo_row.addWidget(create)
        logo_row.addWidget(createlink)
        logo_row.addStretch()

        left_layout.addLayout(logo_row)

        # OWNER name field
        left_layout.addSpacing(2)
        u_lbl = QLabel("Owner name")
        u_lbl.setFont(self.font_lbl)
        u_lbl.setStyleSheet("color: #95a0b1;")
        left_layout.addWidget(u_lbl, alignment=Qt.AlignLeft)

        studentname_container = QFrame()
        studentname_container.setStyleSheet("""
            QFrame {
                border: 1px solid #718096;
                border-radius: 15px;
                background: white;
            }
        """)
        studentname_container.setFixedHeight(70)

        name_layout = QHBoxLayout(studentname_container)
        name_layout.setContentsMargins(12, 0, 12, 0)
        name_layout.setSpacing(0)

        self.name = QLineEdit()
        self.name.setPlaceholderText("")
        self.name.setFont(QFont("Poppins", 10))
        self.name.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                padding-left: 10px;
            }
        """)

        name_layout.addWidget(self.name)
        left_layout.addWidget(studentname_container)

        # Username and Contact row
        label_row = QHBoxLayout()
        label_row.setSpacing(2)

        user_lbl = QLabel("Username")
        contact_lbl = QLabel("Contact number")

        user_lbl.setFont(self.font_lbl)
        user_lbl.setStyleSheet("color: #95a0b1;")

        contact_lbl.setFont(self.font_lbl)
        contact_lbl.setStyleSheet("color: #95a0b1; padding-left: 3px;")

        label_row.addWidget(user_lbl)
        label_row.addWidget(contact_lbl)

        left_layout.addSpacing(2)
        left_layout.addLayout(label_row)

        row = QHBoxLayout()
        row.setSpacing(20)
        row.setContentsMargins(0, 0, 0, 0)

        username_container = QFrame()
        username_container.setStyleSheet("""
            QFrame {
                border: 1px solid #718096;
                border-radius: 15px;
                background: white;
            }
        """)
        username_container.setFixedHeight(70)
        username_container.setMinimumWidth(220)

        username_layout = QHBoxLayout(username_container)
        username_layout.setContentsMargins(12, 0, 12, 0)

        self.username = QLineEdit()
        self.username.setPlaceholderText("")
        self.username.setFont(QFont("Poppins", 10))
        self.username.setStyleSheet("border: none; padding-left: 10px;")

        username_layout.addWidget(self.username)

        contact_container = QFrame()
        contact_container.setStyleSheet("""
            QFrame {
                border: 1px solid #718096;
                border-radius: 15px;
                background: white;
            }
        """)
        contact_container.setFixedHeight(70)
        contact_container.setMinimumWidth(220)

        contact_layout = QHBoxLayout(contact_container)
        contact_layout.setContentsMargins(12, 0, 12, 0)

        self.contact = QLineEdit()
        self.contact.setPlaceholderText("")
        self.contact.setFont(QFont("Poppins", 10))
        self.contact.setStyleSheet("border: none; padding-left: 10px;")

        contact_layout.addWidget(self.contact)

        row.addWidget(username_container)
        row.addWidget(contact_container)

        left_layout.addLayout(row)

        # Email field
        left_layout.addSpacing(2)
        email_lbl = QLabel("Email")
        email_lbl.setFont(self.font_lbl)
        email_lbl.setStyleSheet("color: #95a0b1;")
        left_layout.addWidget(email_lbl, alignment=Qt.AlignLeft)

        email_container = QFrame()
        email_container.setStyleSheet("""
            QFrame {
                border: 1px solid #718096;
                border-radius: 15px;
                background: white;
            }
        """)
        email_container.setFixedHeight(70)

        email_layout = QHBoxLayout(email_container)
        email_layout.setContentsMargins(12, 0, 12, 0)
        email_layout.setSpacing(0)

        self.email = QLineEdit()
        self.email.setPlaceholderText("")
        self.email.setFont(QFont("Poppins", 10))
        self.email.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                padding-left: 10px;
            }
        """)

        email_layout.addWidget(self.email)
        left_layout.addWidget(email_container)

        # Password field
        left_layout.addSpacing(2)
        p_lbl = QLabel("Password")
        p_lbl.setFont(self.font_lbl)
        p_lbl.setStyleSheet("color: #95a0b1;")
        left_layout.addWidget(p_lbl, alignment=Qt.AlignLeft)

        password_container = QFrame()
        password_container.setStyleSheet("""
            QFrame {
                border: 1px solid #718096;
                border-radius: 15px;
                background: white;
            }
        """)
        password_container.setFixedHeight(70)

        container_layout = QHBoxLayout(password_container)
        container_layout.setContentsMargins(12, 0, 12, 0)
        container_layout.setSpacing(0)

        self.password = QLineEdit()
        self.password.setPlaceholderText("")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFont(QFont("Poppins", 10))
        self.password.setStyleSheet("border: none; padding-left: 5px;")
        container_layout.addWidget(self.password)

        eye_btn = QPushButton()
        eye_btn.setCursor(Qt.PointingHandCursor)
        eye_icon_path = os.path.join(ASSETS, "visibility-eye-svgrepo-com.svg")
        eye_btn.setIcon(QIcon(load_pixmap(eye_icon_path)))
        eye_btn.setIconSize(QSize(30, 30))
        eye_btn.setStyleSheet("""
            QPushButton {
                border: none;
                padding-right: 20px;
                background: transparent;
            }
            QPushButton:hover {
                background: #F5F5F5;
                border-radius: 10px;
            }
        """)
        eye_btn.clicked.connect(self.toggle_password)
        container_layout.addWidget(eye_btn)

        left_layout.addWidget(password_container)

        left_layout.addSpacing(2)
        cp_lbl = QLabel("")
        cp_lbl.setFont(self.font_lbl)
        cp_lbl.setStyleSheet("color: #95a0b1;")
        left_layout.addWidget(cp_lbl, alignment=Qt.AlignLeft)

        conpassword_container = QFrame()
        conpassword_container.setStyleSheet("""
            QFrame {
                border: 1px solid #718096;
                border-radius: 15px;
                background: white;
            }
        """)
        conpassword_container.setFixedHeight(70)

        container_layout = QHBoxLayout(conpassword_container)
        container_layout.setContentsMargins(12, 0, 12, 0)
        container_layout.setSpacing(0)

        self.conpassword = QLineEdit()
        self.conpassword.setPlaceholderText("")
        self.conpassword.setEchoMode(QLineEdit.Password)
        self.conpassword.setFont(QFont("Poppins", 10))
        self.conpassword.setStyleSheet("border: none; padding-left: 5px;")
        container_layout.addWidget(self.conpassword)

        eye_btn = QPushButton()
        eye_btn.setCursor(Qt.PointingHandCursor)
        eye_btn.setIcon(QIcon(load_pixmap(eye_icon_path)))
        eye_btn.setIconSize(QSize(30, 30))
        eye_btn.setStyleSheet("""
            QPushButton {
                border: none;
                padding-right: 20px;
                background: transparent;
            }
            QPushButton:hover {
                background: #F5F5F5;
                border-radius: 10px;
            }
        """)
        eye_btn.clicked.connect(self.toggle_conpassword)
        container_layout.addWidget(eye_btn)

        left_layout.addWidget(conpassword_container)

        left_layout.addSpacing(10)
        self.login_btn = QPushButton("Sign up")
        self.login_btn.clicked.connect(self.handle_signup)
        self.login_btn.setFixedHeight(70)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #11402D;
                color: white;
                border-radius: 17px;
                font-size: 25px;
            }
        """)
        self.login_btn.installEventFilter(self)
        left_layout.addWidget(self.login_btn)
        
        self.left.setMinimumWidth(520)
        self.left.setMinimumHeight(995)
        left_layout.addStretch()

        self.root.addWidget(self.left, 45)

    def setup_right_panel(self):
        self.right = QFrame()
        self.right.setObjectName("rightPanel")
        self.right.setStyleSheet("""
            QFrame#rightPanel {
                background: qlineargradient(spread:pad, x1:0.0, y1:0.0, x2:1.0, y2:1.0,
                    stop:0 #0E3E2B, stop:1 #11402D);
            }
        """)
        right_layout = QVBoxLayout(self.right)

        self.overlay_bg = QLabel(self.right)
        self.overlay_bg.setPixmap(QPixmap("assets/Circle.png"))
        self.overlay_bg.setScaledContents(True)
        self.overlay_bg.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.overlay_bg.lower()

        nav = QHBoxLayout()
        nav.setSpacing(24)
        nav.setContentsMargins(20, 20, 20, 0)

        nav.addStretch()

        for txt in ["HOME", "AVAILABLE ROOMS", "ABOUT US"]:
            link = QLabel(f"<a style='color:#FFFFFF; text-decoration:underline;' href='{txt}'>{txt}</a>")
            link.setFont(self.font_nav)
            link.setTextFormat(Qt.RichText)
            link.setTextInteractionFlags(Qt.TextBrowserInteraction)
            link.setOpenExternalLinks(False)
            link.linkActivated.connect(self.handle_nav_click)
            nav.addWidget(link)
        self.right.setMinimumWidth(500)
        nav.addStretch()

        right_layout.addLayout(nav)

        carousel_container = QWidget()
        carousel_layout = QHBoxLayout(carousel_container)
        carousel_layout.setSpacing(19)
        right_layout.addSpacing(200)
        carousel_layout.setContentsMargins(100, 8, 150, 8)
        carousel_layout.setAlignment(Qt.AlignCenter)

        self.left_img = HoverRoundedImageLabel(load_pixmap("assets/room2.png"), radius=20, parent=carousel_container)
        self.center_img = HoverRoundedImageLabel(load_pixmap("assets/room1.png"), radius=20, parent=carousel_container)
        self.right_img = HoverRoundedImageLabel(load_pixmap("assets/room3.png"), radius=20, parent=carousel_container)

        self.left_img.setObjectName("left")
        self.center_img.setObjectName("center")
        self.right_img.setObjectName("right")

        carousel_layout.addWidget(self.left_img)
        carousel_layout.addWidget(self.center_img)
        carousel_layout.addWidget(self.right_img)

        right_layout.addWidget(carousel_container)

        self.left_img.stackUnder(self.center_img)
        self.right_img.stackUnder(self.center_img)
        self.center_img.raise_()

        self.carousel = carousel_container
        self.carousel_layout = carousel_layout
        self.right_layout = right_layout

        right_layout.addSpacing(50)
        intro_title = QLabel("INTRODUCING")
        intro_title.setFont(QFont("Poppins", 16, QFont.Bold))
        intro_title.setStyleSheet("color: white;")
        intro_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(intro_title)

        text = (
            "<p align='justify'>"
            "StaySmart, an online platform that replaces slow, manual "
            "dormitory reservations with a faster and more organized "
            "digital system. It allows students to easily view and reserve"
            "rooms while helping administrators manage records "
            "accurately and efficiently. Overall, the system "
            "improves convenience, transparency, and the overall experience of "
            "dormitory operations."
            "</p>"
        )

        intro_desc = QLabel(text)
        intro_desc.setWordWrap(True)
        intro_desc.setTextFormat(Qt.RichText)
        intro_desc.setStyleSheet("color: #EAF6EE;")
        intro_desc.setFont(QFont("Poppins", 11))
        intro_desc.setContentsMargins(100, 20, 100, 0)
        right_layout.addWidget(intro_desc)
        right_layout.addStretch()

        self.root.addWidget(self.right, 55)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if hasattr(self, "overlay_bg"):
            self.overlay_bg.resize(self.right.width(), self.right.height())

        if not hasattr(self, 'right') or self.right is None:
            return

        rw = max(320, int(self.right.width() * 0.70))
        center_w = int(rw * 0.65)
        side_w = int(center_w * 0.70)
        center_h = int(center_w * 0.66)
        side_h = int(side_w * 0.66)

        self.center_img.set_base_size(center_w, center_h)
        self.left_img.set_base_size(side_w, side_h)
        self.right_img.set_base_size(side_w, side_h)


    def eventFilter(self, obj, event):
        if obj is self.login_btn:
            if event.type() == event.Enter:
                self._animate_button_scale(self.login_btn, 1.0, 1.04)
            elif event.type() == event.Leave:
                self._animate_button_scale(self.login_btn, 1.04, 1.0)
        return super().eventFilter(obj, event)

    def _animate_button_scale(self, btn: QPushButton, start: float, end: float):
        if not hasattr(btn, "_scale_proxy"):
            proxy = QGraphicsProxyWidget()
            proxy.setWidget(btn)

            scale = QGraphicsScale()
            scale.setXScale(1.0)
            scale.setYScale(1.0)

            proxy.setTransformations([scale])

            btn._scale_proxy = proxy
            btn._scale = scale

        anim = QPropertyAnimation(btn._scale, b"xScale")
        anim.setDuration(180)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.InOutQuad)

        anim2 = QPropertyAnimation(btn._scale, b"yScale")
        anim2.setDuration(180)
        anim2.setStartValue(start)
        anim2.setEndValue(end)
        anim2.setEasingCurve(QEasingCurve.InOutQuad)

        anim.start()
        anim2.start()

    @pyqtSlot()
    def toggle_password(self):
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
        else:
            self.password.setEchoMode(QLineEdit.Password)

    @pyqtSlot()
    def toggle_conpassword(self):
        if self.conpassword.echoMode() == QLineEdit.Password:
            self.conpassword.setEchoMode(QLineEdit.Normal)
        else:
            self.conpassword.setEchoMode(QLineEdit.Password)

    def showEvent(self, event):
        super().showEvent(event)
        self.layout().activate()
        if not self._first_show_done:
            self._first_show_done = True
            self._run_entrance_animations()

    def _run_entrance_animations(self):
        left_op = QGraphicsOpacityEffect(self.left)
        self.left.setGraphicsEffect(left_op)
        left_op.setOpacity(0.0)

        anim_op_l = QPropertyAnimation(left_op, b"opacity")
        anim_op_l.setDuration(600)
        anim_op_l.setStartValue(0.0)
        anim_op_l.setEndValue(1.0)
        anim_op_l.setEasingCurve(QEasingCurve.OutCubic)

        geom = self.left.geometry()
        start_geom = QRect(geom.x() - 60, geom.y(), geom.width(), geom.height())
        anim_geom_l = QPropertyAnimation(self.left, b"geometry")
        anim_geom_l.setDuration(650)
        anim_geom_l.setStartValue(start_geom)
        anim_geom_l.setEndValue(geom)
        anim_geom_l.setEasingCurve(QEasingCurve.OutCubic)

        right_op = QGraphicsOpacityEffect(self.right)
        self.right.setGraphicsEffect(right_op)
        right_op.setOpacity(0.0)
        anim_op_r = QPropertyAnimation(right_op, b"opacity")
        anim_op_r.setDuration(700)
        anim_op_r.setStartValue(0.0)
        anim_op_r.setEndValue(1.0)
        anim_op_r.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_op_l)
        group.addAnimation(anim_geom_l)
        group.addAnimation(anim_op_r)
        group.start()

        def pulse():
            carousel_widget = self.carousel
            g = carousel_widget.geometry()
            anim = QPropertyAnimation(carousel_widget, b"geometry")
            anim.setDuration(420)
            anim.setStartValue(QRect(g.x(), g.y(), g.width() * 95 // 100, g.height() * 95 // 100))
            anim.setEndValue(g)
            anim.setEasingCurve(QEasingCurve.OutBack)
            anim.start()
            carousel_widget._pulse_anim = anim

        QTimer.singleShot(650, pulse)


def main():

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = SignupOwnerWindow()
    w.showNormal()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
