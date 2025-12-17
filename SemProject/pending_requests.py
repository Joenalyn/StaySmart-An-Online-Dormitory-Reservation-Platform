# pending_requests.py
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from database import DatabaseManager


class PendingRequestsWindow(QWidget):
    def __init__(self, owner_id):
        super().__init__()
        self.setWindowTitle("Pending Requests — StaySmart")
        self.setMinimumSize(1000, 600)

        self.db = DatabaseManager()
        self.owner_id = owner_id
        self.requests = []

        self._fonts()
        self._apply_styles()
        self._build_ui()
        self.load_data()

    def _fonts(self):
        self.font_title = QFont("Segoe UI", 20, QFont.Bold)
        self.font_section = QFont("Segoe UI", 12, QFont.DemiBold)
        self.font_normal = QFont("Segoe UI", 10)

    # -------------------------
    # NAVIGATION
    # -------------------------
    def go_back(self):
        from owner_dashboard import OwnerDashboardWindow
        self.dashboard = OwnerDashboardWindow(owner_id=self.owner_id)
        self.dashboard.show()
        self.close()

    # -------------------------
    # DB LOAD
    # -------------------------
    def load_data(self):
        search = self.txt_search.text().strip() if hasattr(self, "txt_search") else ""
        all_requests = self.db.get_pending_requests(self.owner_id)

        if search:
            s = search.lower()
            self.requests = [
                r for r in all_requests
                if s in r["applicant"].lower()
                or s in r["dorm"].lower()
                or s in str(r["room_name"]).lower()
            ]
        else:
            self.requests = all_requests

        self.table.setRowCount(0)

        for row, req in enumerate(self.requests):
            self.table.insertRow(row)
            id_item = QTableWidgetItem(str(req["request_id"]))
            id_item.setData(Qt.UserRole, req["request_id"])

            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(req["applicant"]))
            self.table.setItem(row, 2, QTableWidgetItem(req["dorm"]))
            self.table.setItem(row, 3, QTableWidgetItem(req["room_type"]))
            self.table.setItem(row, 4, QTableWidgetItem(str(req["submitted_at"])))
            self.table.setItem(row, 5, QTableWidgetItem(req["status"]))
            self.table.setItem(row, 6, QTableWidgetItem("WAITING"))

    def get_selected_request(self):
        row = self.table.currentRow()
        if row < 0:
            return None

        req = self.requests[row]
        return req

    def approve_selected(self):
        req = self.get_selected_request()
        if not req:
            QMessageBox.warning(self, "No Selection", "Please select a request to approve.")
            return

        confirm = QMessageBox.question(
            self,
            "Approve Request",
            f"Approve application from '{req['applicant']}' for {req['dorm']} room {req['room_name']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        if self.db.approve_request(req["request_id"]):
            QMessageBox.information(self, "Approved", "Request approved successfully.")
            self.load_data()
        else:
            QMessageBox.critical(self, "Error", "Failed to approve request.")

    def reject_selected(self):
        req = self.get_selected_request()
        if not req:
            QMessageBox.warning(self, "No Selection", "Please select a request to reject.")
            return

        note, ok = QInputDialog.getText(
            self,
            "Reject Request",
            "Enter rejection reason (optional):"
        )
        if not ok: 
            return

        confirm = QMessageBox.question(
            self,
            "Reject Request",
            f"Reject application from '{req['applicant']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        if self.db.reject_request(req["request_id"], note):
            QMessageBox.information(self, "Rejected", "Request rejected successfully.")
            self.load_data()
        else:
            QMessageBox.critical(self, "Error", "Failed to reject request.")

    def view_details(self):
        req = self.get_selected_request()
        if not req:
            QMessageBox.warning(self, "No Selection", "Please select a request to view.")
            return

        QMessageBox.information(
            self,
            "Request Details",
            f"""
Request ID: {req['request_id']}
Applicant: {req['applicant']}
Dorm: {req['dorm']}
Room No.: {req['room_name']}
Room Type: {req['room_type']}
Submitted On: {req['submitted_at']}
Status: {req['status']}
            """.strip()
        )

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: #f2f5f3; color:#1d1d1d; }
            QLabel { font-family: Segoe UI; }

            QFrame#panel {
                background:white;
                border-radius:14px;
                border:2px solid #cce8d4;
            }

            QPushButton {
                background:#0f7a3a;
                color:white;
                padding:6px 14px;
                border-radius:8px;
                font-size:11px;
            }
            QPushButton:hover { background:#0c5d30; }

            QLineEdit {
                background:white;
                border-radius:8px;
                border:1px solid #cce8d4;
                padding:6px;
            }

            QTableWidget {
                background:white;
                border:1px solid #cce8d4;
                border-radius:10px;
            }
            QHeaderView::section {
                background:#e8f3ec;
                padding:6px;
                font-weight:bold;
                border:none;
            }
        """)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- HEADER ---
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

        title = QLabel("Pending Requests")
        title.setFont(self.font_title)
        title.setStyleSheet("color:#0f7a3a;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # --- SEARCH ---
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Applicant / Dorm / Room...")
        self.txt_search.textChanged.connect(self.load_data)
        search_row.addWidget(self.txt_search)

        layout.addLayout(search_row)

        # TABLE PANEL
        panel = QFrame()
        panel.setObjectName("panel")
        box = QVBoxLayout(panel)

        label = QLabel("Applications Waiting for Approval")
        label.setFont(self.font_section)
        label.setStyleSheet("color:#0f7a3a;")
        box.addWidget(label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Request ID", "Applicant", "Dorm", "Room Type",
            "Submitted On", "Status", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        box.addWidget(self.table)
        layout.addWidget(panel)

        # ACTIONS PANEL
        act_panel = QFrame()
        act_panel.setObjectName("panel")
        act = QHBoxLayout(act_panel)

        btn_approve = QPushButton("Approve")
        btn_approve.clicked.connect(self.approve_selected)

        btn_reject = QPushButton("Reject")
        btn_reject.clicked.connect(self.reject_selected)

        btn_view = QPushButton("View Details")
        btn_view.clicked.connect(self.view_details)

        act.addWidget(btn_approve)
        act.addWidget(btn_reject)
        act.addWidget(btn_view)

        layout.addWidget(act_panel)
