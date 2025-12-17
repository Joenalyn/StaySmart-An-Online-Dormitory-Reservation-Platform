import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QListWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QLineEdit, QMessageBox
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt

from database import DatabaseManager
from add_dorm import AddDormForm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def resolve_image_path(rel_or_abs):
    if not rel_or_abs:
        return None
    if os.path.isabs(rel_or_abs):
        return rel_or_abs
    return os.path.join(BASE_DIR, rel_or_abs.replace("/", os.sep))

class DormDialog(QDialog):
    """UI for Editing a Dorm (Add is handled by AddDormForm)"""
    def __init__(self, parent=None, dorm_data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Dorm")
        self.setFixedSize(400, 220)
        self.dorm_data = dorm_data
        self.data_saved = False

        self._build_ui()
        if dorm_data:
            self._populate_fields()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Dorm Name")

        self.inp_address = QLineEdit()
        self.inp_address.setPlaceholderText("Address")

        layout.addWidget(QLabel("Dorm Name:"))
        layout.addWidget(self.inp_name)
        layout.addWidget(QLabel("Address:"))
        layout.addWidget(self.inp_address)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_dorm)
        btn_save.setStyleSheet(
            "background:#0f7a3a; color:white; padding:6px; border-radius:4px;"
        )

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _populate_fields(self):
        self.inp_name.setText(self.dorm_data.get("name", ""))
        self.inp_address.setText(self.dorm_data.get("address", ""))

    def save_dorm(self):
        name = self.inp_name.text().strip()
        address = self.inp_address.text().strip()

        if not name:
            QMessageBox.warning(self, "Input Error", "Dorm Name is required.")
            return

        db = DatabaseManager()
        pid = self.dorm_data["property_id"]
        success = db.update_property(pid, name, address)

        if success:
            self.data_saved = True
            self.accept()
        else:
            QMessageBox.critical(self, "Database Error", "Failed to update dorm.")


