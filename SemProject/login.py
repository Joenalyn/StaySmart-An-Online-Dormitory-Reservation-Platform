import sys
from auth import Auth
from student_dashboard import StudentDashboardWindow
from owner_dashboard import OwnerDashboardWindow

from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QRect, QRectF, pyqtSlot, QPropertyAnimation, QEasingCurve, QSize, QParallelAnimationGroup, pyqtProperty
)
from PyQt5.QtGui import QFont, QPixmap, QPainter, QPainterPath, QIcon

from PyQt5.QtWidgets import *

IMAGE_PATH = "/mnt/data/4323b332-6725-4ea1-bdd3-60073d2b1dec.png"


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

        scaled = self._pix.scaled(rect.size() * self._scale_factor, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        # center the pixmap
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
        self._opacity_eff.setOpacity(1)

        self._fade_anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(28)
        self._shadow.setOffset(0, 10)
        self._shadow.setColor(Qt.black)

        self.setProperty("shadow_effect", self._shadow)

        self.setGraphicsEffect(self._opacity_eff)

        self._base_size = QSize(300, 200)
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

        parent = self.parent()
        if parent is not None:
            if not hasattr(self, "_shadow_frame"):
                shadow_frame = QFrame(parent)
                shadow_frame.setObjectName(f"shadow_{id(self)}")
                shadow_frame.setStyleSheet("background: transparent;")
                shadow_frame.setGraphicsEffect(self._shadow)
                self._shadow_frame = shadow_frame
            self._shadow_frame.setGeometry(self.geometry())
            self._shadow_frame.lower()

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
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
        super().leaveEvent(event)


class AnimatedCarousel(QWidget):
    """Three-image carousel: crossfade + subtle scale animation.

    Kept for backward compatibility but we won't use it in the responsive layout below.
    """
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.image_paths = image_paths
        self.stack = QStackedWidget()
        self.stack.setContentsMargins(500, 0, 0, 0)
        self.stack.setSizePolicy(self.sizePolicy())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(500, 0, 0, 0)
        layout.addWidget(self.stack)

        self.labels = []
        for path in image_paths:
            pix = QPixmap(path)
            lbl = RoundedImageLabel(pix, radius=22)
            lbl.setAlignment(Qt.AlignCenter)
            eff = QGraphicsOpacityEffect(lbl)
            eff.setOpacity(0.0)
            lbl.setGraphicsEffect(eff)
            container = QFrame()
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.addStretch()
            v.addWidget(lbl, alignment=Qt.AlignCenter)
            v.addStretch()
            self.stack.addWidget(container)
            self.labels.append((lbl, eff))

        if self.labels:
            self.labels[0][1].setOpacity(1.0)
            self.stack.setCurrentIndex(0)

        self.current = 0
        self._setup_timer()

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(2600)
        self.timer.timeout.connect(self.next_image)
        self.timer.start()

    def next_image(self):
        if not self.labels:
            return
        old_idx = self.current
        new_idx = (self.current + 1) % len(self.labels)
        self.current = new_idx

        old_lbl, old_eff = self.labels[old_idx]
        new_lbl, new_eff = self.labels[new_idx]

        a1 = QPropertyAnimation(old_eff, b"opacity")
        a1.setDuration(700)
        a1.setStartValue(1.0)
        a1.setEndValue(0.0)
        a1.setEasingCurve(QEasingCurve.InOutQuad)

        a2 = QPropertyAnimation(new_eff, b"opacity")
        a2.setDuration(700)
        a2.setStartValue(0.0)
        a2.setEndValue(1.0)
        a2.setEasingCurve(QEasingCurve.InOutQuad)

        group = QParallelAnimationGroup(self)
        group.addAnimation(a1)
        group.addAnimation(a2)
        group.start()


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StaySmart")
        self.setMinimumSize(900, 560)
        self.auth = Auth()
        self.init_ui()
        self._first_show_done = False

    def handle_login(self):
        username = self.username.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Missing Fields", "Please enter both username and password.")
            return

        if hasattr(self.auth, "login"):
            success, user_id, role, msg = self.auth.login(username, password)

            if not success:
                QMessageBox.warning(self, "Login Failed", msg or "Invalid username or password.")
                return

            if role == "OWNER":
                QMessageBox.information(self, "Login Successful",
                                        f"Welcome back, Admin {username}!")
                self.dashboard = OwnerDashboardWindow(owner_id=user_id)
                self.dashboard.show()
                self.close()
                return

            if role == "TENANT":
                QMessageBox.information(self, "Login Successful",
                                        f"Welcome, User {username}!")
                self.student_dash = StudentDashboardWindow(tenant_id=user_id)
                self.student_dash.show()
                self.close()
                return


            QMessageBox.warning(self, "Login Failed", "Invalid role.")
            return

        is_admin, admin_msg = self.auth.admin_login(username, password)

        if is_admin:
            user = getattr(self.auth, "get_user", lambda u: None)(username)
            user_id = user["user_id"] if user and "user_id" in user else 1
            QMessageBox.information(self, "Login Successful", f"Welcome back, Admin {username}!")
            self.dashboard = OwnerDashboardWindow(owner_id=user_id)
            self.dashboard.show()
            self.close()
            return

        is_student, student_msg = self.auth.student_login(username, password)

        if is_student:
            user = getattr(self.auth, "get_user", lambda u: None)(username)
            user_id = user["user_id"] if user and "user_id" in user else 1 
            QMessageBox.information(self, "Login Successful", f"Welcome, {username}!")
            self.student_dash = StudentDashboardWindow(tenant_id=user_id)
            self.student_dash.show()
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")

    def open_signup_choice(self):
        from signupas import SignupasWindow 

        self.next_window = SignupasWindow()
        self.next_window.show()
        self.close()
    
    def forget_pass(self):
        from forgotpassword import ForgotWindow

        self.next_window = ForgotWindow()
        self.next_window.show()
        self.close()

    def handle_nav_click(self, link):
        print("Navigation clicked:", link)

    def init_ui(self):
        # global fonts
        self.font_title = QFont("Poppins", 30, QFont.Bold)
        self.font_lbl = QFont("Poppins", 10)
        self.font_nav = QFont("Poppins", 10)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

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
        logo = QLabel()
        logo_pix = QPixmap("assets/logo.png")
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

        title = QLabel("LOGIN")
        title.setFont(self.font_title)
        title.setStyleSheet("color: #123C24; padding-top: 75px;")
        left_layout.addWidget(title, alignment=Qt.AlignCenter)

        left_layout.addSpacing(20)
        create = QLabel("Don't have an aaccount?")
        createlink = QLabel("<a href='#'>Sign up</a>")
        create.setFont(self.font_lbl)
        create.setStyleSheet("color: #718096;")
        createlink.setTextFormat(Qt.RichText)
        createlink.setOpenExternalLinks(False)
        createlink.setText("<a style='color:#0A3B2E; font-weight: Bold; text-decoration:underline;' href='#'>Create now</a>")
        createlink.linkActivated.connect(self.open_signup_choice)
        createlink.setTextFormat(Qt.RichText)
        createlink.setOpenExternalLinks(False)

        logo_row = QHBoxLayout()
        logo_row.addStretch()
        logo_row.addWidget(create)
        logo_row.addWidget(createlink)
        logo_row.addStretch()

        left_layout.addLayout(logo_row)

        # Username
        left_layout.addSpacing(20)
        u_lbl = QLabel("Username")
        u_lbl.setFont(self.font_lbl)
        u_lbl.setStyleSheet("color: #95a0b1;")
        left_layout.addWidget(u_lbl, alignment=Qt.AlignLeft)

        # ---- USERNAME FIELD CONTAINER (same as password) ----
        username_container = QFrame()
        username_container.setStyleSheet("""
            QFrame {
                border: 1px solid #718096;
                border-radius: 15px;
                background: white;
            }
        """)
        username_container.setFixedHeight(70)

        username_layout = QHBoxLayout(username_container)
        username_layout.setContentsMargins(12, 0, 12, 0)
        username_layout.setSpacing(0)

        self.username = QLineEdit()
        self.username.setPlaceholderText("")
        self.username.setFont(QFont("Poppins", 10))
        self.username.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                padding-left: 10px;
            }
        """)

        username_layout.addWidget(self.username)
        left_layout.addWidget(username_container)

        # Password
        left_layout.addSpacing(20)
        p_lbl = QLabel("Password")
        p_lbl.setFont(self.font_lbl)
        p_lbl.setStyleSheet("color: #95a0b1;")
        left_layout.addWidget(p_lbl, alignment=Qt.AlignLeft)

        # ---- PASSWORD FIELD CONTAINER ----
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
        container_layout.setContentsMargins(12, 0, 12, 0)   # inner padding like screenshot
        container_layout.setSpacing(0)

        # ---- TEXT FIELD ----
        self.password = QLineEdit()
        self.password.setPlaceholderText("")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFont(QFont("Poppins", 10))
        self.password.setStyleSheet("border: none; padding-left: 5px;")
        container_layout.addWidget(self.password)

        # ---- EYE BUTTON ----
        eye_btn = QPushButton()
        eye_btn.setCursor(Qt.PointingHandCursor)
        eye_btn.setIcon(QIcon("assets/visibility-eye-svgrepo-com.svg"))
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

        # ---- ADD TO LAYOUT ----
        left_layout.addWidget(password_container)

        # Remember & forgot
        left_layout.addSpacing(20)
        bottom_row = QHBoxLayout()
        forgot = QLabel("<a style='color:#0A3B2E;text-decoration:underline' href='#'>Forgot Password</a>")
        forgot.setFont(self.font_lbl)
        forgot.setOpenExternalLinks(False)
        bottom_row.addWidget(forgot)
        forgot.linkActivated.connect(self.forget_pass)
        left_layout.addLayout(bottom_row)

        left_layout.addSpacing(20)
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)
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

        # Right panel
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

        # Top nav
        nav = QHBoxLayout()
        nav.setSpacing(24)
        nav.setContentsMargins(20, 20, 20, 0) 

        nav.addStretch()


        self.right.setMinimumWidth(500)
        nav.addStretch()
        
        right_layout.addLayout(nav)

        # --- RESPONSIVE, CENTERED CAROUSEL ---
        carousel_container = QWidget()
        carousel_layout = QHBoxLayout(carousel_container)
        carousel_layout.setSpacing(19)
        right_layout.addSpacing(200)
        carousel_layout.setContentsMargins(100, 8, 150, 8)
        carousel_layout.setAlignment(Qt.AlignCenter)

        self.left_img  = HoverRoundedImageLabel(QPixmap("assets/room2.png"), radius=20, parent=carousel_container)
        self.center_img = HoverRoundedImageLabel(QPixmap("assets/room1.png"), radius=20, parent=carousel_container)
        self.right_img = HoverRoundedImageLabel(QPixmap("assets/room3.png"), radius=20, parent=carousel_container)

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

        # Introducing text
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

        root.addWidget(self.left, 45)
        root.addWidget(self.right, 55) 

        self._first_show_done = False

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

        # keep refs
        btn._hover_anim_x = anim
        btn._hover_anim_y = anim2

        anim.start()
        anim2.start()
    @pyqtSlot()
    def toggle_password(self):
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
        else:
            self.password.setEchoMode(QLineEdit.Password)

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


def LoginMain():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = LoginWindow()
    w.showNormal()
    sys.exit(app.exec_())


if __name__ == "__main__":
    LoginMain()
