import sys, csv
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView,
    QFileDialog, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from database import DatabaseManager


class MonthlyEarningsWindow(QWidget):
    def __init__(self, owner_id):
        super().__init__()
        self.setWindowTitle("Monthly Earnings - StaySmart")
        self.setMinimumSize(1050, 720)

        self.db = DatabaseManager()
        self.owner_id = owner_id

        self.font_title = QFont("Segoe UI", 18, QFont.Bold)
        self.font_section = QFont("Segoe UI", 13, QFont.DemiBold)

        self._build_ui()
        self._apply_styles()
        self._init_years()
        self.load_data()

    # -----------------------------------------------------
    # NAVIGATION
    # -----------------------------------------------------
    def go_back(self):
        from owner_dashboard import OwnerDashboardWindow
        self.dashboard = OwnerDashboardWindow(owner_id=self.owner_id)
        self.dashboard.show()
        self.close()

    # -----------------------------------------------------
    # LOAD + REFRESH UI FROM DB
    # -----------------------------------------------------
    def _init_years(self):
        """Fill year combo from DB (fallback to current year)."""
        years = self.db.get_owner_transaction_years(self.owner_id)
        if not years:
            years = [datetime.now().year]
        self.combo_year.clear()
        self.combo_year.addItems([str(y) for y in years])

    def load_data(self):
        year = int(self.combo_year.currentText())
        now = datetime.now()

        # ---- STAT CARDS ----
        summary = self.db.get_monthly_earnings_summary(
            self.owner_id, year=year, month=now.month
        )
        self.lbl_total_val.setText(f"₱ {summary['paid']:,.0f}")
        self.lbl_pending_val.setText(f"₱ {summary['pending']:,.0f}")
        self.lbl_rate_val.setText(f"{summary['collection_rate']}%")

        # ---- CHART ----
        series = self.db.get_monthly_revenue_series(self.owner_id, year=year)
        self._plot_chart(series, year)

        # ---- TABLE ----
        tx = self.db.get_recent_transactions(self.owner_id, year=year, limit=15)
        self.table.setRowCount(0)

        for row, t in enumerate(tx):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(t["transaction_date"].date())))
            self.table.setItem(row, 1, QTableWidgetItem(t["tenant_name"]))
            self.table.setItem(row, 2, QTableWidgetItem(f"₱ {float(t['amount']):,.0f}"))
            self.table.setItem(row, 3, QTableWidgetItem(t["status"]))

    # -----------------------------------------------------
    # EXPORT REPORT (CSV)
    # -----------------------------------------------------
    def export_report(self):
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "No Data", "No transactions to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            "monthly_earnings_report.csv",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # header
                headers = [self.table.horizontalHeaderItem(i).text()
                           for i in range(self.table.columnCount())]
                writer.writerow(headers)

                # rows
                for r in range(self.table.rowCount()):
                    row_vals = []
                    for c in range(self.table.columnCount()):
                        item = self.table.item(r, c)
                        row_vals.append(item.text() if item else "")
                    writer.writerow(row_vals)

            QMessageBox.information(self, "Exported", f"Report saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # --- HEADER ---
        header = QHBoxLayout()
        header.setSpacing(15)

        btn_back = QPushButton("← Back")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFixedWidth(80)
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

        title = QLabel("Monthly Earnings")
        title.setFont(self.font_title)
        header.addWidget(title)

        header.addStretch()

        self.btn_export = QPushButton("Export Report")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_report)
        header.addWidget(self.btn_export)

        layout.addLayout(header)

        # --------------------------- TOP STAT CARDS ---------------------------
        top_grid = QHBoxLayout()
        top_grid.setSpacing(12)

        self.card_total, self.lbl_total_val = self._make_stat_card("Total Earnings", "₱ 0")
        self.card_pending, self.lbl_pending_val = self._make_stat_card("Pending Payments", "₱ 0")
        self.card_rate, self.lbl_rate_val = self._make_stat_card("Collection Rate", "0%")

        top_grid.addWidget(self.card_total)
        top_grid.addWidget(self.card_pending)
        top_grid.addWidget(self.card_rate)

        layout.addLayout(top_grid)

        # --------------------------- CHART SECTION ---------------------------
        chart_frame = QFrame()
        chart_frame.setObjectName("cardLarge")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(12, 12, 12, 12)

        chart_header = QHBoxLayout()
        lbl_chart = QLabel("Revenue Overview")
        lbl_chart.setFont(self.font_section)
        chart_header.addWidget(lbl_chart)
        chart_header.addStretch()

        self.combo_year = QComboBox()
        self.combo_year.currentTextChanged.connect(self.load_data)
        chart_header.addWidget(self.combo_year)
        chart_layout.addLayout(chart_header)

        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)

        layout.addWidget(chart_frame)

        # --------------------------- RECENT TRANSACTIONS TABLE ---------------------------
        table_frame = QFrame()
        table_frame.setObjectName("card")
        t_layout = QVBoxLayout(table_frame)
        t_layout.setContentsMargins(12, 12, 12, 12)

        lbl_table = QLabel("Recent Transactions")
        lbl_table.setFont(self.font_section)
        t_layout.addWidget(lbl_table)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Tenant", "Amount", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("border:none;")

        t_layout.addWidget(self.table)
        layout.addWidget(table_frame)

    # -----------------------------------------------------
    # CHART PLOT
    # -----------------------------------------------------
    def _plot_chart(self, month_to_amount, year):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        earnings = [month_to_amount.get(i+1, 0) for i in range(12)]

        ax.plot(months, earnings, marker='o', linestyle='-', linewidth=2)
        ax.set_title(f"Monthly Revenue Trend ({year})")
        ax.grid(True, linestyle='--', alpha=0.6)
        self.canvas.draw()

    # -----------------------------------------------------
    # Helper: Stat Card
    # -----------------------------------------------------
    def _make_stat_card(self, title, value):
        card = QFrame()
        card.setObjectName("statCard")
        card.setFixedHeight(105)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_lbl.setStyleSheet("color:#0f7a3a;")

        val_lbl = QLabel(value)
        val_lbl.setFont(QFont("Segoe UI", 22, QFont.Bold))
        val_lbl.setStyleSheet("color:black;")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(title_lbl)
        lay.addStretch()
        lay.addWidget(val_lbl)
        return card, val_lbl

    # -----------------------------------------------------
    # Stylesheet
    # -----------------------------------------------------
    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background:#f2f5f3; color:#1d1d1d; font-family: 'Segoe UI'; }

            QFrame#statCard {
                background:white;
                border-radius:14px;
                border:2px solid #cce8d4;
            }
            QFrame#statCard:hover {
                border:2px solid #0f7a3a;
                background:#f6fbf7;
            }

            QFrame#card, QFrame#cardLarge {
                background:white;
                border-radius:12px;
                border:1px solid #c7d9cd;
            }

            QPushButton {
                background:#0f7a3a;
                color:white;
                border-radius:6px;
                padding:5px 12px;
            }
            QPushButton:hover {
                background:#0c5d30;
            }

            QTableWidget {
                background:white;
                border:none;
            }
            QHeaderView::section {
                background:#e8f3ec;
                padding:4px;
                border:none;
                font-weight:bold;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MonthlyEarningsWindow(owner_id=1)
    win.show()
    sys.exit(app.exec_())
