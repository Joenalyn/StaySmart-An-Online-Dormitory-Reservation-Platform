from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QFont, QCursor
from PyQt5.QtCore import Qt
from database import DatabaseManager
from datetime import datetime
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class PaymentsWindow(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle("Payments")
        self.resize(1000, 650)
        self.db = DatabaseManager()
        self.user_id = user_id 
        
        self._build_ui()
        self._apply_styles()

    def go_back(self):
        from student_dashboard import StudentDashboardWindow
        self.next_window = StudentDashboardWindow()
        self.next_window.show()
        self.close()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        payments = self.db.get_user_payments(self.user_id)

        # ----------------------------
        # Determine active payment
        # ----------------------------
        active_payment = next(
            (p for p in payments if p['status'] in ('Due', 'Overdue')),
            None
        )

        if active_payment:
            self.rental_id = active_payment['rental_id']
            self.amount_due = active_payment['amount_due']
        else:
            self.rental_id = None
            self.amount_due = 0

        due_items = [
            p for p in payments
            if p['status'] in ('Due', 'Overdue')
        ]

        outstanding = sum(
            p['amount_due'] for p in due_items
        )

        if self.rental_id:
            remark = self.db.get_last_payment_rejection(
                self.user_id,
                self.rental_id
            )

            if remark:
                QMessageBox.warning(
                    self,
                    "Payment Rejected",
                    f"Your last payment was rejected.\n\nReason:\n{remark}"
                )

        due_items.sort(key=lambda x: x['due_date'])
        next_due_str = "No Dues"

        if due_items:
            d = due_items[0]['due_date']
            next_due_str = f"{d.strftime('%B %d, %Y')}"

        paid_items = [p for p in payments if p['status'] == 'Paid']
        paid_items.sort(key=lambda x: x.get('payment_date') or x['due_date'], reverse=True)
        last_pay_str = "No history"
        if paid_items:
            p = paid_items[0]
            d = p.get('payment_date') or p['due_date']
            last_pay_str = f"₱{p['amount_due']:,.0f} — {d}"

        status_str = "Up to Date"
        if any(p['status'] == 'Overdue' for p in payments):
            status_str = "Overdue!"
        elif outstanding > 0:
            status_str = "Pending"

        # ----------------------------
        # HEADER
        # ----------------------------
        header = QHBoxLayout()

        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedHeight(36)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #e6e6e6;
                border-radius: 8px;
                padding: 6px 12px;
                color: black;
            }
            QPushButton:hover { background: #d0d0d0; }
        """)
        back_btn.clicked.connect(self.go_back)

        title = QLabel("Payments")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color:black;")

        header.addWidget(back_btn)
        header.addStretch()
        header.addWidget(title)
        header.addStretch()

        root.addLayout(header)

        # ----------------------------
        # TOP SUMMARY CARDS (Dynamic)
        # ----------------------------
        top = QHBoxLayout()
        top.setSpacing(12)

        top.addWidget(self._summary_card("Next Due", next_due_str))
        top.addWidget(self._summary_card(
            "Due Amount",
            f"₱{outstanding:,.2f}",
            show_pay_button=True
        ))
        top.addWidget(self._summary_card("Last Payment", last_pay_str))
        top.addWidget(self._summary_card("Status", status_str))

        root.addLayout(top)

        # ----------------------------
        # BILLING FILTERS
        # ----------------------------
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Billing Cycle:"))

        self.billing_filter = QComboBox()
        self.billing_filter.addItems(["Monthly", "Semester", "Annual", "All"])
        self.billing_filter.setFixedWidth(150)
        filter_row.addWidget(self.billing_filter)

        filter_row.addStretch()

        export_btn = QPushButton("Export Records")
        export_btn.setCursor(QCursor(Qt.PointingHandCursor))
        filter_row.addWidget(export_btn)

        root.addLayout(filter_row)

        table_frame = QFrame()
        table_frame.setObjectName("cardLarge")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel("Payment History")
        lbl.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        table_layout.addWidget(lbl)

        self.tbl = QTableWidget(len(payments), 4)
        self.tbl.setHorizontalHeaderLabels(["Date", "Amount", "Status", "Room"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for r, p in enumerate(payments):
            date_val = str(p['due_date'])
            amt_val = f"₱{p['amount_due']:,.2f}"
            status_val = p['status']
            room_val = p.get('room_name', 'Unknown')

            self.tbl.setItem(r, 0, QTableWidgetItem(date_val))
            self.tbl.setItem(r, 1, QTableWidgetItem(amt_val))
            self.tbl.setItem(r, 2, QTableWidgetItem(status_val))
            self.tbl.setItem(r, 3, QTableWidgetItem(room_val))

        table_layout.addWidget(self.tbl)
        root.addWidget(table_frame)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        breakdown = QFrame()
        breakdown.setObjectName("card")
        b_layout = QVBoxLayout(breakdown)
        b_layout.setContentsMargins(16, 16, 16, 16)

        b_layout.addWidget(QLabel("Payment Breakdown (Outstanding)"))
        br_list = QListWidget()

        rent_due = sum(p['amount_due'] for p in due_items if p.get('payment_type') == 'Rent')
        util_due = sum(p['amount_due'] for p in due_items if p.get('payment_type') == 'Utility')
        other_due = sum(p['amount_due'] for p in due_items if p.get('payment_type') not in ['Rent', 'Utility'])

        if rent_due > 0:
            QListWidgetItem(f"₱{rent_due:,.2f} — Rent", br_list)
        if util_due > 0:
            QListWidgetItem(f"₱{util_due:,.2f} — Utilities", br_list)
        if other_due > 0:
            QListWidgetItem(f"₱{other_due:,.2f} — Others", br_list)
        
        if outstanding <= 0 or status_str == "Up to Date":
            if hasattr(self, "btn_pay_now"):
                self.btn_pay_now.setDisabled(True)
        else:
            if hasattr(self, "btn_pay_now"):
                self.btn_pay_now.setEnabled(True)


        b_layout.addWidget(br_list)
        bottom.addWidget(breakdown)

        recent = QFrame()
        recent.setObjectName("card")
        r_layout = QVBoxLayout(recent)
        r_layout.setContentsMargins(16, 16, 16, 16)

        r_layout.addWidget(QLabel("Recent Payment Activity"))

        act_list = QListWidget()

        sorted_recent = sorted(payments, key=lambda x: x['due_date'], reverse=True)[:5]

        for p in sorted_recent:
            if p['status'] == 'Paid':
                msg = f"Paid ₱{p['amount_due']:,.0f} for {p.get('room_name','')}"
            elif p['status'] == 'Due':
                msg = f"Due: ₱{p['amount_due']:,.0f} on {p['due_date']}"
            else:
                msg = f"{p['status']}: ₱{p['amount_due']:,.0f}"

            QListWidgetItem(msg, act_list)

        r_layout.addWidget(act_list)
        bottom.addWidget(recent)


        root.addLayout(bottom)
        root.addStretch()

    def upload_payment_proof(self):
        file, _ = QFileDialog.getOpenFileName(self, "Upload Payment Proof", "", "Images (*.png *.jpg *.jpeg)")
        if not file:
            return

        # Copy proof into uploads/payment_proofs/
        folder = os.path.join(BASE_DIR, "uploads", "payment_proofs")
        os.makedirs(folder, exist_ok=True)

        filename = os.path.basename(file)
        final_path = os.path.join(folder, filename)
        shutil.copy(file, final_path)

        rel_path = os.path.relpath(final_path, BASE_DIR).replace("\\", "/")

        confirm = QMessageBox.question(
            self,
            "Confirm Payment",
            f"You are about to submit ₱{self.amount_due:,.2f}.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        self.db.submit_payment_request(self.user_id, self.rental_id, self.amount_due, rel_path)


        QMessageBox.information(self, "Payment Submitted", 
            "Your payment has been sent to the owner for verification.")
        
        has_pending = self.db.has_pending_payment_request(
            self.user_id,
            self.rental_id
        )

        if has_pending:
            self.btn_pay_now.setText("Pending Approval")
            self.btn_pay_now.setDisabled(True)

    def _summary_card(self, title, subtitle, show_pay_button=False):
        card = QFrame()
        card.setObjectName("statCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        layout.addWidget(t)

        layout.addStretch()

        row = QHBoxLayout()

        s = QLabel(subtitle)
        s.setFont(QFont("Segoe UI", 15, QFont.Bold))
        s.setStyleSheet("color: black;")
        row.addWidget(s)

        if show_pay_button:
            self.btn_pay_now = QPushButton("Pay Now")
            self.btn_pay_now.setFixedHeight(32)
            self.btn_pay_now.setCursor(Qt.PointingHandCursor)
            self.btn_pay_now.setStyleSheet("""
                QPushButton {
                    background:#0f7a3a;
                    color:white;
                    font-weight:bold;
                    padding:4px 12px;
                    border-radius:6px;
                }
                QPushButton:disabled {
                    background:#ccc;
                    color:#666;
                }
            """)
            self.btn_pay_now.clicked.connect(self.upload_payment_proof)

            row.addStretch()
            row.addWidget(self.btn_pay_now)

        layout.addLayout(row)
        return card

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: #f2f5f3; color: #1d1d1d; font-family: Segoe UI; }

            QFrame#statCard {
                background:white;
                border-radius:14px;
                border:2px solid #cce8d4;
            }
            QFrame#statCard:hover { border:2px solid #0f7a3a; }

            QFrame#card, QFrame#cardLarge {
                background:white;
                border-radius:14px;
                border:1px solid #d6e4db;
            }

            QPushButton {
                background:#0f7a3a;
                color:white;
                padding:6px 14px;
                border-radius:8px;
            }
            QPushButton:hover { background:#0c5d30; }
        """)

