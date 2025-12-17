import sys
import os
import importlib
import database
print("USING DATABASE FILE:", database.__file__)
from my_reservations import MyReservationsWindow
from payments import PaymentsWindow
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QListWidget, QListWidgetItem, QScrollArea, QGridLayout,
    QSizePolicy, QSpacerItem, QLineEdit, QComboBox, QDialog, QWidgetItem
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QCursor

from database import DatabaseManager

RoomsAvailability = None
try:
    ra = importlib.import_module("room_availability")
    RoomsAvailability = getattr(ra, "RoomsAvailability", None)
except Exception:
    RoomsAvailability = None

# ---------------------------
# Theme & shared styles
# ---------------------------
SharedStyle = """
QWidget { background:#f5f7f8; color:#222; font-family: "Segoe UI"; }
QFrame.card { background: #ffffff; border-radius: 12px; border: 1px solid rgba(0,0,0,0.06); }
QFrame.cardSmall { background:#ffffff; border-radius:10px; border:1px solid rgba(0,0,0,0.05); }
QLabel.h1 { font-size:20px; font-weight:700; color:#0f3f2b; }
QLabel.h2 { font-size:13px; font-weight:600; color:#222; }
QPushButton.btnPrimary {
    background: #0f7a3a; color: white; border-radius:8px; padding:8px 12px;
}
QPushButton.btnPrimary:hover { background:#0d6c33; }
QPushButton.pill {
    background: transparent; border: 1px solid #ddd; padding:6px 12px; border-radius:16px;
}
QListWidget { background: transparent; border: none; }
QScrollArea { background: transparent; border: none; }
"""

class StudentTotalDormsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Total Dorms - Student View")
        self.setMinimumSize(880, 600)
        self._fonts()
        self._build_ui()
        self.setStyleSheet(SharedStyle)
        

    def _fonts(self):
        self.font_title = QFont("Segoe UI", 16, QFont.Bold)
        self.font_section = QFont("Segoe UI", 11, QFont.DemiBold)

    def _build_ui(self):
        root = QVBoxLayout(self)
        header = QLabel("Occupancy — Student View")
        header.setFont(self.font_title)
        root.addWidget(header)

        info_card = QFrame()
        info_card.setObjectName("card")
        info_card.setProperty("class", "card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12,12,12,12)
        info_layout.addWidget(QLabel("This is a placeholder for the Total Dorms chart."))
        root.addWidget(info_card, stretch=1)

class StudentReservationsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Reservations")
        self.setMinimumSize(700, 480)
        self._build_ui()
        self.setStyleSheet(SharedStyle)

    def _build_ui(self):
        root = QVBoxLayout(self)
        header = QLabel("My Reservations")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        root.addWidget(header)
        listw = QListWidget()
        for t in ["Reservation #123 - Pending", "Reservation #112 - Approved"]:
            QListWidgetItem(t, listw)
        root.addWidget(listw)

class StudentPaymentsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Payments")
        self.setMinimumSize(700, 420)
        self._build_ui()
        self.setStyleSheet(SharedStyle)

    def _build_ui(self):
        root = QVBoxLayout(self)
        header = QLabel("Payments")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        root.addWidget(header)
        p_list = QListWidget()
        for p in ["2024-11-01 — ₱4,500 — Paid", "2024-12-01 — ₱4,500 — Due"]:
            QListWidgetItem(p, p_list)
        root.addWidget(p_list)

class StudentDashboardWindow(QWidget):
    def __init__(self, tenant_id=None, user_id=None):
        super().__init__()
        self.setWindowTitle("StaySmart — Student Dashboard")
        self.setMinimumSize(1100, 720)

        self.db = DatabaseManager()

        if user_id is not None:
            self.user_id = user_id
        elif tenant_id is not None:
            self.user_id = tenant_id
        else:
            self.user_id = 1 

        self._fonts()
        self._build_ui()
        self.setStyleSheet(SharedStyle)
        self.load_live_data()


    def load_live_data(self):
        print("Fetching live data from database...")

        stats = self.db.get_dashboard_stats(self.user_id)

        lbl_dorms = self.findChild(QLabel, "lbl_total_dorms")
        if lbl_dorms:
            lbl_dorms.setText(str(stats.get("total_dorms", "0 rooms")))

        lbl_res = self.findChild(QLabel, "lbl_active_res")
        if lbl_res:
            count = stats.get("active_res", 0)
            lbl_res.setText(f"{count} active")

        lbl_pay = self.findChild(QLabel, "lbl_next_payment")
        if lbl_pay:
            lbl_pay.setText(str(stats.get("next_payment", "No due")))

        self.db.get_recommended_rooms()

    def _fonts(self):
        self.font_title = QFont("Segoe UI", 20, QFont.Bold)
        self.font_section = QFont("Segoe UI", 12, QFont.DemiBold)
        self.font_normal = QFont("Segoe UI", 10)
    
    def logout(self):
        from login import LoginWindow 
        self.login = LoginWindow()
        self.login.show()
        self.close()


    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        hdr = QHBoxLayout()
        title = QLabel("Student Dashboard")
        title.setFont(self.font_title)
        hdr.addWidget(title)
        hdr.addStretch()

        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(QCursor(Qt.PointingHandCursor))
        logout_btn.setStyleSheet(
            "background:#ff6b6b; color:white; padding:6px 14px; border-radius:6px;"
        )
        logout_btn.clicked.connect(self.logout)
        hdr.addWidget(logout_btn)


        root.addLayout(hdr)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        top_row.addWidget(self._summary_card(
            "Total Dorms", 
            "0 rooms", 
            label_id="lbl_total_dorms", 
            open_action=self.open_total_dorms
        ))

        top_row.addWidget(self._summary_card(
            "My Reservations", 
            "0 active", 
            label_id="lbl_active_res", 
            open_action=self.open_reservations
        ))

        top_row.addWidget(self._summary_card(
            "Payments", 
            "No due", 
            label_id="lbl_next_payment", 
            open_action=self.open_payments
        ))


        root.addLayout(top_row)

        search_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search dorms, locations, amenities...")
        self.search_input.setFixedHeight(36)
        search_row.addWidget(self.search_input)

        self.filter_capacity = QComboBox()
        self.filter_capacity.addItem("Any capacity")
        self.filter_capacity.addItems(["1", "2", "3", "4+"])
        self.filter_capacity.setFixedHeight(36)
        search_row.addWidget(self.filter_capacity)

        btn_search = QPushButton("Search")
        btn_search.setCursor(QCursor(Qt.PointingHandCursor))
        btn_search.setObjectName("searchBtn")
        btn_search.clicked.connect(self._on_search)
        search_row.addWidget(btn_search)

        root.addLayout(search_row)

        middle = QHBoxLayout()
        middle.setSpacing(12)

        left = QFrame()
        left.setObjectName("card")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)

        hdr_lbl = QLabel("Recommended For You")
        hdr_lbl.setFont(self.font_section)
        left_layout.addWidget(hdr_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        sc_cont = QWidget()
        sc_layout = QHBoxLayout(sc_cont)
        sc_layout.setSpacing(12)

        recommended = self.db.get_recommended_rooms()

        if not recommended:
            sc_layout.addWidget(QLabel("No recommended rooms"))


        for r in recommended:
            sc_layout.addWidget(self._mini_room_card(r))

        sc_layout.addStretch()
        scroll.setWidget(sc_cont)
        left_layout.addWidget(scroll)

        middle.addWidget(left, 100)

        root.addLayout(middle)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        notif_card = QFrame()
        notif_card.setObjectName("card")
        notif_layout = QVBoxLayout(notif_card)
        notif_layout.setContentsMargins(14, 14, 14, 14)

        n_title = QLabel("Notifications")
        n_title.setFont(self.font_section)
        notif_layout.addWidget(n_title)

        nlist = QListWidget()
        nlist.setFixedHeight(150)

        db_notifications = []

        if not db_notifications:
            QListWidgetItem("No notifications", nlist)
        else:
            for note in db_notifications:
                QListWidgetItem(note, nlist)

        notif_layout.addWidget(nlist)
        bottom.addWidget(notif_card, 3)


       # --- Recently Viewed ---
        recent = QFrame()
        recent.setObjectName("card")
        re_layout = QVBoxLayout(recent)
        re_layout.setContentsMargins(14,14,14,14)

        re_title = QLabel("Recently Viewed")
        re_title.setFont(self.font_section)
        re_layout.addWidget(re_title)

        rlist = QListWidget()
        rlist.setFixedHeight(150)
        
        recent_data = self.db.get_recently_viewed(self.user_id)
        
        if not recent_data:
            QListWidgetItem("No recently viewed dorms", rlist)
        else:
            for view in recent_data:
                label_text = f"{view['property_name']} - {view['room_name']}"
                QListWidgetItem(label_text, rlist)

        re_layout.addWidget(rlist)
        bottom.addWidget(recent, 2)

        active = QFrame()
        active.setObjectName("card")
        active_layout = QVBoxLayout(active)
        active_layout.setContentsMargins(14,14,14,14)

        a_title2 = QLabel("Active Reservations")
        a_title2.setFont(self.font_section)
        active_layout.addWidget(a_title2)

        alist = QListWidget()
        alist.setFixedHeight(150)

        reservations_bottom = self.db.get_user_reservations(self.user_id)

        if not reservations_bottom:
            QListWidgetItem("No active reservations", alist)
        else:
            for r in reservations_bottom:
                text = f"{r['property_name']} - {r['room_name']} — {r['status']}"
                QListWidgetItem(text, alist)

        active_layout.addWidget(alist)
        bottom.addWidget(active, 2)

        root.addLayout(bottom)
        root.addStretch()

        self._apply_extra_styles()

    def _summary_card(self, title, subtitle, label_id=None, open_action=None):
        f = QFrame()
        f.setObjectName("card")  
        f.setFixedHeight(120)
        layout = QVBoxLayout(f)
        
        t = QLabel(title)
        t.setFont(self.font_normal)
        layout.addWidget(t)
        layout.addStretch()
        
        sub = QLabel(subtitle)
        sub.setFont(QFont("Segoe UI", 16, QFont.Bold)) 
        
        if label_id:
            sub.setObjectName(label_id)

        layout.addWidget(sub)

        if open_action:
            btn = QPushButton("Open")
            btn.setObjectName("openBtn")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(open_action)
            layout.addWidget(btn, alignment=Qt.AlignRight)
            
        return f

    def _mini_room_card(self, room):
        c = QFrame()
        c.setFixedSize(240, 150)
        c.setObjectName("card")
        l = QVBoxLayout(c)
        l.setContentsMargins(10,10,10,10)

        name_text = room.get("name") or room.get("property_name") or "Room"
        name = QLabel(name_text)
        name.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        l.addWidget(name)

        price = room.get("price")
        if price is None:
            price = room.get("price_monthly") 
        price_text = f"₱{int(price):,}" if price is not None else "₱—"

        capacity = room.get("capacity")
        cap_text = f"{capacity}p" if capacity is not None else "—p"

        distance = room.get("distance")
        dist_text = f"{distance}m" if distance is not None else "—m"

        details = QLabel(f"{price_text} • {cap_text} • {dist_text}")
        details.setStyleSheet("color:#666;")
        l.addWidget(details)

        l.addStretch()

        btn_row = QHBoxLayout()
        view = QPushButton("View")
        view.setCursor(QCursor(Qt.PointingHandCursor))
        view.clicked.connect(self.open_room_availability)
        view.setStyleSheet(
            "background:#0f7a3a; color:white; border-radius:8px; padding:6px 10px;"
        )
        btn_row.addStretch()
        btn_row.addWidget(view)
        l.addLayout(btn_row)

        return c


    def open_room_availability(self):
        if RoomsAvailability:
            try:
                self.ra_win = RoomsAvailability(tenant_id=self.user_id)
                self.ra_win.show()
                self.ra_win.raise_()
                self.ra_win.activateWindow()
                return
            except Exception:
                pass
        dlg = QDialog(self)
        dlg.setWindowTitle("Room Availability (placeholder)")
        dlg.setMinimumSize(800, 520)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("room_availability.py not found or failed to open."))
        dlg.exec_()

    def open_total_dorms(self):
        from room_availability import RoomsAvailability
        self.child = RoomsAvailability() 
        self.child.show()
        self.close()

    def open_reservations(self):
        from my_reservations import MyReservationsWindow
        self.child = MyReservationsWindow(user_id=self.user_id)  
        self.child.show()
        self.close()

    def open_payments(self):
        from payments import PaymentsWindow
        self.child = PaymentsWindow(user_id=self.user_id)
        self.child.show()
        self.close()


    def _on_search(self):
        text = self.search_input.text().strip()
        capacity = self.filter_capacity.currentText()

        from room_availability import RoomsAvailability
        
        self.ra_win = RoomsAvailability(tenant_id=self.user_id)
        self.ra_win.search.setText(text)
        
        if "Any" not in capacity:
             index = self.ra_win.capacity.findText(capacity)
             if index >= 0:
                 self.ra_win.capacity.setCurrentIndex(index)

        self.ra_win.update_room_list()
        self.ra_win.show()

    def _apply_extra_styles(self):
        self.setStyleSheet(self.styleSheet() + """
            QFrame#card { background: white; border-radius:12px; border:1px solid rgba(0,0,0,0.06); }
            QFrame.cardSmall { background: white; border-radius:10px; border:1px solid rgba(0,0,0,0.05); }
            QLabel { color: #222; }
            QPushButton#openBtn { background:#0f7a3a; color:white; border-radius:8px; padding:6px 10px; }
            QPushButton#searchBtn { background:#0f7a3a; color:white; border-radius:8px; padding:6px 12px; }
            /* Info cards */
            QFrame#infoCard {
                background: white;
                border-radius: 14px;
                border: 1px solid #cfe6d9;
            }

            QLabel#cardTitle {
                font-size: 15px;
                font-weight: 600;
                color: #0f7a3a;
                margin-bottom: 5px;
            }

            /* List styling */
            QListWidget {
                background: #fbfdfc;
                border-radius: 10px;
                border: 1px solid #d3e6dc;
                padding: 6px;
            }

            QListWidget::item {
                padding: 8px;
                font-size: 13px;
            }

        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = StudentDashboardWindow()
    win.show()
    sys.exit(app.exec_())
