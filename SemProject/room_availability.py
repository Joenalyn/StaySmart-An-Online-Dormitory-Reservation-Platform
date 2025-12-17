import sys
from PyQt5.QtCore import Qt, QSize, QTimer, QEasingCurve
from PyQt5.QtGui import QFont, QPixmap, QCursor
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QDialog, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QMessageBox, 
    QLineEdit, QComboBox, QApplication
)
from PyQt5.QtGui import QFont, QColor, QPainter
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt
from database import DatabaseManager
from reserve_form import ReserveForm
from registrationform import TenantRegistrationForm

import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def resolve_image_path(rel_or_abs):
    if not rel_or_abs:
        return None
    if os.path.isabs(rel_or_abs):
        return rel_or_abs
    return os.path.join(BASE_DIR, rel_or_abs.replace("/", os.sep))


class DimOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: rgba(0, 0, 0, 150);")
        self.hide()

    def show_overlay(self):
        self.setGeometry(self.parent().rect())
        self.show()

    def hide_overlay(self):
        self.hide()

class ContactOverlay(QDialog):
    def __init__(self, parent, host):
        super().__init__(parent)
        self.setWindowTitle("Contact Host")
        self.setModal(True)
        self.setFixedSize(420, 430)
        self.setStyleSheet("background: white; border-radius: 14px;")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Title
        title = QLabel("Contact Host")
        title.setFont(QFont("Segoe UI Semibold", 16))
        title.setStyleSheet("color: #0f7a3a;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Avatar
        avatar = QLabel()
        avatar.setFixedSize(80, 80)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background: #e7f4ec;
            border-radius: 40px;
            color: #0f7a3a;
            font-size: 20px;
        """)
        name_str = host.get("host_name", "").strip()
        initial = name_str[0].upper() if name_str else "?"
        avatar.setText(initial)

        layout.addWidget(avatar, alignment=Qt.AlignCenter)

        name = QLabel(host.get("host_name", "Unknown Host"))
        name.setFont(QFont("Segoe UI Semibold", 13))
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("color: #222;")
        layout.addWidget(name)

        box = QFrame()
        box.setStyleSheet("""
            background: #f7f9fa;
            border-radius: 12px;
            border: 1px solid #d9d9d9;
        """)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(16, 12, 16, 12)
        box_layout.setSpacing(8)

        info_fields = [
            ("📞 Phone", host.get("phone", "Not available")),
            ("💬 Messenger", host.get("messenger", "Not available")),
            ("📘 Facebook", host.get("facebook", "Not available")),
            ("📧 Email", host.get("email", "Not available")),
        ]

        for label, value in info_fields:
            field = QLabel(f"{label}:  <b>{value}</b>")
            field.setFont(QFont("Segoe UI", 10))
            field.setStyleSheet("color: #333;")
            box_layout.addWidget(field)

        layout.addWidget(box)

        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        # Copy Button
        copy_btn = QPushButton("Copy Contact Info")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #0f7a3a;
                color: white;
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0d6c33;
            }
        """)
        copy_btn.clicked.connect(lambda: self.copy_info(host))
        btn_row.addWidget(copy_btn)

        # Close Button
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #e6e6e6;
                color: #222;
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #d0d0d0;
            }
        """)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def copy_info(self, host):
        text = (
            f"Host Name: {host.get('host_name','')}\n"
            f"Phone: {host.get('phone','')}\n"
            f"Messenger: {host.get('messenger','')}\n"
            f"Facebook: {host.get('facebook','')}\n"
            f"Email: {host.get('email','')}"
        )
        QApplication.clipboard().setText(text)


    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog { background: transparent; }
            QFrame { background: transparent; }
            QPushButton {
                padding:8px 12px;
                border-radius:8px;
                background: #0f7a3a;
                color:white;
            }
            QPushButton[role="close"] {
                background: #ccc;
                color: #111;
            }
        """)


