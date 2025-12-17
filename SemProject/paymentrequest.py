from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QFrame, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt
import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from database import DatabaseManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class PaymentRequestsWindow(QWidget):
    def __init__(self, owner_id, parent_window=None):
        super().__init__()
        self.owner_id = owner_id
        self.parent_window = parent_window
        self.db = DatabaseManager()

        self.setWindowTitle("Pending Requests — StaySmart")
        self.setMinimumSize(1100, 700)

        self.build_ui()

        self.load_requests()

    def go_back(self):
        if self.parent_window:
            self.parent_window.showMaximized()
        self.close()


    # ---------------- UI ----------------
    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ---------- HEADER ----------
        header = QHBoxLayout()

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
        title.setFont(QFont("Poppins", 22, QFont.Bold))
        title.setStyleSheet("color:#137333;")

        header.addWidget(btn_back)
        header.addSpacing(12)
        header.addWidget(title)
        header.addStretch()

        root.addLayout(header)

        # ---------- SEARCH ----------
        search_row = QHBoxLayout()
        lbl_search = QLabel("Search:")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tenant / Amount ...")
        self.search.textChanged.connect(self.filter_table)

        search_row.addWidget(lbl_search)
        search_row.addWidget(self.search)

        root.addLayout(search_row)

        # ---------- CARD ----------
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_title = QLabel("Applications Waiting for Approval")
        card_title.setFont(QFont("Poppins", 14, QFont.Bold))
        card_title.setStyleSheet("color:#137333;")

        card_layout.addWidget(card_title)

        # ---------- TABLE ----------
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Tenant", "Amount", "Proof", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #cce5d6;
                border-radius: 10px;
            }
            QHeaderView::section {
                background: #eaf6ef;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background: #d4f2e2;
                color: black;
            }
        """)

        card_layout.addWidget(self.table)
        root.addWidget(card, 1)

        # ---------- ACTION BUTTONS ----------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_approve = QPushButton("Approve")
        self.btn_reject = QPushButton("Reject")
        self.btn_view = QPushButton("View Proof")

        for btn in (self.btn_approve, self.btn_reject, self.btn_view):
            btn.setFixedHeight(40)
            btn.setCursor(Qt.PointingHandCursor)

        self.btn_approve.setStyleSheet(self.btn_style("#1a7f37"))
        self.btn_reject.setStyleSheet(self.btn_style("#c62828"))
        self.btn_view.setStyleSheet(self.btn_style("#137333"))

        self.btn_approve.clicked.connect(self.approve_selected)
        self.btn_reject.clicked.connect(self.reject_selected)
        self.btn_view.clicked.connect(self.view_proof)
        

        btn_row.addWidget(self.btn_approve)
        btn_row.addWidget(self.btn_reject)
        btn_row.addWidget(self.btn_view)

        root.addLayout(btn_row)

    # ---------------- STYLES ----------------
    def btn_style(self, color):
        return f"""
            QPushButton {{
                background:{color};
                color:white;
                border:none;
                border-radius:20px;
                padding:8px 24px;
                font-weight:bold;
            }}
            QPushButton:hover {{
                background:#145a32;
            }}
        """

    # ---------------- DATA ----------------
    def load_requests(self):
        self.table.setRowCount(0)

        requests = self.db.get_pending_payment_requests(self.owner_id)

        for row, req in enumerate(requests):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(req["tenant_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(f"₱{req['amount']:,}"))
            self.table.setItem(row, 2, QTableWidgetItem("View"))
            self.table.setItem(row, 3, QTableWidgetItem("Pending"))

    # ---------------- ACTIONS ----------------
    def selected_row(self):
        row = self.table.currentRow()
        return row if row >= 0 else None

    def approve_selected(self):
        row = self.selected_row()
        if row is None:
            return
        tenant = self.table.item(row, 0).text()
        print("Approved:", tenant)

    def reject_selected(self):
        row = self.selected_row()
        if row is None:
            return
        tenant = self.table.item(row, 0).text()
        print("Rejected:", tenant)

    def view_proof(self):
        row = self.selected_row()
        if row is None:
            return
        tenant = self.table.item(row, 0).text()
        print("View proof for:", tenant)

    def filter_table(self, text):
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)



    def load_requests(self):
        requests = self.db.get_pending_payment_requests(self.owner_id)
        self.table.setRowCount(0)

        for row, req in enumerate(requests):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(req["tenant_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(req["amount"])))

            # Proof button
            btn_proof = QPushButton("View")
            btn_proof.clicked.connect(lambda _, p=req["proof_image"]: self.show_proof(p))
            self.table.setCellWidget(row, 2, btn_proof)

            # Approve button
            btn_appr = QPushButton("Approve")
            btn_appr.clicked.connect(lambda _, r=req: self.approve(r))
            self.table.setCellWidget(row, 3, btn_appr)

            # Reject button
            btn_rej = QPushButton("Reject")
            btn_rej.clicked.connect(lambda _, r=req: self.reject(r))
            self.table.setCellWidget(row, 4, btn_rej)

    def show_proof(self, path):
        abs_path = os.path.join(BASE_DIR, path)
        QMessageBox.information(self, "Payment Proof", f"Image located at:\n{abs_path}")

    def approve(self, req):
        self.db.review_payment_request(req["request_id"], approve=True)
        self.db.update_payment_due_date(req["rental_id"])
        self.load_requests()

    def reject(self, req):
        self.db.review_payment_request(req["request_id"], approve=False)
        QMessageBox.warning(self, "Rejected", 
            "Payment declined. Tenant will be notified.")
        self.load_requests()

def main():

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = PaymentRequestsWindow(owner_id=1)
    window.show()


    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
