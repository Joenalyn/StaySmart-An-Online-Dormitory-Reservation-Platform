import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from database import DatabaseManager


class CurrentOccupantsWindow(QWidget):
    def __init__(self, owner_id):
        super().__init__()
        self.db = DatabaseManager()
        self.owner_id = owner_id

        self.setWindowTitle("Current Occupants - StaySmart")
        self.resize(1300, 750)

        self._fonts()
        self._build_ui()
        self._apply_styles()
        self.load_data()

    def _fonts(self):
        self.font_title   = QFont("Segoe UI", 18, QFont.Bold)
        self.font_section = QFont("Segoe UI", 12, QFont.DemiBold)
        self.font_normal  = QFont("Segoe UI", 10)

    def load_data(self):
        search = self.txt_search.text().strip() if hasattr(self, "txt_search") else ""
        occupants = self.db.get_current_occupants(self.owner_id, search)

        self.table.setRowCount(0)
        for r, occ in enumerate(occupants):
            self.table.insertRow(r)

            id_item = QTableWidgetItem(str(occ["tenant_id"]))
            id_item.setData(Qt.UserRole, occ["rental_id"])

            self.table.setItem(r, 0, id_item)
            self.table.setItem(r, 1, QTableWidgetItem(occ["tenant_name"]))
            self.table.setItem(r, 2, QTableWidgetItem(occ["dorm_name"]))
            self.table.setItem(r, 3, QTableWidgetItem(str(occ["room_no"])))
            self.table.setItem(r, 4, QTableWidgetItem(occ["tenant_phone"]))
            self.table.setItem(r, 5, QTableWidgetItem(str(occ["start_date"])))
            self.table.setItem(r, 6, QTableWidgetItem(occ["status"]))


        total_occupants = len(occupants)

        filled_rooms = len({(o["dorm_name"], o["room_no"]) for o in occupants})

        cap_row = self.db.fetchone("""
            SELECT COALESCE(SUM(capacity),0) AS cap
            FROM rooms r
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE d.owner_id=%s
        """, (self.owner_id,))
        total_capacity = cap_row["cap"] if cap_row and cap_row["cap"] else 0
        occ_rate = int((total_occupants / total_capacity) * 100) if total_capacity else 0

        self.lbl_total.setText(str(total_occupants))
        self.lbl_filled.setText(str(filled_rooms))
        self.lbl_rate.setText(f"{occ_rate}%")

    def view_details(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an occupant.")
            return

        tenant_id = int(self.table.item(row, 0).text())

        from tenant_details import TenantDetailsWindow
        self.details = TenantDetailsWindow(tenant_id)
        self.details.show()

    def end_contract(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an occupant to end contract.")
            return

        id_item = self.table.item(row, 0)
        rental_id = id_item.data(Qt.UserRole)
        tenant_name = self.table.item(row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Confirm End Contract",
            f"End contract for '{tenant_name}'?\nThis will mark the room as available.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        success = self.db.end_rental_contract(rental_id)

        if success:
            QMessageBox.information(self, "Success", "Contract ended successfully.")
            self.load_data()
        else:
            QMessageBox.critical(self, "Database Error", "Failed to end contract.")

    # -------------------------
    # NAVIGATION
    # -------------------------
    def go_back(self):
        from owner_dashboard import OwnerDashboardWindow
        self.dashboard = OwnerDashboardWindow(owner_id=self.owner_id)
        self.dashboard.show()
        self.close()

    # -------------------------
    # BUILD UI
    # -------------------------
    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(15)

        btn_back = QPushButton("← Back")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background: #e6e6e6;
                color: #333;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                border: 1px solid #ccc;
            }
            QPushButton:hover { background: #d0d0d0; }
        """)
        btn_back.clicked.connect(self.go_back)
        header.addWidget(btn_back)

        title = QLabel("Current Occupants")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)

        header.addStretch()
        main.addLayout(header)

        top_cards = QHBoxLayout()
        top_cards.setSpacing(20)

        self.card_total, self.lbl_total = self._create_stat_card("Total Occupants", "0")
        self.card_filled, self.lbl_filled = self._create_stat_card("Filled Rooms", "0")
        self.card_rate, self.lbl_rate = self._create_stat_card("Occupancy Rate", "0%")

        top_cards.addWidget(self.card_total)
        top_cards.addWidget(self.card_filled)
        top_cards.addWidget(self.card_rate)

        main.addLayout(top_cards)

        search_row = QHBoxLayout()
        search_row.setSpacing(15)


        search_label = QLabel("Search:")
        search_label.setFont(QFont("Segoe UI", 11))

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search occupant name...")
        self.txt_search.textChanged.connect(self.load_data)
        self.txt_search.setMinimumWidth(250)

        search_row.addWidget(search_label)
        search_row.addWidget(self.txt_search)

        search_row.addStretch()

        btn_view = QPushButton("View Details")
        btn_view.clicked.connect(self.view_details)

        btn_end = QPushButton("End Contract")
        btn_end.clicked.connect(self.end_contract)

        search_row.addWidget(btn_view)
        search_row.addWidget(btn_end)

        main.addLayout(search_row)

        table_frame = QFrame()
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(12, 12, 12, 12)

        tbl_label = QLabel("Occupants List")
        tbl_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        table_layout.addWidget(tbl_label)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Occupant ID", "Full Name", "Dorm", "Room No.",
            "Contact No.", "Start Date", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        table_layout.addWidget(self.table)
        main.addWidget(table_frame)

    def _create_stat_card(self, title, value):
        frame = QFrame()
        frame.setObjectName("statCard")
        frame.setFixedHeight(120)  

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12) 
        layout.setSpacing(6)

        lbl_title = QLabel(title)
        lbl_title.setFont(self.font_section)
        lbl_title.setStyleSheet("color:#0c5d30;")

        lbl_value = QLabel(value)
        lbl_value.setFont(QFont("Segoe UI", 26, QFont.Bold)) 
        lbl_value.setObjectName("numberText")
        lbl_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(lbl_title)
        layout.addStretch()
        layout.addWidget(lbl_value)

        return frame, lbl_value

    # -------------------------
    # STYLESHEET
    # -------------------------
    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { 
                background: #f2f5f3; 
                color: #1d1d1d;
                font-family: Segoe UI; 
            }

            /* STAT CARDS */
            QFrame#statCard {
                background:white;
                border-radius:14px;
                border:2px solid #cce8d4;
            }
            QFrame#statCard:hover {
                border:2px solid #0f7a3a;
                background:#f6fbf7;
            }
            QLabel#numberText {
                color:#0f3f2b;
            }

            /* Buttons */
            QPushButton {
                background:#0f7a3a;
                color:white;
                padding:6px 16px;
                border-radius:8px;
                font-size:12px;
            }
            QPushButton:hover { background:#0c5d30; }

            QLineEdit {
                background:white;
                padding:5px 8px;
                border:1px solid #c7d9cd;
                border-radius:6px;
                font-size:11px;
            }

            /* Table */
            QTableWidget {
                background:white;
                border:1px solid #d6e2da;
                border-radius:10px;
            }
            QHeaderView::section {
                background:#eaf3ee;
                padding:6px;
                border:none;
                font-weight:bold;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CurrentOccupantsWindow(owner_id=1)
    win.show()
    sys.exit(app.exec_())
