import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self):
        self.config = {
            "host": "localhost",
            "user": "root",
            "password": "",
            "database": "staysmartdb"
        }

    def get_connection(self):
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            print("DB Connection Error:", e)
            return None

    def fetchall(self, sql, params=None):
        conn = self.get_connection()
        if not conn or not conn.is_connected():
            return []
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or {})
        rows = cur.fetchall()
        conn.close()
        return rows

    def fetchone(self, sql, params=None):
        conn = self.get_connection()
        if not conn or not conn.is_connected():
            return None
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or {})
        row = cur.fetchone()
        conn.close()
        return row

    def execute(self, sql, params=None):
        conn = self.get_connection()
        if not conn or not conn.is_connected():
            return None
        cur = conn.cursor()
        cur.execute(sql, params or {})
        conn.commit()
        last_id = cur.lastrowid
        conn.close()
        return last_id

     =========================================================
     AUTH / SIGNUP / LOGIN
    # =========================================================

    def create_user(self, role, fullname, username, email, contact_no, password_hash):
        sql = """
            INSERT INTO users(role, fullname, username, email, contact_no, password_hash)
            VALUES (%s,%s,%s,%s,%s,%s)
        """
        return self.execute(sql, (role, fullname, username, email, contact_no, password_hash))

    def create_owner_profile(self, owner_id, display_name=None, messenger_link=None, facebook_link=None):
        sql = """
            INSERT INTO owner_profiles(owner_id, display_name, messenger_link, facebook_link)
            VALUES (%s,%s,%s,%s)
        """
        self.execute(sql, (owner_id, display_name, messenger_link, facebook_link))

    def create_tenant_profile(self, tenant_id, first_name, last_name, gender,
                              guardian_fullname, guardian_contact, guardian_email,
                              profile_picture_url=None, agreed_terms=False):
        sql = """
            INSERT INTO tenant_profiles(
                tenant_id, first_name, last_name, gender,
                guardian_fullname, guardian_contact, guardian_email,
                profile_picture_url, agreed_terms
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        self.execute(sql, (
            tenant_id, first_name, last_name, gender,
            guardian_fullname, guardian_contact, guardian_email,
            profile_picture_url, int(agreed_terms)
        ))

    def get_user_by_username(self, username):
        sql = "SELECT * FROM users WHERE username=%s AND is_active=1"
        return self.fetchone(sql, (username,))

    # =========================================================
    # OWNER DASHBOARD (TotalDorms.py etc.)
    # =========================================================

    def get_owner_stats(self, owner_id):
        stats = {
            "total_dorms": 0,
            "current_occupants": 0,
            "pending_requests": 0,
            "monthly_earnings": 0,
            "active_dorms": 0,
            "maintenance_dorms": 0,
            "occupancy_rate": 0
        }

        # total dorms
        row = self.fetchone(
            "SELECT COUNT(*) AS cnt FROM dorms WHERE owner_id=%s",
            (owner_id,)
        )
        stats["total_dorms"] = row["cnt"] if row else 0

        # active occupants (rentals)
        row = self.fetchone("""
            SELECT COUNT(*) AS cnt
            FROM rentals rr
            JOIN rooms r ON rr.room_id=r.room_id
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE d.owner_id=%s
              AND rr.status IN ('ACTIVE','EXTENDED','ENDING')
        """, (owner_id,))
        stats["current_occupants"] = row["cnt"] if row else 0

        row = self.fetchone("""
            SELECT COUNT(*) AS cnt
            FROM rental_applications ra
            JOIN dorms d ON ra.dorm_id=d.dorm_id
            WHERE d.owner_id=%s AND ra.action_status='WAITING'
        """, (owner_id,))
        stats["pending_requests"] = row["cnt"] if row else 0

        now = datetime.now()
        row = self.fetchone("""
            SELECT COALESCE(SUM(amount),0) AS total
            FROM transactions
            WHERE owner_id=%s AND status='PAID'
              AND MONTH(transaction_date)=%s
              AND YEAR(transaction_date)=%s
        """, (owner_id, now.month, now.year))
        stats["monthly_earnings"] = float(row["total"]) if row else 0

        row = self.fetchone("""
            SELECT
              SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) AS active_cnt,
              SUM(CASE WHEN status='UNDER_MAINTENANCE' THEN 1 ELSE 0 END) AS maint_cnt
            FROM dorms
            WHERE owner_id=%s
        """, (owner_id,))
        if row:
            stats["active_dorms"] = row["active_cnt"] or 0
            stats["maintenance_dorms"] = row["maint_cnt"] or 0

        cap_row = self.fetchone("""
            SELECT COALESCE(SUM(capacity),0) AS cap
            FROM rooms r JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE d.owner_id=%s
        """, (owner_id,))
        total_capacity = cap_row["cap"] if cap_row and cap_row["cap"] else 1
        if total_capacity > 0:
            stats["occupancy_rate"] = int((stats["current_occupants"] / total_capacity) * 100)

        return stats

    def get_recent_reservations(self, owner_id, limit=5):
        sql = """
            SELECT ra.submitted_at AS created_at,
                   u.fullname AS full_name,
                   r.room_no AS room_name,
                   ra.action_status AS status
            FROM rental_applications ra
            JOIN users u ON ra.tenant_id=u.user_id
            JOIN rooms r ON ra.room_id=r.room_id
            JOIN dorms d ON ra.dorm_id=d.dorm_id
            WHERE d.owner_id=%s
            ORDER BY ra.submitted_at DESC
            LIMIT %s
        """
        return self.fetchall(sql, (owner_id, limit))

    def get_host_properties(self, owner_id):
        sql = """
            SELECT d.dorm_id AS property_id,
                   d.dorm_name AS name,
                   d.location_text AS address,
                   COUNT(r.room_id) AS room_count
            FROM dorms d
            LEFT JOIN rooms r ON d.dorm_id=r.dorm_id
            WHERE d.owner_id=%s
            GROUP BY d.dorm_id
        """
        return self.fetchall(sql, (owner_id,))

    def add_property(self, owner_id, name, address, dorm_type='MIXED', status='OPEN'):
        sql = """
            INSERT INTO dorms(owner_id, dorm_name, location_text, dorm_type, status)
            VALUES (%s,%s,%s,%s,%s)
        """
        return self.execute(sql, (owner_id, name, address, dorm_type, status))

    def update_property(self, dorm_id, name, address, dorm_type='MIXED', status='OPEN'):
        sql = """
            UPDATE dorms
            SET dorm_name=%s, location_text=%s, dorm_type=%s, status=%s
            WHERE dorm_id=%s
        """
        self.execute(sql, (name, address, dorm_type, status, dorm_id))
        return True

    def delete_property(self, dorm_id):
        self.execute("DELETE FROM dorms WHERE dorm_id=%s", (dorm_id,))
        return True

    def get_available_rooms_host(self, owner_id):
        sql = """
            SELECT r.room_id,
            r.room_no AS room_name,
            r.room_type AS type,
            r.capacity,
            r.price_monthly AS price,
            d.dorm_name AS dorm_name,
            d.dorm_id AS dorm_id        
        FROM rooms r
        JOIN dorms d ON r.dorm_id=d.dorm_id
        WHERE d.owner_id=%s AND r.is_available=1

        """
        return self.fetchall(sql, (owner_id,))

    def get_occupied_rooms_host(self, owner_id):
        sql = """
            SELECT r.room_id,
            r.room_no AS room_name,
            r.room_type AS type,
            COALESCE(ad.tenant_fullname, u.fullname) AS tenant_name,
            rr.start_date AS check_in_date,
            rr.end_date AS check_out_date,
            d.dorm_name AS dorm_name,
            d.dorm_id AS dorm_id             
        ...

            FROM rentals rr
            JOIN rooms r ON rr.room_id=r.room_id
            JOIN dorms d ON r.dorm_id=d.dorm_id
            JOIN users u ON rr.tenant_id=u.user_id

            LEFT JOIN rental_applications ra 
                ON ra.tenant_id = rr.tenant_id
                AND ra.room_id = rr.room_id
                AND ra.action_status='APPROVED'

            LEFT JOIN application_details ad 
                ON ad.application_id = ra.application_id

            WHERE d.owner_id=%s
            AND rr.status IN ('ACTIVE','EXTENDED','ENDING')
            ORDER BY rr.start_date DESC
        """
        return self.fetchall(sql, (owner_id,))


    def get_pending_requests(self, owner_id):
        sql = """
            SELECT ra.application_id AS request_id,
                COALESCE(ad.tenant_fullname, u.fullname) AS applicant,
                d.dorm_name AS dorm,
                r.room_no AS room_name,
                r.room_type,
                ra.submitted_at,
                ra.action_status AS status
            FROM rental_applications ra
            JOIN users u ON ra.tenant_id=u.user_id
            LEFT JOIN application_details ad ON ad.application_id = ra.application_id
            JOIN dorms d ON ra.dorm_id=d.dorm_id
            JOIN rooms r ON ra.room_id=r.room_id
            WHERE d.owner_id=%s AND ra.action_status='WAITING'
            ORDER BY ra.submitted_at DESC
        """
        return self.fetchall(sql, (owner_id,))



    def approve_request(self, application_id):
        self.execute("""
            UPDATE rental_applications
            SET action_status='APPROVED', reviewed_at=NOW()
            WHERE application_id=%s
        """, (application_id,))

        row = self.fetchone("""
            SELECT
                rr.rental_id,
                rr.start_date,
                r.price_monthly
            FROM rentals rr
            JOIN rooms r ON rr.room_id = r.room_id
            WHERE rr.application_id = %s
            ORDER BY rr.rental_id DESC
            LIMIT 1
        """, (application_id,))

        if not row:
            return True

        rental_id = row["rental_id"]
        room_price = row["price_monthly"]
        start_date = row["start_date"]

        from datetime import timedelta


        due_date = start_date + timedelta(days=30)

        self.create_monthly_payment(
            rental_id=rental_id,
            due_date=due_date,
            amount_due=room_price
        )

        return True



    def get_recommended_rooms(self, limit=5):
        sql = """
            SELECT r.room_id, d.dorm_name AS property_name, d.location_text AS address,
                r.room_no AS room_name, r.capacity, r.price_monthly, r.room_type
            FROM rooms r
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE r.is_available=1 AND d.status='OPEN'
            ORDER BY RAND()
            LIMIT %s
        """
        rooms = self.fetchall(sql, (limit,))

        for room in rooms:
            room["distance_meters"] = room.get("distance_meters") or room.get("distance") or None
            room["price"] = room.get("price_monthly")
            room["name"] = f"{room['property_name']} - {room['room_name']}"

        return rooms  

    def get_nearby_rooms(self, limit=5):
        sql = """
            SELECT r.room_id, d.dorm_name AS property_name, d.location_text AS address,
                r.room_no AS room_name, r.capacity, r.price_monthly, r.room_type
            FROM rooms r
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE r.is_available=1 AND d.status='OPEN'
            ORDER BY d.created_at DESC
            LIMIT %s
        """
        rooms = self.fetchall(sql, (limit,))

        for room in rooms:
            room["distance_meters"] = room.get("distance_meters") or room.get("distance") or None
            room["price"] = room.get("price_monthly")
            room["name"] = f"{room['property_name']} - {room['room_name']}"

        return rooms 

    def get_all_rooms(self, search_text="", capacity_filter="Any"):
        sql = """
            SELECT
              r.room_id,
              d.dorm_id,                 
              d.owner_id AS host_id,    
              d.dorm_name AS property_name,
              d.location_text AS address,
              r.room_no AS room_name,
              r.capacity,
              r.price_monthly AS price_monthly,
              r.room_type,
              u.fullname AS host_name,
              u.contact_no AS phone,
              u.email,
              op.facebook_link,
              op.messenger_link
            FROM rooms r
            JOIN dorms d ON r.dorm_id=d.dorm_id
            JOIN users u ON d.owner_id=u.user_id
            LEFT JOIN owner_profiles op ON op.owner_id=u.user_id
            WHERE r.is_available=1 AND d.status='OPEN'
        """
        params = []

        if search_text:
            sql += " AND (d.dorm_name LIKE %s OR d.location_text LIKE %s OR r.room_no LIKE %s)"
            wildcard = f"%{search_text}%"
            params.extend([wildcard, wildcard, wildcard])

        if capacity_filter != "Any":
            if capacity_filter == "4+":
                sql += " AND r.capacity >= 4"
            else:
                sql += " AND r.capacity = %s"
                params.append(int(capacity_filter))

        rooms = self.fetchall(sql, tuple(params))

        for room in rooms:
            room["name"] = f"{room['property_name']} - {room['room_name']}"
            room["distance"] = None  
            room["price"] = room["price_monthly"]

        return rooms

    # ---------------- Reservations Window ----------------

    def get_user_reservations(self, tenant_id):
        sql = """
            SELECT
              ra.application_id,
              d.dorm_name AS property_name,
              r.room_no AS room_name,
              ra.action_status AS status,
              ra.submitted_at AS created_at
            FROM rental_applications ra
            JOIN dorms d ON ra.dorm_id=d.dorm_id
            JOIN rooms r ON ra.room_id=r.room_id
            WHERE ra.tenant_id=%s
            ORDER BY ra.submitted_at DESC
        """
        return self.fetchall(sql, (tenant_id,))

    # ---------------- Payments Window ----------------

    def get_user_payments(self, tenant_id):
        sql = """
            SELECT
                p.payment_id,
                p.due_date,
                p.amount_due,
                p.amount_paid,
                CASE
                    WHEN p.status = 'PAID' THEN 'Paid'
                    WHEN p.status = 'OVERDUE' THEN 'Overdue'
                    ELSE 'Due'
                END AS status,
                p.paid_at AS payment_date,
                r.room_no AS room_name,
                d.dorm_name AS property_name,
                'Rent' AS payment_type,
                p.rental_id
            FROM payments p
            JOIN rentals rr ON p.rental_id = rr.rental_id
            JOIN rooms r ON rr.room_id = r.room_id
            JOIN dorms d ON r.dorm_id = d.dorm_id
            WHERE rr.tenant_id = %s
            ORDER BY p.due_date ASC
        """
        return self.fetchall(sql, (tenant_id,))

    def get_recently_viewed(self, tenant_id):
        """
        Safe recently viewed:
        - If table doesn't exist yet, return empty list instead of crashing.
        """
        sql = """
            SELECT rv.room_id, rv.viewed_at,
                r.room_no AS room_name, d.dorm_name AS property_name
            FROM recently_viewed rv
            JOIN rooms r ON rv.room_id=r.room_id
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE rv.user_id=%s
            ORDER BY rv.viewed_at DESC LIMIT 5
        """
        try:
            return self.fetchall(sql, (tenant_id,))
        except Exception as e:
            # Table doesn't exist yet -> return no items instead of error
            if "recently_viewed" in str(e):
                return []
            raise


    # =========================================================
    # RENTING FORM
    # =========================================================
    def create_rental_application(
        self,
        tenant_id,
        dorm_id,
        room_id,
        notes=None,
        tenant_fullname=None,
        tenant_email=None,
        tenant_phone=None,
        tenant_gender=None
    ):
        app_id = self.execute("""
            INSERT INTO rental_applications(tenant_id, dorm_id, room_id)
            VALUES (%s,%s,%s)
        """, (tenant_id, dorm_id, room_id))

        self.execute("""
            INSERT INTO application_details(
                application_id,
                additional_notes,
                tenant_fullname,
                tenant_email,
                tenant_phone,
                tenant_gender
            )
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            app_id,
            notes,
            tenant_fullname,
            tenant_email,
            tenant_phone,
            tenant_gender
        ))

        return app_id


    # =========================================================
    # PAYMENTS / ADMIN UTILITIES
    # =========================================================

    def create_monthly_payment(self, rental_id, due_date, amount_due):
        sql = """
            INSERT INTO payments (rental_id, due_date, amount_due, amount_paid, status)
            VALUES (%s, %s, %s, 0, 'PENDING')
        """
        return self.execute(sql, (rental_id, due_date, amount_due))



    def mark_payment_paid(self, payment_id, amount_paid=None):
        if amount_paid is None:
            row = self.fetchone(
                "SELECT amount_due FROM payments WHERE payment_id=%s",
                (payment_id,)
            )
            amount_paid = row["amount_due"] if row else 0

        self.execute("""
            UPDATE payments
            SET amount_paid=%s,
                status='PAID',
                paid_at=NOW()
            WHERE payment_id=%s
        """, (amount_paid, payment_id))

        return True

    
    def mark_overdue_payments(self):
        sql = """
            UPDATE payments
            SET status = 'OVERDUE'
            WHERE due_date < CURDATE()
            AND status = 'DUE'
        """
        self.execute(sql)
  
    def get_current_occupants(self, owner_id, search_text=""):
        sql = """
            SELECT
                rr.rental_id AS rental_id,
                u.user_id AS tenant_id,
                COALESCE(
                    CONCAT(tp.first_name, ' ', tp.last_name),
                    u.fullname
                ) AS tenant_name,
                u.contact_no AS tenant_phone,
                d.dorm_name AS dorm_name,
                r.room_no AS room_no,
                rr.start_date,
                rr.status
            FROM rentals rr
            JOIN users u ON rr.tenant_id = u.user_id
            LEFT JOIN tenant_profiles tp ON tp.tenant_id = u.user_id
            JOIN rooms r ON rr.room_id = r.room_id
            JOIN dorms d ON r.dorm_id = d.dorm_id
            WHERE d.owner_id = %s
            AND rr.status IN ('ACTIVE','EXTENDED','ENDING')
        """
        params = [owner_id]

        if search_text:
            sql += """
                AND COALESCE(
                    CONCAT(tp.first_name, ' ', tp.last_name),
                    u.fullname
                ) LIKE %s
            """
            params.append(f"%{search_text}%")

        sql += " ORDER BY rr.start_date DESC"
        return self.fetchall(sql, tuple(params))


    def get_owner_transaction_years(self, owner_id):
        """Distinct years with transactions for this owner."""
        rows = self.fetchall("""
            SELECT DISTINCT YEAR(transaction_date) AS yr
            FROM transactions
            WHERE owner_id=%s
            ORDER BY yr DESC
        """, (owner_id,))
        return [r["yr"] for r in rows if r["yr"]]

    def get_monthly_earnings_summary(self, owner_id, year, month):
        """
        Returns:
          paid (sum of PAID transactions this month),
          pending (sum of unpaid dues this month),
          collection_rate (paid/(paid+pending)).
        """
        # paid from transactions
        paid_row = self.fetchone("""
            SELECT COALESCE(SUM(amount),0) AS total
            FROM transactions
            WHERE owner_id=%s AND status='PAID'
              AND YEAR(transaction_date)=%s
              AND MONTH(transaction_date)=%s
        """, (owner_id, year, month))
        paid = float(paid_row["total"]) if paid_row else 0.0

        # pending from payments tied to this owner's rentals
        pending_row = self.fetchone("""
            SELECT COALESCE(SUM(p.amount_due - p.amount_paid),0) AS total
            FROM payments p
            JOIN rentals rr ON p.rental_id=rr.rental_id
            JOIN rooms r ON rr.room_id=r.room_id
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE d.owner_id=%s
              AND p.status IN ('PENDING','OVERDUE')
              AND YEAR(p.due_date)=%s
              AND MONTH(p.due_date)=%s
        """, (owner_id, year, month))
        pending = float(pending_row["total"]) if pending_row else 0.0

        denom = paid + pending
        rate = int((paid / denom) * 100) if denom > 0 else 0

        return {"paid": paid, "pending": pending, "collection_rate": rate}

    def get_monthly_revenue_series(self, owner_id, year):
        """Map month -> sum(amount) for PAID transactions in that year."""
        rows = self.fetchall("""
            SELECT MONTH(transaction_date) AS m,
                   COALESCE(SUM(amount),0) AS total
            FROM transactions
            WHERE owner_id=%s AND status='PAID'
              AND YEAR(transaction_date)=%s
            GROUP BY MONTH(transaction_date)
            ORDER BY m
        """, (owner_id, year))
        return {r["m"]: float(r["total"]) for r in rows}

    def get_recent_transactions(self, owner_id, year, limit=15):
        """Recent PAID transactions with tenant name."""
        return self.fetchall("""
            SELECT t.transaction_date,
                   u.fullname AS tenant_name,
                   t.amount,
                   t.status
            FROM transactions t
            JOIN users u ON t.tenant_id=u.user_id
            WHERE t.owner_id=%s
              AND YEAR(t.transaction_date)=%s
            ORDER BY t.transaction_date DESC
            LIMIT %s
        """, (owner_id, year, limit))

    # ---------------- Occupancy Chart ----------------

    def get_owner_occupancy_weekly(self, owner_id):
        """
        Last 7 days: count of ACTIVE/EXTENDED/ENDING rentals grouped by day.
        """
        rows = self.fetchall("""
            SELECT DAYNAME(rr.start_date) AS day_name,
                   COUNT(*) AS cnt
            FROM rentals rr
            JOIN rooms r ON rr.room_id=r.room_id
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE d.owner_id=%s
              AND rr.status IN ('ACTIVE','EXTENDED','ENDING')
              AND rr.start_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY DAYOFWEEK(rr.start_date), DAYNAME(rr.start_date)
            ORDER BY DAYOFWEEK(rr.start_date)
        """, (owner_id,))

        order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        mp = {r["day_name"]: r["cnt"] for r in rows}
        return [mp.get(d, 0) for d in order]

    def get_owner_occupancy_monthly(self, owner_id, year):
        """
        Current year: count of ACTIVE/EXTENDED/ENDING rentals grouped by month.
        """
        rows = self.fetchall("""
            SELECT MONTH(rr.start_date) AS m,
                   COUNT(*) AS cnt
            FROM rentals rr
            JOIN rooms r ON rr.room_id=r.room_id
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE d.owner_id=%s
              AND rr.status IN ('ACTIVE','EXTENDED','ENDING')
              AND YEAR(rr.start_date)=%s
            GROUP BY MONTH(rr.start_date)
            ORDER BY m
        """, (owner_id, year))

        mp = {r["m"]: r["cnt"] for r in rows}  # month -> count
        return [mp.get(i, 0) for i in range(1, 13)]

    def get_owner_occupancy_yearly(self, owner_id, years_back=4):
        """
        Last N years: count of ACTIVE/EXTENDED/ENDING rentals grouped by year.
        """
        rows = self.fetchall("""
            SELECT YEAR(rr.start_date) AS y,
                   COUNT(*) AS cnt
            FROM rentals rr
            JOIN rooms r ON rr.room_id=r.room_id
            JOIN dorms d ON r.dorm_id=d.dorm_id
            WHERE d.owner_id=%s
              AND rr.status IN ('ACTIVE','EXTENDED','ENDING')
            GROUP BY YEAR(rr.start_date)
            ORDER BY y DESC
            LIMIT %s
        """, (owner_id, years_back))

        rows = list(reversed(rows)) 
        labels = [str(r["y"]) for r in rows]
        values = [r["cnt"] for r in rows]
        return labels, values

    def end_rental_contract(self, rental_id):
        """
        Ends a rental contract:
        - set rentals.status = 'ENDED'
        - set rentals.end_date = today if not already set
        - set rooms.is_available = 1
        """
        # get rental + room info
        rental = self.fetchone("""
            SELECT rental_id, room_id
            FROM rentals
            WHERE rental_id=%s
        """, (rental_id,))

        if not rental:
            return False

        room_id = rental["room_id"]

        self.execute("""
            UPDATE rentals
            SET status='ENDED',
                end_date = COALESCE(end_date, CURDATE())
            WHERE rental_id=%s
        """, (rental_id,))

        self.execute("""
            UPDATE rooms
            SET is_available=1
            WHERE room_id=%s
        """, (room_id,))

        return True

    def get_dorm_main_image(self, dorm_id):
        """
        Returns the first image file_path for a dorm, or None if none.
        file_path is stored as a relative path like 'uploads/dorm_images/xxx.jpg'.
        """
        row = self.fetchone(
            "SELECT file_path FROM dorm_images WHERE dorm_id=%s LIMIT 1",
            (dorm_id,)
        )
        return row["file_path"] if row else None
    
    def submit_payment_request(self, tenant_id, rental_id, amount, proof_path):
        q = """
            INSERT INTO payment_requests (tenant_id, rental_id, amount, proof_image)
            VALUES (%s, %s, %s, %s)
        """
        self.execute(q, (tenant_id, rental_id, amount, proof_path))
        return True

    def get_pending_payment_requests(self, owner_id):
        q = """
            SELECT
                pr.request_id,
                u.fullname AS tenant_name,
                pr.amount,
                pr.proof_image,
                pr.rental_id
            FROM payment_requests pr
            JOIN rentals r ON pr.rental_id = r.rental_id
            JOIN rooms rm ON r.room_id = rm.room_id
            JOIN dorms d ON rm.dorm_id = d.dorm_id
            JOIN users u ON pr.tenant_id = u.user_id
            WHERE d.owner_id = %s
            AND pr.status = 'PENDING'
            ORDER BY pr.submitted_at ASC
        """
        return self.fetchall(q, (owner_id,))

    def user_has_active_reservation(self, user_id):
        """
        Returns True if tenant already has:
        - an ACTIVE rental, OR
        - a WAITING rental application
        """

        q1 = """
            SELECT 1
            FROM rentals
            WHERE tenant_id = %s
            AND status IN ('ACTIVE', 'EXTENDED', 'ENDING')
            LIMIT 1
        """
        if self.fetchone(q1, (user_id,)):
            return True

        q2 = """
            SELECT 1
            FROM rental_applications
            WHERE tenant_id = %s
            AND action_status = 'WAITING'
            LIMIT 1
        """
        if self.fetchone(q2, (user_id,)):
            return True

        return False

    def get_tenant_profile(self, tenant_id):
        sql = """
            SELECT
                tp.first_name,
                tp.last_name,
                tp.gender,
                tp.guardian_fullname AS guardian_name,
                tp.guardian_contact,
                tp.profile_picture_url AS photo_path,
                u.email,
                u.contact_no AS phone
            FROM tenant_profiles tp
            JOIN users u ON tp.tenant_id = u.user_id
            WHERE tp.tenant_id = %s
            LIMIT 1
        """
        return self.fetchone(sql, (tenant_id,))


    def review_payment(self, request_id, approve=True):
        status = "APPROVED" if approve else "REJECTED"
        q = """
            UPDATE payment_requests
            SET status=%s, reviewed_at=NOW()
            WHERE request_id=%s
        """
        self.execute(q, (status, request_id))
        return True



    def update_due_date(self, rental_id):
        q = "SELECT due_date FROM payments WHERE rental_id=%s"
        row = self.fetchone(q, (rental_id,))
        due = row["due_date"]

        next_month = due + timedelta(days=30)

        q2 = """
            UPDATE payments
            SET due_date=%s, status='PAID', is_overdue=0
            WHERE rental_id=%s
        """
        self.execute(q2, (next_month, rental_id))

    def check_overdue(self):
        sql = """
            UPDATE payments
            SET status = 'OVERDUE'
            WHERE due_date < CURDATE()
            AND status = 'DUE'
        """
        self.execute(sql)


    def has_pending_payment_request(self, tenant_id, rental_id):
        q = """
            SELECT 1
            FROM payment_requests
            WHERE tenant_id=%s
            AND rental_id=%s
            AND status='PENDING'
            LIMIT 1
        """
        row = self.fetchone(q, (tenant_id, rental_id))
        return row is not None

    def get_last_payment_rejection(self, tenant_id, rental_id):
        q = """
            SELECT remarks
            FROM payment_requests
            WHERE tenant_id=%s
            AND rental_id=%s
            AND status='REJECTED'
            ORDER BY reviewed_at DESC
            LIMIT 1
        """
        row = self.fetchone(q, (tenant_id, rental_id))
        return row["remarks"] if row else None

    def cancel_reservation(self, reservation_id):
        """
        Cancels a pending/waiting reservation application
        """
        q = """
            UPDATE rental_applications
            SET action_status = 'CANCELLED'
            WHERE application_id = %s
            AND action_status IN ('PENDING', 'WAITING')
        """
        self.execute(q, (reservation_id,))
    
    def save_tenant_profile(
        self,
        tenant_id,
        first_name,
        last_name,
        gender,
        guardian_name,
        guardian_contact,
        guardian_email,
        photo_path,
        agreed_terms
    ):
        sql = """
            INSERT INTO tenant_profiles
            (
                tenant_id, first_name, last_name, gender,
                guardian_fullname, guardian_contact, guardian_email,
                profile_picture_url, agreed_terms
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                first_name=VALUES(first_name),
                last_name=VALUES(last_name),
                gender=VALUES(gender),
                guardian_fullname=VALUES(guardian_fullname),
                guardian_contact=VALUES(guardian_contact),
                guardian_email=VALUES(guardian_email),
                profile_picture_url=VALUES(profile_picture_url),
                agreed_terms=VALUES(agreed_terms)
        """
        self.execute(sql, (
            tenant_id,
            first_name,
            last_name,
            gender,
            guardian_name,
            guardian_contact,
            guardian_email,
            photo_path,
            agreed_terms
        ))

    def get_room_amenities(self, room_id):
        """
        Fetch amenities assigned to a specific room.
        Uses room_amenities + amenities tables.
        """
        sql = """
            SELECT a.label
            FROM room_amenities ra
            JOIN amenities a ON a.amenity_id = ra.amenity_id
            WHERE ra.room_id = %s
            ORDER BY a.label
        """
        rows = self.fetchall(sql, (room_id,))
        return [r["label"] for r in rows]

    def get_tenant_due(self, tenant_id):
        sql = """
            SELECT
                r.price AS amount,
                DATE_ADD(rr.start_date, INTERVAL TIMESTAMPDIFF(MONTH, rr.start_date, CURDATE()) MONTH) AS due_date
            FROM rentals rr
            JOIN rooms r ON rr.room_id = r.room_id
            WHERE rr.tenant_id = %s
            AND rr.status = 'ACTIVE'
        """
        return self.fetchone(sql, (tenant_id,))

    def get_dashboard_stats(self, tenant_id):
        """
        Returns summary data for Student Dashboard:
        - active reservations
        - next unpaid payment (amount + due date)
        """

        stats = {
            "active_res": 0,
            "next_payment": "No due",
            "total_dorms": "0 rooms"
        }

        # 1️⃣ Active reservations
        row = self.fetchone("""
            SELECT COUNT(*) AS cnt
            FROM rentals
            WHERE tenant_id=%s
            AND status IN ('ACTIVE','EXTENDED','ENDING')
        """, (tenant_id,))
        stats["active_res"] = row["cnt"] if row else 0

        # 2️⃣ Next unpaid payment (based on OWNER-SET PRICE)
        row = self.fetchone("""
            SELECT
                (p.amount_due - p.amount_paid) AS due_amount,
                p.due_date
            FROM payments p
            JOIN rentals rr ON p.rental_id = rr.rental_id
            WHERE rr.tenant_id = %s
            AND p.status IN ('DUE','OVERDUE')
            ORDER BY p.due_date ASC
            LIMIT 1
        """, (tenant_id,))

        if row:
            amount = f"₱{row['due_amount']:,.2f}"
            due_date = row["due_date"].strftime("%B %d, %Y")
            stats["next_payment"] = f"{amount} — Due {due_date}"

        return stats
