from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QListWidgetItem, QApplication, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from database import DatabaseManager


class MyReservationsWindow(QWidget):
    def __init__(self, user_id=1):
        super().__init__()
        self.setWindowTitle("My Reservations")
        self.resize(900, 600)
        self.db = DatabaseManager()
        self.user_id = user_id 
        self._build_ui()
        self._apply_styles()

    def go_back(self):
        from student_dashboard import StudentDashboardWindow
        self.next_window = StudentDashboardWindow(user_id=self.user_id)
        self.next_window.show()
        self.close()
    
    def _cancel_reservation(self, reservation_id):
        if not reservation_id:
            QMessageBox.warning(self, "Error", "Reservation ID not found.")
            return

        confirm = QMessageBox.question(
            self,
            "Cancel Reservation",
            "Are you sure you want to cancel this reservation?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        try:
            self.db.cancel_reservation(reservation_id)

            QMessageBox.information(
                self,
                "Reservation Cancelled",
                "Your reservation has been cancelled successfully."
            )

            self.close()
            self.__init__(user_id=self.user_id)
            self.show()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to cancel reservation:\n{e}"
            )

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # HEADER ROW
        header_row = QHBoxLayout()

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

        title = QLabel("My Reservations")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color:black;")

        header_row.addWidget(back_btn)
        header_row.addStretch()
        header_row.addWidget(title)
        header_row.addStretch()

        root.addLayout(header_row)

        reservations = self.db.get_user_reservations(self.user_id)

        active_res = None
        history_res = []

        for r in reservations:
            status = str(r.get("status", "")).upper()
            if status in ["PENDING", "WAITING", "APPROVED", "ACTIVE"] and not active_res:
                active_res = r
            else:
                history_res.append(r)


        if not reservations:
            msg = QLabel("No current reservation.")
            msg.setAlignment(Qt.AlignCenter)
            msg.setFont(QFont("Segoe UI", 14))
            root.addWidget(msg)
            root.addStretch()
            return

        def k(row, *names, default="—"):
            for n in names:
                if n in row and row[n] is not None:
                    return row[n]
            return default


        if not active_res:
            msg = QLabel("No current reservation.")
            msg.setAlignment(Qt.AlignCenter)
            msg.setFont(QFont("Segoe UI", 14))
            root.addWidget(msg)
        else:
            active = active_res
            reservation_id = active.get("application_id") or active.get("reservation_id")

            active_card = QFrame()
            active_card.setObjectName("card")
            ac = QVBoxLayout(active_card)
            ac.setContentsMargins(16, 16, 16, 16)
            ac.setSpacing(6)

            t1 = QLabel("Active Reservation")
            t1.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
            ac.addWidget(t1)

            dorm_name = k(active, "property_name", "dorm_name")
            room_name = k(active, "room_name", "room_no", "room")

            move_in = k(active, "move_in_date", "start_date", "check_in_date")
            next_pay = k(active, "next_payment", "next_payment_date", "check_out_date")
            status = k(active, "status", "action_status")

            ac.addWidget(QLabel(f"Dorm: {dorm_name}"))
            ac.addWidget(QLabel(f"Room: {room_name}"))
            ac.addWidget(QLabel(f"Move-in Date: {move_in}"))
            ac.addWidget(QLabel(f"Next Payment / End: {next_pay}"))
            ac.addWidget(QLabel(f"Status: {status}"))

            btn_row = QHBoxLayout()
            btn_row.addStretch()

            btn_view = QPushButton("View Details")
            btn_row.addWidget(btn_view)

            btn_cancel = QPushButton("Cancel Reservation")
            btn_cancel.setEnabled(str(status).upper() in ["PENDING", "WAITING"])
            btn_cancel.clicked.connect(
                lambda: self._cancel_reservation(reservation_id)
            )
            btn_row.addWidget(btn_cancel)

            ac.addLayout(btn_row)
            root.addWidget(active_card)


        history_card = QFrame()
        history_card.setObjectName("card")
        hc = QVBoxLayout(history_card)
        hc.setContentsMargins(16, 16, 16, 16)
        hc.setSpacing(8)

        htitle = QLabel("Reservation History")
        htitle.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        hc.addWidget(htitle)

        list_history = QListWidget()
        history_items = history_res


        if not history_items:
            QListWidgetItem("No previous reservations.", list_history)
        else:
            for h in history_items:
                dorm = k(h, "property_name", "dorm_name")
                room = k(h, "room_name", "room_no", "room")
                start = k(h, "move_in_date", "start_date", "check_in_date")
                end = k(h, "check_out_date", "next_payment_date", "end_date")
                st = k(h, "status", "action_status")

                item_text = f"{dorm} — Room {room} — {start} to {end} — {st}"
                QListWidgetItem(item_text, list_history)

        hc.addWidget(list_history)
        root.addWidget(history_card)

        root.addStretch()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: #f2f5f3; }
            QLabel { color:#1d1d1d; font-family:'Segoe UI'; }

            QFrame#card {
                background:white;
                border-radius:14px;
                border:2px solid #cce8d4;
            }
            QFrame#card:hover {
                border:2px solid #0f7a3a;
                background:#f8fdf9;
            }

            QPushButton {
                background:#0f7a3a;
                color:white;
                border-radius:8px;
                padding:6px 14px;
                font-size:12px;
            }
            QPushButton:hover {
                background:#0c5d30;
            }

            QListWidget {
                border:1px solid #cbd9d0;
                border-radius:8px;
                background:white;
            }
        """)

if __name__ == "__main__":
    app = QApplication([])
    win = MyReservationsWindow(user_id=1)
    win.show()
    app.exec_()