class RoomDetailsDialog(QDialog):
    def __init__(self, parent, room_data, tenant_id=1):
        super().__init__(parent)
        self.setWindowTitle(room_data.get("name", "Room Details"))
        self.setMinimumWidth(780)
        self.setMinimumHeight(640)
        self.db = DatabaseManager()


        self.tenant_id = tenant_id
        self.room = room_data
        self.reserve_form = None  # keep ref

        self._fonts()
        self._build_ui()
        self._apply_styles()

    def _fonts(self):
        self.font_title = QFont("Segoe UI", 20, QFont.Bold)
        self.font_header = QFont("Segoe UI", 14, QFont.DemiBold)
        self.font_normal = QFont("Segoe UI", 11)
        self.font_small = QFont("Segoe UI", 10)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        scroll.setWidget(container)

        scroll.setStyleSheet("""
            /* ===== VERTICAL SCROLLBAR ===== */
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #0f7a3a;
                min-height: 40px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: #0c5d30;
            }

            /* REMOVE TOP/BOTTOM BUTTONS */
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }

            QScrollBar::up-arrow:vertical,
            QScrollBar::down-arrow:vertical {
                background: none;
                width: 0px;
                height: 0px;
            }

            /* REMOVE TRACK */
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }

            /* ===== HORIZONTAL SCROLLBAR ===== */
            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 0px;
            }

            QScrollBar::handle:horizontal {
                background: #0f7a3a;
                min-width: 40px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #0c5d30;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
                border: none;
            }

            QScrollBar::left-arrow:horizontal,
            QScrollBar::right-arrow:horizontal {
                background: none;
                width: 0px;
                height: 0px;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }
            """)


        main = QVBoxLayout(container)
        main.setSpacing(18)
        main.setContentsMargins(20, 20, 20, 20)

        # Back button
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.go_back)
        main.addWidget(back_btn, alignment=Qt.AlignLeft)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #e6e6e6;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton:hover { background: #d0d0d0; }
        """)

        # Banner image placeholder        
        banner = QLabel()
        banner.setFixedHeight(300)
        banner.setStyleSheet("background:#ddd; border-radius:12px;")
        banner.setAlignment(Qt.AlignCenter)

        rel_path = self.room.get("image_path")
        if not rel_path and self.room.get("dorm_id"):
            from database import DatabaseManager
            db = DatabaseManager()
            rel_path = db.get_dorm_main_image(self.room["dorm_id"])

        if rel_path:
            abs_path = resolve_image_path(rel_path)
            if abs_path and os.path.exists(abs_path):
                pix = QPixmap(abs_path)
                if not pix.isNull():
                    banner.setPixmap(
                        pix.scaled(banner.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                else:
                    banner.setText("Invalid image")
            else:
                banner.setText("Image not found")
        else:
            banner.setText("Room Image")

        main.addWidget(banner)

        title = QLabel(self.room.get("name", "Room Name"))
        title.setFont(self.font_title)
        main.addWidget(title)

        dist = self.room.get("distance") or "—m"
        sub = QLabel(f"{self.room.get('address','')}  •  {dist}")
        sub.setFont(self.font_normal)
        sub.setStyleSheet("color:#666;")
        main.addWidget(sub)

        main.addWidget(self._section_label("What this place offers"))

        dorm_id = self.room.get("dorm_id")
        amenities = []

        if dorm_id:
            room_id = self.room.get("room_id")
            amenities = self.db.get_room_amenities(room_id) if room_id else []

        if not amenities:
            lbl = QLabel("No amenities listed for this dorm.")
            lbl.setFont(self.font_normal)
            lbl.setStyleSheet("color:#666; padding:4px 0;")
            main.addWidget(lbl)
        else:
            for amenity in amenities:
                lbl = QLabel(f"• {amenity}")
                lbl.setFont(self.font_normal)
                lbl.setStyleSheet("padding:4px 0;")
                main.addWidget(lbl)

        main.addWidget(self._section_label("Where you'll be"))
        map_box = QLabel("Map Preview (replace with Google Maps embed later)")
        map_box.setFixedSize(700, 240)
        map_box.setAlignment(Qt.AlignCenter)
        map_box.setStyleSheet("background:#eee; border-radius:10px;")
        main.addWidget(map_box)

        main.addWidget(self._section_label("Hosted by"))

        host_card = QFrame()
        host_card.setObjectName("hostCard")
        h_layout = QHBoxLayout(host_card)
        h_layout.setContentsMargins(12, 12, 12, 12)
        h_layout.setSpacing(12)

        avatar = QLabel()
        avatar.setFixedSize(64, 64)
        avatar.setStyleSheet("background:#ccc; border-radius:32px;")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setText("Host")
        h_layout.addWidget(avatar)

        info_layout = QVBoxLayout()
        host_name = QLabel(self.room.get("host_name", "Host"))
        host_name.setFont(self.font_header)

        rating_val = self.room.get("rating")
        rating_txt = f"⭐ {rating_val}" if rating_val else "⭐ —"
        rating = QLabel(rating_txt)
        rating.setFont(self.font_small)
        rating.setStyleSheet("color:#666;")

        info_layout.addWidget(host_name)
        info_layout.addWidget(rating)
        h_layout.addLayout(info_layout)
        h_layout.addStretch()

        contact_btn = QPushButton("Contact Host")
        contact_btn.setObjectName("contactBtn")
        contact_btn.clicked.connect(self._open_contact)
        contact_btn.setFixedHeight(36)
        h_layout.addWidget(contact_btn)

        reserve_btn = QPushButton("Reserve")
        reserve_btn.setObjectName("reserveBtn")
        reserve_btn.setFixedHeight(36)
        reserve_btn.clicked.connect(self._open_reserve_form)
        h_layout.addWidget(reserve_btn)

        main.addWidget(host_card)
        layout.addWidget(scroll)

    def _open_reserve_form(self):
        dorm_id = self.room.get("dorm_id")
        room_id = self.room.get("room_id")
        host_id = self.room.get("host_id")

        if not dorm_id or not room_id:
            QMessageBox.warning(self, "Missing Data", "Dorm/Room IDs not found.")
            return
        
        if self.db.user_has_active_reservation(self.tenant_id):
            QMessageBox.warning(
                self,
                "Reservation Not Allowed",
                "You already have an active dorm reservation.\n\n"
                "You can only reserve one dorm at a time."
            )
            return

        self.reserve_form = ReserveForm(
            tenant_id=self.tenant_id,
            dorm_id=dorm_id,
            room_id=room_id,
            host_id=host_id
        )
        self.reserve_form.setWindowModality(Qt.ApplicationModal)
        self.reserve_form.submitted.connect(self._after_reserved)

        self.reserve_form.show()
        self.reserve_form.raise_()
        self.reserve_form.activateWindow()

    def _after_reserved(self, application_id):
        QMessageBox.information(
            self,
            "Reservation Sent",
            "Your reservation was sent to the owner and is now pending approval."
        )

        if self.reserve_form:
            self.reserve_form.close()

        from registrationform import TenantRegistrationForm
        self.registration_form = TenantRegistrationForm(tenant_id=self.tenant_id)
        self.registration_form.setWindowModality(Qt.ApplicationModal)
        self.registration_form.show()
 
    def go_back(self):
        self.close()

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(self.font_header)
        lbl.setStyleSheet("margin-top:8px; margin-bottom:6px;")
        return lbl

    def _open_contact(self):
        top_window = self.parent().window()

        if hasattr(top_window, "overlay"):
            top_window.overlay.show_overlay()

        host = {
            "host_name": self.room.get("host_name", ""),
            "phone": self.room.get("phone", "N/A"),
            "messenger": self.room.get("messenger", "N/A"),
            "facebook": self.room.get("facebook", "N/A"),
            "email": self.room.get("email", "N/A")
        }

        dlg = ContactOverlay(top_window, host)
        dlg.finished.connect(lambda _: top_window.overlay.hide_overlay())
        dlg.exec_()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog { background: #ffffff; }
            QFrame#hostCard {
                background:#fafafa;
                border-radius:12px;
                border:1px solid #eee;
            }
            QPushButton#contactBtn {
                background:#0f7a3a;
                color:white;
                border-radius:8px;
                padding:6px 12px;
            }
            QPushButton#contactBtn:hover { background:#0d6c33; }
            
            QPushButton#reserveBtn {
                background:#1e88e5;
                color:white;
                border-radius:8px;
                padding:6px 12px;
            }
            QPushButton#reserveBtn:hover { background:#1565c0; }

        """)

    def go_back(self):
        self.close()

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(self.font_header)
        lbl.setStyleSheet("margin-top:8px; margin-bottom:6px;")
        return lbl

    def _open_contact(self):
        top_window = self.parent().window()

        if hasattr(top_window, "overlay"):
            top_window.overlay.show_overlay()

        host = {
            "host_name": self.room.get("host_name", ""),
            "phone": self.room.get("phone", "N/A"),
            "messenger": self.room.get("messenger", "N/A"),
            "facebook": self.room.get("facebook", "N/A"),
            "email": self.room.get("email", "N/A")
        }

        dlg = ContactOverlay(top_window, host)

        dlg.finished.connect(lambda _: top_window.overlay.hide_overlay())

        dlg.exec_()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog { background: #ffffff; }
            QFrame#hostCard {
                background:#fafafa;
                border-radius:12px;
                border:1px solid #eee;
            }
            QPushButton#contactBtn {
                background:#0f7a3a;
                color:white;
                border-radius:8px;
                padding:6px 12px;
            }
            QPushButton#contactBtn:hover { background:#0d6c33; }
            
            QPushButton#reserveBtn {
                background:#1e88e5;
                color:white;
                border-radius:8px;
                padding:6px 12px;
            }
            QPushButton#reserveBtn:hover { background:#1565c0; }

        """)


# ==========================================================
# MAIN ROOMS AVAILABILITY WINDOW
# ==========================================================
class RoomsAvailability(QWidget):
    def __init__(self, parent=None, tenant_id=1):
        super().__init__()
        self.db = DatabaseManager()
        self.tenant_id = tenant_id
        self.setWindowTitle("Rooms Availability - StaySmart")
        self.setMinimumSize(1100, 720)
        self.parent_window = parent

        # sorting state must exist before UI build
        self.sort_states = {
            "nearest": False,
            "price_low": False,
            "price_high": False,
            "capacity": False
        }

        self._fonts()
        self._build_ui()
        self._apply_styles()

        self.overlay = DimOverlay(self)
        self.overlay.raise_()

    def _fonts(self):
        self.font_title = QFont("Segoe UI", 18, QFont.Bold)
        self.font_normal = QFont("Segoe UI", 10)

    def go_back(self):
        from student_dashboard import StudentDashboardWindow
        self.next_window = StudentDashboardWindow(user_id=self.tenant_id)
        self.next_window.show()
        self.close()


    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)
        

        header = QHBoxLayout()
        title = QLabel("Available Rooms Near You")
        title.setFont(self.font_title)

        #Back buttonn
        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedHeight(36)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #e6e6e6;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton:hover { background: #d0d0d0; }
        """)
        back_btn.clicked.connect(self.go_back)

        header.addWidget(back_btn)

        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        # Search + capacity filter
        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search dorm, room, or location...")
        self.search.setFixedHeight(36)

        self.search.textChanged.connect(self.update_room_list)

        self.capacity = QComboBox()
        self.capacity.addItems(["Any", "1", "2", "3", "4+"])
        self.capacity.setFixedHeight(36)
        self.capacity.currentIndexChanged.connect(self.update_room_list)  # update when changed

        controls.addWidget(self.search)
        controls.addWidget(self.capacity)
        root.addLayout(controls)

        # sort pills row
        self.sort_row = QHBoxLayout()
        self.sort_buttons = {}
        sorts = [
            ("nearest", "Nearest"),
            ("price_low", "Price ↑"),
            ("price_high", "Price ↓"),
            ("capacity", "Capacity")
        ]
        for key, label in sorts:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("pill")
            btn.clicked.connect(lambda _, k=key: self.toggle_sort(k))
            self.sort_row.addWidget(btn)
            self.sort_buttons[key] = btn
        self.sort_row.addStretch()
        root.addLayout(self.sort_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        self.rooms_layout = QVBoxLayout(container)
        self.rooms_layout.setSpacing(14)

        scroll.setStyleSheet("""
            /* ===== ROOMS LIST SCROLLBAR ONLY ===== */
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #0f7a3a;
                min-height: 40px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: #0c5d30;
            }

            /* remove arrows */
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }

            QScrollBar::up-arrow:vertical,
            QScrollBar::down-arrow:vertical {
                background: none;
                width: 0px;
                height: 0px;
            }

            /* remove track */
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
            """)

        root.addWidget(scroll)
        self.update_room_list()

    def update_room_list(self):
        while self.rooms_layout.count():
            w = self.rooms_layout.takeAt(0)
            if w.widget():
                w.widget().deleteLater()

        search_text = self.search.text().strip()
        cap_text = self.capacity.currentText()

        fetched_rooms = self.db.get_all_rooms(search_text, cap_text)

        if self.sort_states.get("nearest"):
            fetched_rooms.sort(key=lambda r: r.get("distance", 0))
        if self.sort_states.get("price_low"):
            fetched_rooms.sort(key=lambda r: r.get("price", 0))

        for room in fetched_rooms:
            card = self._create_card(room)
            self.rooms_layout.addWidget(card)
        
        if not fetched_rooms:
            self.rooms_layout.addWidget(QLabel("No rooms found matching your criteria."))
            
        self.rooms_layout.addStretch()

    def toggle_sort(self, key):
        self.sort_states[key] = not self.sort_states.get(key, False)
        btn = self.sort_buttons.get(key)
        if btn:
            if self.sort_states[key]:
                btn.setStyleSheet("background:#0f7a3a; color:white; border-radius:18px; padding:6px 14px;")
                btn.setChecked(True)
            else:
                btn.setStyleSheet("")
                btn.setChecked(False)
        self.update_room_list()

    def _create_card(self, room):
        card = QFrame()
        card.setObjectName("roomCard")
        card.setFixedHeight(180)
        card.setStyleSheet("background:white; border-radius:12px; border:1px solid #eee;")

        h = QHBoxLayout(card)
        h.setContentsMargins(12, 12, 12, 12)
        h.setSpacing(12)

        img = QLabel()
        img.setFixedSize(200, 150)
        img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet("background:#e8e8e8; border-radius:10px;")

        dorm_id = room.get("dorm_id")
        rel_path = self.db.get_dorm_main_image(dorm_id) if dorm_id else None

        if rel_path:
            abs_path = resolve_image_path(rel_path)
            if abs_path and os.path.exists(abs_path):
                pix = QPixmap(abs_path)
                if not pix.isNull():
                    img.setPixmap(
                        pix.scaled(img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                else:
                    img.setText("Invalid")
            else:
                img.setText("Not found")
        else:
            img.setText("No Image")

        info = QVBoxLayout()

        title = QLabel(room.get("name", "Room"))
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))

        addr = QLabel(room.get("address", ""))
        addr.setStyleSheet("color:#555;")

        dist = QLabel(f"{room.get('distance', 0)}m away")
        dist.setStyleSheet("color:#0f7a3a; font-weight:bold;")

        bottom = QHBoxLayout()
        price = QLabel(f"₱{room.get('price',0):,} / month")
        price.setFont(QFont("Segoe UI", 11, QFont.Bold))

        btn = QPushButton("View Details")
        btn.setObjectName("accentBtn")
        btn.setFixedHeight(32)
        btn.clicked.connect(lambda _, r=room: self._open_details(r))

        btn.setStyleSheet("""
            QPushButton {
                background: #0f7a3a;
                color: white;
                border-radius: 14px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0c5d30;
            }
        """)


        bottom.addWidget(price)
        bottom.addStretch()
        bottom.addWidget(btn)

        info.addWidget(title)
        info.addWidget(addr)
        info.addWidget(dist)
        info.addStretch()
        info.addLayout(bottom)

        info_widget = QWidget()
        info_widget.setLayout(info)
        h.addWidget(info_widget)

        h.setStretch(0, 1)  
        h.setStretch(1, 5)   

        return card


    def _open_details(self, room):
        from copy import deepcopy
        room_copy = deepcopy(room)
        dorm_id = room_copy.get("dorm_id")
        if dorm_id:
            rel_path = self.db.get_dorm_main_image(dorm_id)
            if rel_path:
                room_copy["image_path"] = rel_path

        dlg = RoomDetailsDialog(self, room_copy, tenant_id=self.tenant_id)
        dlg.exec_()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background:#f5f7f8; color:#222; font-family: "Segoe UI"; }

            QLineEdit, QComboBox {
                background:white;
                border:1px solid #ccc;
                border-radius:8px;
                padding:8px;
                min-height: 32px;
            }

            QPushButton#pill {
                border:1px solid #ccc;
                border-radius:18px;
                padding:6px 14px;
                background:white;
                color:#333;
            }
            
            QPushButton#accentBtn {
                background:#0f7a3a;
                color:white;
                border-radius:8px;
                padding:6px 12px;
            }
            QPushButton#accentBtn:hover { background:#0d6c33; }

            QPushButton#reserveBtn {
                background:#1e88e5;
                color:white;
                border-radius:8px;
                padding:6px 12px;
            }
            QPushButton#reserveBtn:hover { background:#1565c0; }

            #contactCard { background:white; border-radius:12px; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = RoomsAvailability()
    win.show()
    sys.exit(app.exec_())
