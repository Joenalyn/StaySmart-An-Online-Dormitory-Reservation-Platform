import mysql.connector
import bcrypt


class Auth:
    def __init__(self, host="localhost", user="root", password="", database="staysmartdb"):
        try:
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=3306
            )
        except mysql.connector.Error as e:
            print("Database connection failed:", str(e))
            raise

    def student_signup(self, student_name, username, contact, email, password):
        try:
            cursor = self.conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, "Username already exists"

            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return False, "Email already registered"

            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode("utf-8")

            sql = """
                INSERT INTO users (role, fullname, username, contact_no, email, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, ("TENANT", student_name, username, contact, email, hashed_pw))

            self.conn.commit()
            return True, "Signup successful!"

        except mysql.connector.Error as e:
            return False, f"Database Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def admin_signup(self, fullname, username, contact, email, password):
        try:
            cursor = self.conn.cursor(dictionary=True)

            # Check username
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, "Username already exists"

            # Check email
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return False, "Email already registered"

            # Hash password
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode("utf-8")

            # INSERT into users
            sql = """
                INSERT INTO users (role, fullname, username, contact_no, email, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, ("OWNER", fullname, username, contact, email, hashed_pw))

            self.conn.commit()
            return True, "Admin signup successful!"

        except mysql.connector.Error as e:
            return False, f"Database Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def login(self, username, password):
        try:
            cursor = self.conn.cursor(dictionary=True)

            sql = "SELECT * FROM users WHERE username = %s AND is_active = 1"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

            if not user:
                return False, None, None, "Invalid username or password"

            stored_pw = user["password_hash"].encode("utf-8")
            if bcrypt.checkpw(password.encode("utf-8"), stored_pw):
                return True, user["user_id"], user["role"], "Login successful"
            else:
                return False, None, None, "Invalid username or password"

        except Exception as e:
            return False, None, None, f"Login Error: {str(e)}"


    def student_login(self, username, password):
        success, user_id, role, msg = self.login(username, password)
        if success and role == "TENANT":
            return True, msg
        return False, "Invalid username or password"

    def admin_login(self, username, password):
        success, user_id, role, msg = self.login(username, password)
        if success and role == "OWNER":
            return True, msg
        return False, "Invalid username or password"

    def get_user(self, username):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        return cursor.fetchone()

    def email_exists(self, email):
        try:
            cursor = self.conn.cursor(dictionary=True)

            cursor.execute("SELECT role FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()

            if row:
                if row["role"] == "TENANT":
                    return True, "student"
                if row["role"] == "OWNER":
                    return True, "admin"

            return False, None

        except Exception as e:
            return False, f"Database error: {str(e)}"
