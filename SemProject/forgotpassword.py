import sys
from auth import Auth

from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QRect, QRectF, pyqtSlot, QPropertyAnimation, QEasingCurve, QSize, QParallelAnimationGroup, pyqtProperty
)
from PyQt5.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor

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

class ForgotWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StaySmart")
        self.setMinimumSize(900, 560)
        self.auth = Auth()
        self.init_ui()
        self._first_show_done = False

    def back_to_login(self):
        from login import LoginWindow

        self.next_window = LoginWindow()
        self.next_window.show()
        self.close() 


    def init_ui(self):
        self.font_title = QFont("Poppins", 30, QFont.Bold)
        self.font_lbl = QFont("Poppins", 10)
        self.font_nav = QFont("Poppins", 10)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        self.left = QFrame()
        self.left.setObjectName("leftPanel")
        self.left.setStyleSheet("""
            QFrame#leftPanel {
                background: #FFFFFF;
            }
        """)
        left_layout = QVBoxLayout(self.left)
        left_layout.setContentsMargins(48, 28, 48, 28)
        left_layout.setSpacing(20)


        # -------------------- LOGO + TITLE --------------------
        logo_row = QHBoxLayout()
        logo_row.setSpacing(6)

        logo = QLabel()
        logo_pix = QPixmap("assets/logo.png")
        logo.setPixmap(logo_pix.scaled(65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        title_label = QLabel("STAYSMART")
        title_label.setFont(QFont("Poppins", 19, QFont.Bold))
        title_label.setStyleSheet("color: #0A3B2E;")
        title_label.setAlignment(Qt.AlignVCenter)

        logo_row.addWidget(logo)
        logo_row.addWidget(title_label)
        logo_row.addStretch()

        left_layout.addLayout(logo_row)


        # -------------------- FORGOT PASSWORD TITLE --------------------
        title = QLabel("Forgot Password")
        title.setFont(QFont("Poppins", 24, QFont.Bold))
        title.setStyleSheet("color: #123C24; padding-top: 40px;")
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)


        # -------------------- SUBTEXT --------------------
        create = QLabel("Enter your email to receive a password reset link.")
        create.setFont(QFont("Poppins", 11))
        create.setStyleSheet("color: #718096;")
        create.setAlignment(Qt.AlignCenter)
        create.setWordWrap(True)
        left_layout.addWidget(create)


        # -------------------- EMAIL LABEL --------------------
        email_lbl = QLabel("Email Address")
        email_lbl.setFont(QFont("Poppins", 12))
        email_lbl.setStyleSheet("color: #123C24; padding-top: 20px;")
        left_layout.addWidget(email_lbl)


        # -------------------- EMAIL INPUT --------------------
        email_container = QFrame()
        email_container.setStyleSheet("""
            QFrame {
                border: 1px solid #718096;
                border-radius: 12px;
                background: white;
            }
        """)
        email_container.setFixedHeight(55)

        email_layout = QHBoxLayout(email_container)
        email_layout.setContentsMargins(12, 0, 12, 0)

        self.username = QLineEdit()
        self.username.setFont(QFont("Poppins", 11))
        self.username.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
            }
        """)

        email_layout.addWidget(self.username)
        left_layout.addWidget(email_container)


        # -------------------- RESET BUTTON --------------------
        reset_btn = QPushButton("Confirm")
        reset_btn.setFixedHeight(60)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #11402D;
                color: white;
                border-radius: 12px;
                font-size: 18px;
                font-weight: 600;
            }
        """)
        left_layout.addSpacing(5)
        left_layout.addWidget(reset_btn)
        reset_btn.clicked.connect(self.handle_reset)


        # -------------------- BACK TO LOGIN --------------------
        back_login = QLabel("<a style='color:#0A3B2E; text-decoration:none;' href='#'>Back to Login</a>")
        back_login.setFont(QFont("Poppins", 11))
        back_login.setAlignment(Qt.AlignCenter)
        back_login.setOpenExternalLinks(False)
        left_layout.addWidget(back_login)
        back_login.linkActivated.connect(self.back_to_login)


        left_layout.addStretch()

        self.left.setMinimumWidth(520)
        self.left.setMinimumHeight(995)

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
        self.overlay_bg.setAttribute(Qt.WA_TransparentForMouseEvents)  # clicks go through
        self.overlay_bg.lower()

        # Top nav
        nav = QHBoxLayout()
        nav.setSpacing(24)
        nav.setContentsMargins(20, 20, 20, 0) 
        nav.addStretch()
        self.right.setMinimumWidth(500)
        nav.addStretch()
        
        right_layout.addLayout(nav)

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

        # stacking order
        self.left_img.stackUnder(self.center_img)
        self.right_img.stackUnder(self.center_img)
        self.center_img.raise_()

        # store references
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

    def handle_reset(self):
        from forgotpassword2 import ForgotPassWindow
        email = self.username.text().strip()

        if not email:
            QMessageBox.warning(self, "Missing Email", "Please enter your email.")
            return

        exists, acc_type = self.auth.email_exists(email)

        if not exists:
            QMessageBox.critical(self, "Not Found", "Email does not exist.")
            return

        from forgotpassword2 import ForgotPassWindow
        self.next = ForgotPassWindow(email)
        self.next.show()
        self.close()




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

        # group animations
        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_op_l)
        group.addAnimation(anim_geom_l)
        group.addAnimation(anim_op_r)
        group.start()

        # small scale pulse on carousel after entrance
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
    w = ForgotWindow()
    w.showNormal()
    sys.exit(app.exec_())


if __name__ == "__main__":
    LoginMain()
