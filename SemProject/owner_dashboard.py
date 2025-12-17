import sys
import os
import importlib.util
from datetime import datetime
from pending_requests import PendingRequestsWindow
from paymentrequest import PaymentRequestsWindow


# --- IMPORT DATABASE ---
from database import DatabaseManager 

# --- IMPORT SUB-WINDOWS ---
from TotalDorms import TotalDormsWindow
from current_occu import CurrentOccupantsWindow
from pending_requests import PendingRequestsWindow
from monthly_earnings import MonthlyEarningsWindow

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QListWidget, QGridLayout
)

from PyQt5.QtGui import QFont, QCursor, QFont, QCursor, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

windows_registry = []


def load_total_dorms():
    file_path = "TotalDorms.py"
    if not os.path.exists(file_path):
        return None
    spec = importlib.util.spec_from_file_location("total_dorms", file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "launch"):
        return mod.launch
    for name in ["TotalDormsWindow", "TotalDorms", "Dashboard", "MainWindow"]:
        if hasattr(mod, name):
            ClassRef = getattr(mod, name)
            return lambda: ClassRef().show()
    return None

TotalDormsLauncher = load_total_dorms()

class ClickableCard(QFrame):
    clicked = pyqtSignal()
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class OccupancyChart(QWidget):
    def __init__(self, owner_id, db, parent=None):
        super().__init__(parent)
        self.owner_id = owner_id
        self.db = db

        self.view_mode = "yearly"
        self.auto_timer = QTimer(self)
        self.auto_timer.setInterval(7000)
        self.auto_timer.timeout.connect(self._auto_advance)

        self._build_ui()
        self.draw_chart()


    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        

        ctrl = QHBoxLayout()
        self.btn_week = QPushButton("Weekly")
        self.btn_month = QPushButton("Monthly")
        self.btn_year = QPushButton("Yearly")
        for b, mode in ((self.btn_week, "weekly"), (self.btn_month, "monthly"), (self.btn_year, "yearly")):
            b.setCheckable(True)
            b.clicked.connect(lambda checked, m=mode: self.set_mode(m))
            ctrl.addWidget(b)
        ctrl.addStretch()

        self.btn_play = QPushButton("Play")
        self.btn_play.setCheckable(True)
        self.btn_play.clicked.connect(self._toggle_play)
        ctrl.addWidget(self.btn_play)

        layout.addLayout(ctrl)

        self.fig = Figure(figsize=(8, 3.2), tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect("button_press_event", self._on_chart_click)
        layout.addWidget(self.canvas)

        self._update_mode_buttons()

    def _update_mode_buttons(self):
        self.btn_week.setChecked(self.view_mode == "weekly")
        self.btn_month.setChecked(self.view_mode == "monthly")
        self.btn_year.setChecked(self.view_mode == "yearly")

    def set_mode(self, mode):
        if mode not in ("weekly", "monthly", "yearly"): return
        self.view_mode = mode
        self._update_mode_buttons()
        self.draw_chart()

    def draw_chart(self):
        self.fig.clf()
        ax = self.fig.add_subplot(111)

        if self.view_mode == "weekly":
            labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            values = self.db.get_owner_occupancy_weekly(self.owner_id)
            bars = ax.bar(range(len(values)), values)
            for rect, val in zip(bars, values):
                ax.text(rect.get_x() + rect.get_width()/2.0,
                        rect.get_height(), f"{val}",
                        ha='center', va='bottom', fontsize=9)

        elif self.view_mode == "monthly":
            labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            year = datetime.now().year
            values = self.db.get_owner_occupancy_monthly(self.owner_id, year)
            ax.plot(range(len(values)), values, linewidth=3, marker='o')

        else:  # yearly
            labels, values = self.db.get_owner_occupancy_yearly(self.owner_id, years_back=4)
            if not labels:
                labels = [str(datetime.now().year)]
                values = [0]
            bars = ax.bar(range(len(values)), values)
            for rect, val in zip(bars, values):
                ax.text(rect.get_x() + rect.get_width()/2.0,
                        rect.get_height(), f"{val}",
                        ha='center', va='bottom', fontsize=9)

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_ylabel("Renters Count")
        self.canvas.draw_idle()


    def _on_chart_click(self, event):
        if TotalDormsLauncher:
            try:
                parent_window = self.window()
                obj = TotalDormsLauncher
                if isinstance(obj, type):
                    win = obj()
                    windows_registry.append(win)
                    win.show()
                else:
                    obj()
                if parent_window:
                    parent_window.close()
            except Exception:
                pass

    def _toggle_play(self, checked):
        if checked:
            self.auto_timer.start()
            self.btn_play.setText("Pause")
        else:
            self.auto_timer.stop()
            self.btn_play.setText("Play")

    def _auto_advance(self):
        order = ["weekly", "monthly", "yearly"]
        idx = (order.index(self.view_mode) + 1) % len(order)
        self.set_mode(order[idx])

class OwnerDashboardWindow(QWidget):
    def __init__(self, owner_id=None):
        super().__init__()
        self.setWindowTitle("StaySmart — Owner Dashboard")
        self.setMinimumSize(1180, 760)

        self.db = DatabaseManager()
        self.host_id = owner_id if owner_id is not None else 1

        self._fonts()
        self._build_ui()
        self._start_clock()   
        self._apply_styles()
        self.load_dashboard_data()

    def logout(self):
        from login import LoginWindow 
        self.win_logout = LoginWindow()
        self.win_logout.show()
        self.close()


    def _fonts(self):
        self.font_title = QFont("Segoe UI", 22, QFont.Bold)
        self.font_section = QFont("Segoe UI", 13, QFont.DemiBold)
        self.font_normal = QFont("Segoe UI", 10)

    def load_dashboard_data(self):
        """Fetches real data from database and updates UI."""
        stats = self.db.get_owner_stats(self.host_id)

        self.lbl_total_val.setText(str(stats["total_dorms"]))
        self.lbl_occ_val.setText(str(stats["current_occupants"]))
        self.lbl_pending_val.setText(str(stats["pending_requests"]))
        self.lbl_earn_val.setText(f"₱{stats['monthly_earnings']:,.0f}")

        self.lbl_active_dorms.setText(f"Active Dorms: {stats['active_dorms']}")
        self.lbl_maint_dorms.setText(f"Dorms Under Maintenance: {stats['maintenance_dorms']}")
        self.lbl_occupancy_rate.setText(f"Occupancy: {stats['occupancy_rate']}%")
        recent_res = self.db.get_recent_reservations(self.host_id)
        self.lst_recent.clear()
        
        if not recent_res:
            self.lst_recent.addItem("No recent reservations.")
        else:
            for res in recent_res:
                date_str = res['created_at'].strftime("%b %d") if res['created_at'] else ""
                text = f"[{date_str}] {res['full_name']} - {res['room_name']} ({res['status']})"
                self.lst_recent.addItem(text)

    def open_payment_requests(self):
        self.win_payreq = PaymentRequestsWindow(
            owner_id=self.host_id,
            parent_window=self    
        )
        windows_registry.append(self.win_payreq)

        self.win_payreq.show()
        self.hide()               

    def make_summary_row(self, icon_path, text, accent="#0f7a3a"):
        row = QFrame()
        row.setStyleSheet("""
        QFrame {
            background: #fbfdfc;
            border-radius: 6px;
        }
    """)


        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        icon = QLabel()
        icon.setPixmap(QPixmap(icon_path).scaled(
            20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

        label = QLabel(text)
        label.setFont(QFont("Segoe UI", 10, QFont.DemiBold))

        layout.addWidget(icon)
        layout.addWidget(label)
        layout.addStretch()

        return row, label


    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Owner Dashboard")
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

        self.card_total, self.lbl_total_val = self._make_stat_card("Total Dorms", "...")
        self.card_total.mousePressEvent = (lambda e: self.open_total_dorms())

        self.card_occ, self.lbl_occ_val = self._make_stat_card("Current Occupants", "...")
        self.card_occ.mousePressEvent = lambda e: self.open_current_occupants()

        self.card_pending, self.lbl_pending_val = self._make_stat_card("Pending Requests", "...")
        self.card_pending.mousePressEvent = lambda e: self.open_pending_requests()

        self.card_earn, self.lbl_earn_val = self._make_stat_card("Monthly Earnings", "...")
        self.card_earn.mousePressEvent = lambda e: self.open_collections()

        top_row.addWidget(self.card_total)
        top_row.addWidget(self.card_occ)
        top_row.addWidget(self.card_pending)
        top_row.addWidget(self.card_earn)
        root.addLayout(top_row)

        occ_frame = QFrame()
        occ_frame.setObjectName("cardLarge")
        occ_layout = QVBoxLayout(occ_frame)
        occ_layout.setContentsMargins(12, 12, 12, 12)
        occ_layout.setSpacing(10)

        occ_title_row = QHBoxLayout()
        lbl = QLabel("Occupancy Statistics")
        lbl.setFont(self.font_section)
        occ_title_row.addWidget(lbl)
        occ_title_row.addStretch()

        self.chart = OccupancyChart(owner_id=self.host_id, db=self.db, parent=self)

        occ_layout.addWidget(self.chart)
        root.addWidget(occ_frame)

        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(12)

        act_card = QFrame()
        act_card.setObjectName("card")
        act_layout = QVBoxLayout(act_card)
        act_layout.setContentsMargins(10, 10, 10, 10)
        btn_payments = QPushButton("Payment Requests")
        btn_payments.setFixedHeight(60)
        btn_payments.setFont(QFont("Poppins", 50, QFont.Bold))
        btn_payments.setCursor(QCursor(Qt.PointingHandCursor))
        btn_payments.clicked.connect(self.open_payment_requests)

        btn_payments.setStyleSheet("""
            QPushButton {
                background: #0f7a3a;
                color: white;
                border-radius: 16px;
                padding: 12px;        /* more breathing room */
            }
            QPushButton:hover {
                background: #0c5d30;
            }
        """)


        act_layout.addWidget(btn_payments)

        self.lbl_clock = QLabel()
        self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_clock.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.lbl_clock.setStyleSheet("""
            QLabel {
                background: #f6fbf7;
                border: 1px solid #cce8d4;
                border-radius: 10px;
                padding: 10px;
                color: #0c5d30;
            }
        """)

        act_layout.addWidget(self.lbl_clock)

        # Recent Reservations
        recent_card = QFrame()
        recent_card.setObjectName("card")
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(12, 12, 12, 12)
        lbl_recent = QLabel("Recent Reservations")
        lbl_recent.setFont(self.font_section)
        recent_layout.addWidget(lbl_recent)
        self.lst_recent = QListWidget()
        recent_layout.addWidget(self.lst_recent)

        # Summary
        sum_card = QFrame()
        sum_card.setObjectName("cardSmall")
        sum_layout = QVBoxLayout(sum_card)
        sum_layout.setContentsMargins(12, 12, 12, 12)
        lbl_sum = QLabel("Summary")
        lbl_sum.setFont(self.font_section)
        sum_layout.addWidget(lbl_sum)

        self.sum_active, self.lbl_active_dorms = self.make_summary_row(
            os.path.join(BASE_DIR, "assets/dorm.png"),
            "Active Dorms: ...",
            "#0f7a3a"
        )

        self.sum_maint, self.lbl_maint_dorms = self.make_summary_row(
            os.path.join(BASE_DIR, "assets/maintenance.png"),
            "Dorms Under Maintenance: ...",
            "#c62828"
        )

        self.sum_occ, self.lbl_occupancy_rate = self.make_summary_row(
            os.path.join(BASE_DIR, "assets/occupancy.png"),
            "Occupancy: ...",
            "#1565c0"
        )

        sum_layout.addSpacing(6)
        sum_layout.addWidget(self.sum_active)
        sum_layout.addWidget(self.sum_maint)
        sum_layout.addWidget(self.sum_occ)


        bottom_grid.addWidget(act_card, 0, 0)
        bottom_grid.addWidget(recent_card, 0, 1)
        bottom_grid.addWidget(sum_card, 0, 2)

        bottom_grid.setColumnStretch(0, 2)
        bottom_grid.setColumnStretch(1, 2)
        bottom_grid.setColumnStretch(2, 1)

        root.addLayout(bottom_grid)

    # -------------------------
    # NAVIGATION METHODS
    # -------------------------
    def open_total_dorms(self):
        self.total_dorms_window = TotalDormsWindow(owner_id=self.host_id)
        self.total_dorms_window.show()
        self.total_dorms_window.show()
        self.close()
    
    def open_current_occupants(self):
        self.win_occ = CurrentOccupantsWindow(owner_id=self.host_id)
        self.win_occ.show()
        self.close()


    def open_pending_requests(self):
        self.win_pending = PendingRequestsWindow(owner_id=self.host_id)
        self.win_pending.show()
        self.close()


    def open_collections(self):
        self.monthly_win = MonthlyEarningsWindow(owner_id=self.host_id)
        windows_registry.append(self.monthly_win)
        self.monthly_win.show()
        self.close()

    def _make_stat_card(self, title, value):
        card = ClickableCard()
        card.setObjectName("statCard")
        card.setFixedHeight(115)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_title.setStyleSheet("color:#0c5d30;")
        layout.addWidget(lbl_title)

        layout.addStretch()

        lbl_value = QLabel(value)
        lbl_value.setFont(QFont("Segoe UI", 24, QFont.Bold))
        lbl_value.setStyleSheet("color:black;")  
        layout.addWidget(lbl_value)

        return card, lbl_value

    def _apply_styles(self):
        self.setStyleSheet("""
            /* Global */
            QWidget { background: #f2f5f3; color: #1d1d1d; font-family: 'Segoe UI'; }
            QLabel { font-family: 'Segoe UI'; }

            /* Cards */
            QFrame#statCard { background: white; border-radius: 14px; border: 2px solid #cce8d4; }
            QFrame#statCard:hover { background: #f6fbf7; border: 2px solid #0f7a3a; }
            QFrame#cardLarge, QFrame#cardSmall, QFrame#card {
                background: white; border-radius: 12px; border: 1px solid #c7d9cd;
            }
            /* Buttons */
            QPushButton {
                background: #0f7a3a; color: white; padding: 6px 14px; border-radius: 8px; font-size: 11px;
            }
            QPushButton:hover { background: #0c5d30; }
            
        """)

    def _start_clock(self):
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)  # update every second
        self._update_clock()
    
    def _update_clock(self):
        now = datetime.now()
        self.lbl_clock.setText(
            now.strftime("%A\n%B %d, %Y\n%I:%M:%S %p")
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OwnerDashboardWindow()
    w.show()
    sys.exit(app.exec_())