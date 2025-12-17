# add_dorm.py
import sys
import os
import shutil         
from functools import partial
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QCheckBox, QFileDialog, QListWidget,
    QSpinBox, QScrollArea, QFrame, QMessageBox, QDoubleSpinBox, QGroupBox
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt
import mysql.connector

# ---------------------------
#   Database config (edit)
# ---------------------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",      
    "database": "staysmartdb",
    "port": 3306,
    "raise_on_warnings": True
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "dorm_images")


def get_db_conn():
    return mysql.connector.connect(**DB_CONFIG)


class AddDormForm(QWidget):
    def __init__(self, owner_id=1):
        """
        owner_id: by default 1 for testing. Replace with your logged-in owner's user_id.
        """
        super().__init__()
        self.owner_id = owner_id  
        self.amenities_master = [] 
        self.selected_image_paths = []   
        self.room_widgets = []

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        self.setWindowTitle("Add New Dorm (Save to DB)")
        self.resize(900, 800)
        self.setMinimumSize(800, 700)

        self._setup_style()
        self._build_ui()
        self.load_amenities_from_db()

    def _setup_style(self):
        self.setStyleSheet("""
            * { font-family: 'Poppins', Arial; }
            QLabel { font-size: 13px; }
            QLineEdit, QComboBox, QListWidget, QSpinBox, QDoubleSpinBox {
                border: 1px solid #1B5E20; border-radius: 6px; padding: 6px; background: white;
            }
            QPushButton { padding: 6px 12px; border-radius: 8px; }
        """)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#F7F7F7"))
        self.setPalette(palette)

    def _build_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        self.setLayout(main_layout)

        title = QLabel("Add Dorm (database-backed)")
        title.setFont(QFont("Poppins", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(12)
        form_grid.setVerticalSpacing(10)
        form_grid.setColumnStretch(0, 1)
        form_grid.setColumnStretch(1, 3)

        # Dorm name
        self.name_input = QLineEdit()
        form_grid.addWidget(QLabel("Dorm name *"), 0, 0)
        form_grid.addWidget(self.name_input, 0, 1)

        self.location_input = QLineEdit()
        form_grid.addWidget(QLabel("Address / Location *"), 1, 0)
        form_grid.addWidget(self.location_input, 1, 1)

        latlon_layout = QHBoxLayout()
        self.lat_input = QDoubleSpinBox()
        self.lat_input.setRange(-90.0, 90.0)
        self.lat_input.setDecimals(7)
        self.lat_input.setSingleStep(0.000001)
        self.long_input = QDoubleSpinBox()
        self.long_input.setRange(-180.0, 180.0)
        self.long_input.setDecimals(7)
        self.long_input.setSingleStep(0.000001)
        latlon_layout.addWidget(QLabel("Latitude:"))
        latlon_layout.addWidget(self.lat_input)
        latlon_layout.addSpacing(12)
        latlon_layout.addWidget(QLabel("Longitude:"))
        latlon_layout.addWidget(self.long_input)
        form_grid.addWidget(QLabel("Coordinates (optional)"), 2, 0)
        form_grid.addLayout(latlon_layout, 2, 1)

        self.dorm_type_box = QComboBox()
        self.dorm_type_box.addItems(["BED_SPACER", "APARTMENT", "MIXED"])
        form_grid.addWidget(QLabel("Dorm type *"), 3, 0)
        form_grid.addWidget(self.dorm_type_box, 3, 1)

        self.status_box = QComboBox()
        self.status_box.addItems(["OPEN", "FULL", "UNDER_MAINTENANCE"])
        form_grid.addWidget(QLabel("Status *"), 4, 0)
        form_grid.addWidget(self.status_box, 4, 1)

        self.no_rooms_label = QLabel("0")
        form_grid.addWidget(QLabel("No. of rooms (calculated)"), 5, 0)
        form_grid.addWidget(self.no_rooms_label, 5, 1, alignment=Qt.AlignLeft)

        self.amenities_box = QGroupBox("Amenities (these are general; rooms can also have amenities)")
        self.amenities_layout = QVBoxLayout()
        self.amenities_box.setLayout(self.amenities_layout)
        form_grid.addWidget(self.amenities_box, 6, 0, 1, 2)

        main_layout.addLayout(form_grid)

        rooms_title_layout = QHBoxLayout()
        rooms_title_layout.addWidget(QLabel("Rooms (add at least 1)"))
        add_room_btn = QPushButton("Add Room")
        add_room_btn.clicked.connect(self.add_room_inline)
        rooms_title_layout.addStretch()
        rooms_title_layout.addWidget(add_room_btn)
        main_layout.addLayout(rooms_title_layout)

        self.rooms_area = QVBoxLayout()
        self.rooms_area.setSpacing(8)

        rooms_container = QScrollArea()
        rooms_widget = QWidget()
        rooms_widget.setLayout(self.rooms_area)
        rooms_container.setWidgetResizable(True)
        rooms_container.setWidget(rooms_widget)
        rooms_container.setFixedHeight(300)
        main_layout.addWidget(rooms_container)

        images_layout = QHBoxLayout()
        self.images_list = QListWidget()
        images_layout.addWidget(self.images_list)
        upload_btn = QPushButton("Upload Images")
        upload_btn.clicked.connect(self.upload_images)
        images_layout.addWidget(upload_btn)
        main_layout.addLayout(images_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        save_btn = QPushButton("Save Dorm")
        save_btn.clicked.connect(self.save_to_db)
        save_btn.setStyleSheet("background-color: #1B5E20; color: white;")
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

        self.add_room_inline()

    # ---------------------------
    #   Amenity loading
    # ---------------------------
    def load_amenities_from_db(self):
        """
        Loads amenities from the amenities table and creates checkboxes.
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute("SELECT amenity_id, label FROM amenities ORDER BY amenity_id;")
            rows = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "DB Error", f"Could not load amenities: {e}")
            rows = []

        # clear existing
        for i in reversed(range(self.amenities_layout.count())):
            w = self.amenities_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.amenities_master = []
        for amen_id, label in rows:
            cb = QCheckBox(label)
            cb.amen_id = amen_id
            self.amenities_layout.addWidget(cb)
            self.amenities_master.append(cb)

    # ---------------------------
    #   Rooms UI helpers
    # ---------------------------
    def add_room_inline(self, prefill=None):
        """
        Create an inline room widget group.
        prefill: optional dict {room_no, room_type, capacity, price, amenities_ids}
        """
        # container frame
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frm_layout = QGridLayout()
        frame.setLayout(frm_layout)

        # room_no, room_type, capacity, price
        room_no_input = QLineEdit()
        room_type_box = QComboBox()
        room_type_box.addItems(["BED_SPACER", "APARTMENT"])  # match DB enum for rooms
        capacity_spin = QSpinBox()
        capacity_spin.setRange(1, 100)
        price_spin = QDoubleSpinBox()
        price_spin.setRange(0, 9999999)
        price_spin.setDecimals(2)

        frm_layout.addWidget(QLabel("Room No *"), 0, 0)
        frm_layout.addWidget(room_no_input, 0, 1)
        frm_layout.addWidget(QLabel("Room Type *"), 0, 2)
        frm_layout.addWidget(room_type_box, 0, 3)
        frm_layout.addWidget(QLabel("Capacity *"), 1, 0)
        frm_layout.addWidget(capacity_spin, 1, 1)
        frm_layout.addWidget(QLabel("Monthly Price *"), 1, 2)
        frm_layout.addWidget(price_spin, 1, 3)

        room_amen_group = QGroupBox("Room amenities (optional)")
        ra_layout = QHBoxLayout()
        room_amen_group.setLayout(ra_layout)

        room_amen_cbs = []
        for master_cb in self.amenities_master:
            cb = QCheckBox(master_cb.text())
            cb.amen_id = getattr(master_cb, "amen_id", None)
            cb.setChecked(False)
            room_amen_cbs.append(cb)
            ra_layout.addWidget(cb)
        frm_layout.addWidget(room_amen_group, 2, 0, 1, 4)

        remove_btn = QPushButton("Remove Room")
        remove_btn.clicked.connect(partial(self.remove_room, frame))
        frm_layout.addWidget(remove_btn, 3, 3, alignment=Qt.AlignRight)

        self.rooms_area.addWidget(frame)
        self.room_widgets.append({
            "frame": frame,
            "room_no": room_no_input,
            "room_type": room_type_box,
            "capacity": capacity_spin,
            "price": price_spin,
            "amenities": room_amen_cbs
        })

        if prefill:
            room_no_input.setText(str(prefill.get("room_no", "")))
            room_type_box.setCurrentText(prefill.get("room_type", "BED_SPACER"))
            capacity_spin.setValue(prefill.get("capacity", 1))
            price_spin.setValue(prefill.get("price", 0.0))
            sel_ids = set(prefill.get("amenities_ids", []))
            for cb in room_amen_cbs:
                cb.setChecked(cb.amen_id in sel_ids)

        self._recalc_room_count()

    def remove_room(self, frame):

        for idx, r in enumerate(self.room_widgets):
            if r["frame"] is frame:
                # remove widget
                r["frame"].setParent(None)
                del self.room_widgets[idx]
                break
        self._recalc_room_count()

    def _recalc_room_count(self):
        count = len(self.room_widgets)
        self.no_rooms_label.setText(str(count))

    def upload_images(self):
        """
        Select images, copy them into uploads/dorm_images/, and remember
        their RELATIVE paths so they can be loaded on any machine.
        """
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        if not files:
            return

        for src_path in files:
            if not os.path.isfile(src_path):
                continue

            base_name = os.path.basename(src_path)
            name, ext = os.path.splitext(base_name)
            dest_path = os.path.join(UPLOAD_DIR, base_name)
            i = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(UPLOAD_DIR, f"{name}_{i}{ext}")
                i += 1

            try:
                shutil.copy(src_path, dest_path)
            except Exception as e:
                QMessageBox.warning(self, "Image Copy Error", f"Could not copy {src_path}:\n{e}")
                continue

            rel_path = os.path.relpath(dest_path, BASE_DIR).replace(os.sep, "/")

            if rel_path not in self.selected_image_paths:
                self.selected_image_paths.append(rel_path)
                self.images_list.addItem(rel_path)

    # ---------------------------
    #   Validation
    # ---------------------------
    def validate(self):
        if not self.name_input.text().strip():
            return False, "Dorm name is required."
        if not self.location_input.text().strip():
            return False, "Address / location is required."
        if len(self.room_widgets) == 0:
            return False, "Add at least one room."

        seen_room_nos = set()
        for r in self.room_widgets:
            rn = r["room_no"].text().strip()
            if not rn:
                return False, "Each room must have a room no."
            if rn in seen_room_nos:
                return False, f"Duplicate room no: {rn}"
            seen_room_nos.add(rn)
        return True, None

    def save_to_db(self):
        ok, msg = self.validate()
        if not ok:
            QMessageBox.warning(self, "Validation error", msg)
            return

        dorm_name = self.name_input.text().strip()
        location_text = self.location_input.text().strip()
        latitude = None if self.lat_input.value() == 0.0 and not self.lat_input.text() else self.lat_input.value()
        longitude = None if self.long_input.value() == 0.0 and not self.long_input.text() else self.long_input.value()
        dorm_type = self.dorm_type_box.currentText()
        status = self.status_box.currentText()
        no_of_rooms = len(self.room_widgets)

        rooms_data = []
        for r in self.room_widgets:
            rm_no = r["room_no"].text().strip()
            rm_type = r["room_type"].currentText()
            rm_capacity = int(r["capacity"].value())
            rm_price = float(r["price"].value())

            amen_ids = [
                cb.amen_id for cb in r["amenities"]
                if cb.isChecked() and getattr(cb, "amen_id", None) is not None
            ]
            rooms_data.append({
                "room_no": rm_no,
                "room_type": rm_type,
                "capacity": rm_capacity,
                "price_monthly": rm_price,
                "amenities": amen_ids
            })

        images = list(self.selected_image_paths)

        try:
            conn = get_db_conn()
            cur = conn.cursor()

            # Insert dorm
            insert_dorm_q = """
                INSERT INTO dorms (owner_id, dorm_name, location_text, latitude, longitude, dorm_type, no_of_rooms, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(insert_dorm_q, (
                self.owner_id, dorm_name, location_text,
                latitude if latitude is not None else None,
                longitude if longitude is not None else None,
                dorm_type, no_of_rooms, status
            ))
            dorm_id = cur.lastrowid

            # Insert rooms (and room_amenities)
            insert_room_q = """
                INSERT INTO rooms (dorm_id, room_no, room_type, capacity, price_monthly, is_available)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            insert_room_amen_q = "INSERT INTO room_amenities (room_id, amenity_id) VALUES (%s, %s)"

            for rd in rooms_data:
                cur.execute(insert_room_q, (
                    dorm_id, rd["room_no"], rd["room_type"],
                    rd["capacity"], rd["price_monthly"], 1
                ))
                room_id = cur.lastrowid
                # insert amenities
                for aid in rd["amenities"]:
                    cur.execute(insert_room_amen_q, (room_id, aid))

            # insert images into dorm_images
            if images:
                insert_image_q = "INSERT INTO dorm_images (dorm_id, file_path) VALUES (%s, %s)"
                for fp in images:
                    cur.execute(insert_image_q, (dorm_id, fp))

            conn.commit()
            cur.close()
            conn.close()

        except mysql.connector.Error as e:
            try:
                conn.rollback()
            except:
                pass
            QMessageBox.critical(self, "Database Error", f"Failed to save dorm: {e}")
            return
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            QMessageBox.critical(self, "Error", f"Unexpected error: {e}")
            return

        QMessageBox.information(self, "Saved", "Dorm and rooms successfully saved to database.")
        self.close()


# ---------------------------
#   Main
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = AddDormForm(owner_id=1)
    window.show()
    sys.exit(app.exec_())
