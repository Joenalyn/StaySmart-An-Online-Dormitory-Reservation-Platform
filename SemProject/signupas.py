import sys
import os
from signup_students import SignupStudentWindow
from signup_admin import SignupOwnerWindow
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
        self._fade_anim.setEndValue(0.85)  # Slight fade on leave
        self._fade_anim.start()
        super().leaveEvent(event)

class SignupasWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StaySmart")
        self.setMinimumSize(900, 560) # Assuming auth is a module with signup and login methods
        self.init_ui()
        self._first_show_done = False

    def handle_nav_click(self, link):
        print("Navigation clicked:", link)

        if link == "HOME":
            print("Go to Home Page")
        elif link == "AVAILABLE ROOMS":
            print("Go to Rooms Page")
        elif link == "ABOUT US":
            print("Go to About Us Page")

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
        # Left login panel
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

        # --- Logo + Title Row ---
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
        title = QLabel("SIGN UP AS")
        font = QFont("Poppins", 22)
        font.setBold(True)
        title.setFont(font)

        title.setStyleSheet("color: #123C24; padding-top: 250px;")
        left_layout.addWidget(title, alignment=Qt.AlignCenter)

        left_layout.addSpacing(30)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)

        self.btn_tenant = QPushButton("TENANT")
        self.btn_owner = QPushButton("OWNER")

        btn_style = """
            QPushButton {
                background-color: #0A3B2E;
                color: white;
                border: 2px solid #0A3B2E;
                border-radius: 14px;
                padding: 10px 28px;
                font-size: 17px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0d4c39;
            }
        """

        btn_outline_style = """
            QPushButton {
                background-color: transparent;
                color: #0A3B2E;
                border: 2px solid #0A3B2E;
                border-radius: 14px;
                padding: 10px 28px;
                font-size: 17px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e8f5f1;
            }
        """

        self.btn_tenant.setStyleSheet(btn_style)
        self.btn_tenant.setCursor(Qt.PointingHandCursor)
        self.btn_owner.setStyleSheet(btn_outline_style)
        self.btn_owner.setCursor(Qt.PointingHandCursor)
        self.btn_tenant.setFixedSize(240, 70)       
        self.btn_owner.setFixedSize(240, 70) 

        btn_row.addStretch()
        btn_row.addWidget(self.btn_tenant)
        btn_row.addWidget(self.btn_owner)
        btn_row.addStretch()

        left_layout.addLayout(btn_row)

        left_layout.addSpacing(20)
        create = QLabel("Already have an account?")
        createlink = QLabel("<a href='#'>Login</a>")
        create.setFont(self.font_lbl)
        create.setStyleSheet("color: #718096;")
        createlink.setTextFormat(Qt.RichText)
        createlink.setOpenExternalLinks(False)
        createlink.setText("<a style='color:#0A3B2E; font-weight: Bold; text-decoration:underline;' href='#'>Login</a>")
        createlink.setTextFormat(Qt.RichText)
        createlink.setOpenExternalLinks(False)
        createlink.linkActivated.connect(self.open_login_window)  
        logo_row = QHBoxLayout()
        logo_row.addStretch()
        logo_row.addWidget(create)
        logo_row.addWidget(createlink)
        logo_row.addStretch()

        left_layout.addLayout(logo_row)
        
        self.left.setMinimumWidth(520)
        self.left.setMinimumHeight(995)
        left_layout.addStretch()
        self.root.addWidget(self.left, 45)
    
    def open_student_signup(self):
        self.next_window = SignupStudentWindow()
        self.next_window.show()
        self.close()

    def open_admin_signup(self):
        self.next_window = SignupOwnerWindow()
        self.next_window.show()
        self.close()

    def open_login_window(self):
        self.next_window = LoginWindow()
        self.next_window.show()
        self.close()
        

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

    def connect_signals(self):
        self.btn_tenant.clicked.connect(self.open_student_signup)
        self.btn_owner.clicked.connect(self.open_admin_signup)


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
    w = SignupasWindow()
    w.showNormal()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