# ---------------------------
# BASE WINDOW
# ---------------------------
class StyledWindowBase(QWidget):
    """Base class for consistent styling + owner-aware DB access."""
    def __init__(self, title, owner_id):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(900, 600)
        self.db = DatabaseManager()
        self.host_id = owner_id

        self._fonts()
        self._apply_styles()

    def _fonts(self):
        self.font_title = QFont("Segoe UI", 16, QFont.Bold)
        self.font_normal = QFont("Segoe UI", 10)
        self.font_section = QFont("Segoe UI", 12, QFont.DemiBold)

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background:#f5f7f8; color:#222; font-family:"Segoe UI"; }
            QFrame.card { background:white; border-radius:10px; border:1px solid #ddd; }
            QHeaderView::section {
                background:#eef2f2; padding:6px; border:none; font-weight:600;
            }
            QTableWidget { background:white; border:1px solid #ddd; }
        """)


# ---------------------------
# TOTAL DORMS DETAIL
# ---------------------------
class TotalDormsDetailWindow(StyledWindowBase):
    def __init__(self, owner_id):
        super().__init__("Total Dorms — Management", owner_id)
        self._win_add_dorm = None
        self.properties = []

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("My Dorms", font=self.font_title))
        hdr.addStretch()

        btn_add = QPushButton("+ Add Dorm")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(
            "background:#0f7a3a; color:white; padding:8px 16px;"
            "border-radius:6px; font-weight:bold;"
        )
        btn_add.clicked.connect(self.open_add_dorm_form)
        hdr.addWidget(btn_add)

        layout.addLayout(hdr)

        main_row = QHBoxLayout()

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Address", "Rooms"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.currentCellChanged.connect(self.update_preview)
        main_row.addWidget(self.table, 3)

        self.preview_label = QLabel("Select a dorm to preview image")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(260, 200)
        self.preview_label.setStyleSheet(
            "background:white; border-radius:10px; border:1px solid #ddd; color:#666;"
        )
        main_row.addWidget(self.preview_label, 1)

        layout.addLayout(main_row)

        actions = QHBoxLayout()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_data)

        btn_edit = QPushButton("Edit Selected")
        btn_edit.clicked.connect(self.open_edit_dialog)

        btn_del = QPushButton("Delete Selected")
        btn_del.setStyleSheet(
            "background:#ff4d4d; color:white; border-radius:4px; padding:6px;"
        )
        btn_del.clicked.connect(self.delete_dorm)

        actions.addWidget(btn_refresh)
        actions.addStretch()
        actions.addWidget(btn_edit)
        actions.addWidget(btn_del)
        layout.addLayout(actions)

    def load_data(self):
        self.table.setRowCount(0)
        self.properties = self.db.get_host_properties(self.host_id)

        for row, prop in enumerate(self.properties):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(prop["property_id"])))
            self.table.setItem(row, 1, QTableWidgetItem(prop["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(prop["address"]))
            self.table.setItem(row, 3, QTableWidgetItem(str(prop["room_count"])))

        # reset preview
        self.preview_label.setText("Select a dorm to preview image")
        self.preview_label.setPixmap(QPixmap())

    def update_preview(self, currentRow, currentColumn, prevRow, prevColumn):
        if currentRow < 0 or currentRow >= len(self.properties):
            self.preview_label.setText("Select a dorm to preview image")
            self.preview_label.setPixmap(QPixmap())
            return

        dorm = self.properties[currentRow]
        dorm_id = dorm["property_id"]
        rel_path = self.db.get_dorm_main_image(dorm_id)

        if not rel_path:
            self.preview_label.setText("No image")
            self.preview_label.setPixmap(QPixmap())
            return

        abs_path = resolve_image_path(rel_path)
        if not abs_path or not os.path.exists(abs_path):
            self.preview_label.setText("Image not found")
            self.preview_label.setPixmap(QPixmap())
            return

        pix = QPixmap(abs_path)
        if pix.isNull():
            self.preview_label.setText("Invalid image")
            self.preview_label.setPixmap(QPixmap())
            return

        self.preview_label.setText("")
        self.preview_label.setPixmap(
            pix.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def open_add_dorm_form(self):
        self._win_add_dorm = AddDormForm(owner_id=self.host_id)
        self._win_add_dorm.show()

    def open_edit_dialog(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a dorm to edit.")
            return

        prop_data = self.properties[row]
        dlg = DormDialog(self, prop_data)
        if dlg.exec_():
            self.load_data()

    def delete_dorm(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a dorm to delete.")
            return

        prop_id = self.properties[row]["property_id"]
        name = self.properties[row]["name"]

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            if self.db.delete_property(prop_id):
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Could not delete dorm.")


# ---------------------------
# AVAILABLE ROOMS
# ---------------------------
class AvailableRoomsWindow(StyledWindowBase):
    def __init__(self, owner_id):
        super().__init__("Available Rooms", owner_id)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Available Rooms", font=self.font_title))

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Room ID", "Dorm", "Name/No", "Type", "Capacity", "Price", "Image"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_data)
        layout.addWidget(btn_refresh)

    def load_data(self):
        self.table.setRowCount(0)
        rooms = self.db.get_available_rooms_host(self.host_id)

        for r, room in enumerate(rooms):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(room["room_id"])))
            self.table.setItem(r, 1, QTableWidgetItem(room["dorm_name"]))
            self.table.setItem(r, 2, QTableWidgetItem(room["room_name"]))
            self.table.setItem(r, 3, QTableWidgetItem(room["type"]))
            self.table.setItem(r, 4, QTableWidgetItem(str(room["capacity"])))
            self.table.setItem(r, 5, QTableWidgetItem(f"₱{room['price']}"))

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setFixedSize(120, 80)
            rel_path = self.db.get_dorm_main_image(room.get("dorm_id"))
            if rel_path:
                abs_path = resolve_image_path(rel_path)
                if abs_path and os.path.exists(abs_path):
                    pix = QPixmap(abs_path)
                    if not pix.isNull():
                        img_label.setPixmap(
                            pix.scaled(img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        )
                    else:
                        img_label.setText("Invalid")
                else:
                    img_label.setText("Not found")
            else:
                img_label.setText("No image")

            self.table.setCellWidget(r, 6, img_label)

# ---------------------------
# OCCUPIED ROOMS
# ---------------------------
class OccupiedRoomsWindow(StyledWindowBase):
    def __init__(self, owner_id):
        super().__init__("Occupied Rooms", owner_id)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Occupied Rooms", font=self.font_title))

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Room", "Dorm", "Tenant", "Check In", "Check Out", "Status", "Image"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_data)
        layout.addWidget(btn_refresh)

    def load_data(self):
        self.table.setRowCount(0)
        rooms = self.db.get_occupied_rooms_host(self.host_id)

        for r, room in enumerate(rooms):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(room["room_name"]))
            self.table.setItem(r, 1, QTableWidgetItem(room["dorm_name"]))
            self.table.setItem(r, 2, QTableWidgetItem(room["tenant_name"]))
            self.table.setItem(r, 3, QTableWidgetItem(str(room["check_in_date"])))
            self.table.setItem(r, 4, QTableWidgetItem(str(room["check_out_date"])))
            self.table.setItem(r, 5, QTableWidgetItem("Active"))

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setFixedSize(120, 80)
            rel_path = self.db.get_dorm_main_image(room.get("dorm_id"))
            if rel_path:
                abs_path = resolve_image_path(rel_path)
                if abs_path and os.path.exists(abs_path):
                    pix = QPixmap(abs_path)
                    if not pix.isNull():
                        img_label.setPixmap(
                            pix.scaled(img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        )
                    else:
                        img_label.setText("Invalid")
                else:
                    img_label.setText("Not found")
            else:
                img_label.setText("No image")

            self.table.setCellWidget(r, 6, img_label)


# ---------------------------
# MAIN WINDOW (SUMMARY)
# ---------------------------
class TotalDormsWindow(QWidget):
    def __init__(self, owner_id):
        super().__init__()
        self.setWindowTitle("Total Dorms - StaySmart")
        self.setMinimumSize(1050, 700)

        self.db = DatabaseManager()
        self.host_id = owner_id

        self._win_total = None
        self._win_avail = None
        self._win_occ = None

        self._fonts()
        self._build_ui()
        self._apply_styles()
        self.load_summary_data()

    def _fonts(self):
        self.font_title = QFont("Segoe UI", 20, QFont.Bold)
        self.font_section = QFont("Segoe UI", 12, QFont.DemiBold)
        self.font_normal = QFont("Segoe UI", 10)

    def go_back(self):
        from owner_dashboard import OwnerDashboardWindow
        self.dashboard = OwnerDashboardWindow(owner_id=self.host_id)
        self.dashboard.show()
        self.close()

    def load_summary_data(self):
        stats = self.db.get_owner_stats(self.host_id)

        self.lbl_total_count.setText(str(stats["total_dorms"]))
        avail_count = len(self.db.get_available_rooms_host(self.host_id))
        self.lbl_avail_count.setText(str(avail_count))
        self.lbl_occ_count.setText(str(stats["current_occupants"]))

        self.summary_txt.setText(f"""
Total Dorms: {stats['total_dorms']}
Occupied Rooms: {stats['current_occupants']}
Available Rooms: {avail_count}
Occupancy Rate: {stats['occupancy_rate']}%
        """.strip())

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(18)

        # HEADER
        header = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setFixedWidth(80)
        btn_back.clicked.connect(self.go_back)
        header.addWidget(btn_back)

        title = QLabel("Total Dorms")
        title.setFont(self.font_title)
        header.addWidget(title)
        header.addStretch()

        btn_refresh = QPushButton("Refresh Data")
        btn_refresh.clicked.connect(self.load_summary_data)
        header.addWidget(btn_refresh)
        root.addLayout(header)

        # STAT CARDS
        cards_layout = QHBoxLayout()

        self.card_total, self.lbl_total_count = self._create_card("Total Dorms", "Loading...")
        self.card_total.mousePressEvent = lambda e: self.open_total_dorms()

        self.card_avail, self.lbl_avail_count = self._create_card("Available Rooms", "Loading...")
        self.card_avail.mousePressEvent = lambda e: self.open_available_rooms()

        self.card_occ, self.lbl_occ_count = self._create_card("Occupied Rooms", "Loading...")
        self.card_occ.mousePressEvent = lambda e: self.open_occupied_rooms()

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_avail)
        cards_layout.addWidget(self.card_occ)
        root.addLayout(cards_layout)

        # BOTTOM SECTION
        bottom = QHBoxLayout()

        qa_frame = QFrame()
        qa_frame.setObjectName("panel")
        qa_lay = QVBoxLayout(qa_frame)
        qa_lay.addWidget(QLabel("Quick Actions", font=self.font_section))

        btn_add = QPushButton("Add New Dorm")
        btn_add.setStyleSheet("background:#0f7a3a; color:white; padding:8px; font-weight:bold;")
        btn_add.clicked.connect(self.open_total_dorms)
        qa_lay.addWidget(btn_add)
        qa_lay.addStretch()
        bottom.addWidget(qa_frame, 30)

        rec_frame = QFrame()
        rec_frame.setObjectName("panel")
        rec_lay = QVBoxLayout(rec_frame)
        rec_lay.addWidget(QLabel("Recent Activities", font=self.font_section))
        self.list_activity = QListWidget()
        self.list_activity.addItems(["System connected to Database.", "Real-time stats loaded."])
        rec_lay.addWidget(self.list_activity)
        bottom.addWidget(rec_frame, 40)

        sum_frame = QFrame()
        sum_frame.setObjectName("panel")
        sum_lay = QVBoxLayout(sum_frame)
        sum_lay.addWidget(QLabel("Summary", font=self.font_section))
        self.summary_txt = QLabel("Loading...")
        sum_lay.addWidget(self.summary_txt)
        sum_lay.addStretch()
        bottom.addWidget(sum_frame, 30)

        root.addLayout(bottom)

    def _create_card(self, title, value):
        f = QFrame()
        f.setObjectName("infoCard")
        f.setCursor(Qt.PointingHandCursor)
        f.setFixedHeight(100)

        l = QVBoxLayout(f)
        t = QLabel(title)
        t.setFont(self.font_section)

        v = QLabel(value)
        v.setFont(QFont("Segoe UI", 22, QFont.Bold))
        v.setStyleSheet("color:#0f3f2b;")

        l.addWidget(t)
        l.addStretch()
        l.addWidget(v, alignment=Qt.AlignRight)
        return f, v

    def open_total_dorms(self):
        self._win_total = TotalDormsDetailWindow(owner_id=self.host_id)
        self._win_total.show()

    def open_available_rooms(self):
        self._win_avail = AvailableRoomsWindow(owner_id=self.host_id)
        self._win_avail.show()

    def open_occupied_rooms(self):
        self._win_occ = OccupiedRoomsWindow(owner_id=self.host_id)
        self._win_occ.show()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background:#f5f7f8; color:#222; font-family:"Segoe UI"; }
            QFrame#infoCard { background:white; border-radius:12px; border:2px solid #0f7a3a; }
            QFrame#infoCard:hover { background:#e8f5e9; }
            QFrame#panel { background:white; border-radius:12px; border:1px solid #ddd; }
            QPushButton { background:#e0e0e0; border-radius:6px; padding:6px 12px; }
            QPushButton:hover { background:#d0d0d0; }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TotalDormsWindow(owner_id=1)
    win.show()
    sys.exit(app.exec_())
