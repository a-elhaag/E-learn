import bcrypt
import os
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

# Database file
DB_FILE = "e_learning.db"

# Initialize Database
class DatabaseHandler:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None
        self.setup_database()

    def connect(self):
        self.conn = sqlite3.connect(self.db_file)
        return self.conn

    def setup_database(self):
        conn = self.connect()
        cursor = conn.cursor()
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password BLOB NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Student', 'Instructor', 'Admin'))
            )
        """)
        # Courses Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                description TEXT,
                instructor_id INTEGER,
                price REAL,
                FOREIGN KEY (instructor_id) REFERENCES users(id)
            )
        """)
        # Enrollments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                course_id INTEGER,
                progress INTEGER DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            )
        """)
        conn.commit()
        # Create default admin if not exists
        cursor.execute("SELECT * FROM users WHERE role = 'Admin'")
        if not cursor.fetchone():
            default_admin_password = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", default_admin_password, "Admin"),
            )
            conn.commit()
            print("Default admin user created. Username: admin | Password: admin123")
        conn.close()

    # User Operations
    def add_user(self, username, password, role):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hashed, role),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_user(self, username):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_all_users(self):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM users")
        users = cursor.fetchall()
        conn.close()
        return users

    def delete_user(self, user_id):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

    # Course Operations
    def add_course(self, title, description, instructor_id, price):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO courses (title, description, instructor_id, price) VALUES (?, ?, ?, ?)",
                (title, description, instructor_id, price),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_all_courses(self):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT courses.id, courses.title, courses.description, users.username, courses.price
            FROM courses
            JOIN users ON courses.instructor_id = users.id
        """)
        courses = cursor.fetchall()
        conn.close()
        return courses

    def get_instructor_courses(self, instructor_id):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, price FROM courses WHERE instructor_id = ?
        """, (instructor_id,))
        courses = cursor.fetchall()
        conn.close()
        return courses

    def delete_course(self, course_id):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
        conn.close()

    # Enrollment Operations
    def enroll_student(self, student_id, course_id):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)",
                (student_id, course_id),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_student_enrollments(self, student_id):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT courses.title, courses.description, courses.price, enrollments.progress
            FROM enrollments
            JOIN courses ON enrollments.course_id = courses.id
            WHERE enrollments.student_id = ?
        """, (student_id,))
        enrollments = cursor.fetchall()
        conn.close()
        return enrollments

    def update_progress(self, student_id, course_id, progress):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE enrollments SET progress = ? WHERE student_id = ? AND course_id = ?
        """, (progress, student_id, course_id))
        conn.commit()
        conn.close()

# Main Application
class E_LearningApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("E-Learning Platform")
        self.geometry("900x600")
        self.minsize(800, 500)
        self.configure(bg="#f0f0f0")

        # Initialize Database Handler
        self.db = DatabaseHandler(DB_FILE)

        # Current User
        self.current_user = None

        # Style Configuration
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 12))
        self.style.configure(
            "Header.TLabel",
            background="#f0f0f0",
            font=("Helvetica", 24, "bold"),
            foreground="#003366",
        )
        self.style.configure("TButton", font=("Helvetica", 12), padding=6)
        self.style.configure(
            "Accent.TButton", foreground="white", background="#003366"
        )
        self.style.map(
            "Accent.TButton",
            foreground=[("active", "white")],
            background=[("active", "#00509e")],
        )

        # Container for Frames
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Dictionary to hold frames
        self.frames = {}

        # Initialize Frames
        for F in (
            LoginFrame,
            RegisterFrame,
            StudentDashboard,
            InstructorDashboard,
            AdminDashboard,
            CourseDetailsFrame,
            ProfileFrame,
        ):
            frame = F(parent=container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(LoginFrame)

    def show_frame(self, cont, *args):
        """Brings the specified frame to the front."""
        frame = self.frames[cont]
        if hasattr(frame, 'refresh'):
            frame.refresh(*args)
        frame.tkraise()

    def logout(self):
        """Logs out the current user."""
        self.current_user = None
        self.show_frame(LoginFrame)

# Login Frame
class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Widgets
        header = ttk.Label(self, text="E-Learning Platform", style="Header.TLabel")
        header.pack(pady=40)

        login_frame = ttk.Frame(self)
        login_frame.pack(pady=10)

        username_label = ttk.Label(login_frame, text="Username:")
        username_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.username_entry = ttk.Entry(login_frame, width=30)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)

        password_label = ttk.Label(login_frame, text="Password:")
        password_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.password_entry = ttk.Entry(login_frame, show="*", width=30)
        self.password_entry.grid(row=1, column=1, padx=10, pady=10)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)

        login_button = ttk.Button(
            button_frame, text="Login", style="Accent.TButton", command=self.login
        )
        login_button.grid(row=0, column=0, padx=10)

        register_button = ttk.Button(
            button_frame,
            text="Register",
            command=lambda: controller.show_frame(RegisterFrame),
        )
        register_button.grid(row=0, column=1, padx=10)

    def login(self):
        """Handles user login."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning(
                "Input Error", "Please enter both username and password."
            )
            return

        user = self.controller.db.get_user(username)
        if user and bcrypt.checkpw(password.encode(), user[2]):
            self.controller.current_user = {
                "id": user[0],
                "username": user[1],
                "role": user[3],
            }
            messagebox.showinfo("Login Successful", f"Welcome, {user[1]}!")
            if user[3] == "Student":
                self.controller.show_frame(StudentDashboard)
            elif user[3] == "Instructor":
                self.controller.show_frame(InstructorDashboard)
            elif user[3] == "Admin":
                self.controller.show_frame(AdminDashboard)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

# Register Frame
class RegisterFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Widgets
        header = ttk.Label(self, text="Register", style="Header.TLabel")
        header.pack(pady=20)

        register_frame = ttk.Frame(self)
        register_frame.pack(pady=10)

        username_label = ttk.Label(register_frame, text="Username:")
        username_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.username_entry = ttk.Entry(register_frame, width=30)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)

        password_label = ttk.Label(register_frame, text="Password:")
        password_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.password_entry = ttk.Entry(register_frame, show="*", width=30)
        self.password_entry.grid(row=1, column=1, padx=10, pady=10)

        confirm_label = ttk.Label(register_frame, text="Confirm Password:")
        confirm_label.grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.confirm_entry = ttk.Entry(register_frame, show="*", width=30)
        self.confirm_entry.grid(row=2, column=1, padx=10, pady=10)

        role_label = ttk.Label(register_frame, text="Role:")
        role_label.grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.role_combo = ttk.Combobox(
            register_frame, values=["Student", "Instructor"], state="readonly", width=28
        )
        self.role_combo.current(0)
        self.role_combo.grid(row=3, column=1, padx=10, pady=10)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)

        register_button = ttk.Button(
            button_frame, text="Register", style="Accent.TButton", command=self.register
        )
        register_button.grid(row=0, column=0, padx=10)

        back_button = ttk.Button(
            button_frame,
            text="Back to Login",
            command=lambda: controller.show_frame(LoginFrame),
        )
        back_button.grid(row=0, column=1, padx=10)

    def register(self):
        """Handles user registration."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm = self.confirm_entry.get().strip()
        role = self.role_combo.get().strip()

        if not username or not password or not confirm:
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        if len(username) < 4:
            messagebox.showwarning(
                "Input Error", "Username must be at least 4 characters long."
            )
            return

        if len(password) < 6:
            messagebox.showwarning(
                "Input Error", "Password must be at least 6 characters long."
            )
            return

        if password != confirm:
            messagebox.showwarning("Input Error", "Passwords do not match.")
            return

        success = self.controller.db.add_user(username, password, role)
        if success:
            messagebox.showinfo(
                "Registration Successful",
                "You have registered successfully. Please log in.",
            )
            self.controller.show_frame(LoginFrame)
        else:
            messagebox.showerror("Registration Failed", "Username already exists.")

# Student Dashboard
class StudentDashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.enrollments = []

        # Widgets
        header = ttk.Label(self, text="Student Dashboard", style="Header.TLabel")
        header.pack(pady=10)

        # Navigation Buttons
        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=5)
        self.profile_button = ttk.Button(nav_frame, text="Profile", command=lambda: controller.show_frame(ProfileFrame))
        self.profile_button.grid(row=0, column=0, padx=5)
        self.logout_button = ttk.Button(nav_frame, text="Logout", command=controller.logout)
        self.logout_button.grid(row=0, column=1, padx=5)

        # Courses Section
        courses_label = ttk.Label(self, text="Available Courses:", font=("Helvetica", 14))
        courses_label.pack(pady=10)

        search_frame = ttk.Frame(self)
        search_frame.pack(pady=5)

        search_label = ttk.Label(search_frame, text="Search:")
        search_label.grid(row=0, column=0, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=1, padx=5)
        search_button = ttk.Button(search_frame, text="Search", command=self.search_courses)
        search_button.grid(row=0, column=2, padx=5)
        show_all_button = ttk.Button(search_frame, text="Show All", command=self.load_courses)
        show_all_button.grid(row=0, column=3, padx=5)

        self.courses_tree = ttk.Treeview(
            self,
            columns=("ID", "Title", "Instructor", "Price"),
            show="headings",
            selectmode="browse",
        )
        self.courses_tree.heading("ID", text="ID")
        self.courses_tree.heading("Title", text="Title")
        self.courses_tree.heading("Instructor", text="Instructor")
        self.courses_tree.heading("Price", text="Price ($)")
        self.courses_tree.column("ID", width=50, anchor="center")
        self.courses_tree.column("Title", width=300, anchor="w")
        self.courses_tree.column("Instructor", width=150, anchor="center")
        self.courses_tree.column("Price", width=100, anchor="center")
        self.courses_tree.pack(pady=10, fill="both", expand=True, padx=50)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        enroll_button = ttk.Button(
            button_frame,
            text="Enroll in Selected Course",
            style="Accent.TButton",
            command=self.enroll_course,
        )
        enroll_button.grid(row=0, column=0, padx=10)
        details_button = ttk.Button(
            button_frame,
            text="View Course Details",
            command=lambda: controller.show_frame(CourseDetailsFrame, "student"),
        )
        details_button.grid(row=0, column=1, padx=10)

        # Enrollments Section
        enrollments_label = ttk.Label(self, text="My Enrollments:", font=("Helvetica", 14))
        enrollments_label.pack(pady=10)

        self.enrollments_tree = ttk.Treeview(
            self,
            columns=("Title", "Progress"),
            show="headings",
            selectmode="browse",
        )
        self.enrollments_tree.heading("Title", text="Title")
        self.enrollments_tree.heading("Progress", text="Progress (%)")
        self.enrollments_tree.column("Title", width=400, anchor="w")
        self.enrollments_tree.column("Progress", width=150, anchor="center")
        self.enrollments_tree.pack(pady=10, fill="both", expand=True, padx=50)

    def refresh(self):
        """Refreshes the dashboard data."""
        self.load_courses()
        self.load_enrollments()

    def load_courses(self, courses=None):
        """Loads available courses into the treeview."""
        for item in self.courses_tree.get_children():
            self.courses_tree.delete(item)
        if courses is None:
            courses = self.controller.db.get_all_courses()
        for course in courses:
            self.courses_tree.insert(
                "",
                "end",
                values=(
                    course[0],
                    course[1],
                    course[3],
                    f"{course[4]:.2f}",
                ),
            )

    def search_courses(self):
        """Searches courses based on the search entry."""
        query = self.search_entry.get().strip().lower()
        if not query:
            messagebox.showwarning("Input Error", "Please enter a search term.")
            return
        all_courses = self.controller.db.get_all_courses()
        filtered = [course for course in all_courses if query in course[1].lower()]
        self.load_courses(filtered)

    def enroll_course(self):
        """Enrolls the student in the selected course."""
        selected = self.courses_tree.focus()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a course to enroll.")
            return
        course = self.courses_tree.item(selected)["values"]
        course_id = course[0]
        course_title = course[1]

        student_id = self.controller.current_user["id"]
        success = self.controller.db.enroll_student(student_id, course_id)
        if success:
            messagebox.showinfo("Enrollment", f"You have enrolled in '{course_title}' successfully.")
            self.load_enrollments()
        else:
            messagebox.showerror("Enrollment Failed", "You are already enrolled in this course.")

    def load_enrollments(self):
        """Loads the student's enrollments."""
        for item in self.enrollments_tree.get_children():
            self.enrollments_tree.delete(item)
        student_id = self.controller.current_user["id"]
        enrollments = self.controller.db.get_student_enrollments(student_id)
        for enrollment in enrollments:
            self.enrollments_tree.insert(
                "",
                "end",
                values=(
                    enrollment[0],
                    enrollment[3],
                ),
            )

# Instructor Dashboard
class InstructorDashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Widgets
        header = ttk.Label(self, text="Instructor Dashboard", style="Header.TLabel")
        header.pack(pady=10)

        # Navigation Buttons
        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=5)
        self.profile_button = ttk.Button(nav_frame, text="Profile", command=lambda: controller.show_frame(ProfileFrame))
        self.profile_button.grid(row=0, column=0, padx=5)
        self.logout_button = ttk.Button(nav_frame, text="Logout", command=controller.logout)
        self.logout_button.grid(row=0, column=1, padx=5)

        # Course Creation Section
        create_frame = ttk.LabelFrame(self, text="Create New Course")
        create_frame.pack(pady=10, fill="x", padx=50)

        title_label = ttk.Label(create_frame, text="Title:")
        title_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.title_entry = ttk.Entry(create_frame, width=50)
        self.title_entry.grid(row=0, column=1, padx=10, pady=10)

        description_label = ttk.Label(create_frame, text="Description:")
        description_label.grid(row=1, column=0, padx=10, pady=10, sticky="ne")
        self.description_text = tk.Text(create_frame, height=4, width=38)
        self.description_text.grid(row=1, column=1, padx=10, pady=10)

        price_label = ttk.Label(create_frame, text="Price ($):")
        price_label.grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.price_entry = ttk.Entry(create_frame, width=50)
        self.price_entry.grid(row=2, column=1, padx=10, pady=10)

        create_button = ttk.Button(
            create_frame,
            text="Create Course",
            style="Accent.TButton",
            command=self.create_course,
        )
        create_button.grid(row=3, column=1, padx=10, pady=10, sticky="e")

        # Courses Section
        courses_label = ttk.Label(self, text="My Courses:", font=("Helvetica", 14))
        courses_label.pack(pady=10)

        self.courses_tree = ttk.Treeview(
            self, columns=("ID", "Title", "Price"), show="headings", selectmode="browse"
        )
        self.courses_tree.heading("ID", text="ID")
        self.courses_tree.heading("Title", text="Title")
        self.courses_tree.heading("Price", text="Price ($)")
        self.courses_tree.column("ID", width=50, anchor="center")
        self.courses_tree.column("Title", width=500, anchor="w")
        self.courses_tree.column("Price", width=100, anchor="center")
        self.courses_tree.pack(pady=10, fill="both", expand=True, padx=50)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        delete_button = ttk.Button(
            button_frame,
            text="Delete Selected Course",
            style="Accent.TButton",
            command=self.delete_course,
        )
        delete_button.grid(row=0, column=0, padx=10)
        details_button = ttk.Button(
            button_frame,
            text="View Course Details",
            command=lambda: controller.show_frame(CourseDetailsFrame, "instructor"),
        )
        details_button.grid(row=0, column=1, padx=10)

    def refresh(self):
        """Refreshes the dashboard data."""
        self.load_courses()

    def create_course(self):
        """Creates a new course."""
        title = self.title_entry.get().strip()
        description = self.description_text.get("1.0", tk.END).strip()
        price = self.price_entry.get().strip()

        if not title or not description or not price:
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        try:
            price = float(price)
            if price < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive price.")
            return

        instructor_id = self.controller.current_user["id"]
        success = self.controller.db.add_course(title, description, instructor_id, price)
        if success:
            messagebox.showinfo("Success", f"Course '{title}' created successfully.")
            self.title_entry.delete(0, tk.END)
            self.description_text.delete("1.0", tk.END)
            self.price_entry.delete(0, tk.END)
            self.load_courses()
        else:
            messagebox.showerror("Error", "Course title already exists.")

    def load_courses(self):
        """Loads the instructor's courses."""
        for item in self.courses_tree.get_children():
            self.courses_tree.delete(item)
        instructor_id = self.controller.current_user["id"]
        courses = self.controller.db.get_instructor_courses(instructor_id)
        for course in courses:
            self.courses_tree.insert(
                "",
                "end",
                values=(
                    course[0],
                    course[1],
                    f"{course[2]:.2f}",
                ),
            )

    def delete_course(self):
        """Deletes the selected course."""
        selected = self.courses_tree.focus()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a course to delete.")
            return
        course = self.courses_tree.item(selected)["values"]
        course_id = course[0]
        course_title = course[1]

        confirm = messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete course '{course_title}'?"
        )
        if confirm:
            self.controller.db.delete_course(course_id)
            messagebox.showinfo("Success", f"Course '{course_title}' has been deleted.")
            self.load_courses()

# Admin Dashboard
class AdminDashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Widgets
        header = ttk.Label(self, text="Admin Dashboard", style="Header.TLabel")
        header.pack(pady=10)

        # Navigation Buttons
        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=5)
        self.logout_button = ttk.Button(nav_frame, text="Logout", command=controller.logout)
        self.logout_button.grid(row=0, column=0, padx=5)

        # Users Section
        users_label = ttk.Label(self, text="Registered Users:", font=("Helvetica", 14))
        users_label.pack(pady=10)

        search_frame = ttk.Frame(self)
        search_frame.pack(pady=5)

        search_label = ttk.Label(search_frame, text="Search:")
        search_label.grid(row=0, column=0, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=1, padx=5)
        search_button = ttk.Button(search_frame, text="Search", command=self.search_users)
        search_button.grid(row=0, column=2, padx=5)
        show_all_button = ttk.Button(search_frame, text="Show All", command=self.load_users)
        show_all_button.grid(row=0, column=3, padx=5)

        self.users_tree = ttk.Treeview(
            self,
            columns=("ID", "Username", "Role"),
            show="headings",
            selectmode="browse",
        )
        self.users_tree.heading("ID", text="ID")
        self.users_tree.heading("Username", text="Username")
        self.users_tree.heading("Role", text="Role")
        self.users_tree.column("ID", width=50, anchor="center")
        self.users_tree.column("Username", width=300, anchor="w")
        self.users_tree.column("Role", width=150, anchor="center")
        self.users_tree.pack(pady=10, fill="both", expand=True, padx=50)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        delete_button = ttk.Button(
            button_frame,
            text="Delete Selected User",
            style="Accent.TButton",
            command=self.delete_user,
        )
        delete_button.grid(row=0, column=0, padx=10)
        promote_button = ttk.Button(
            button_frame,
            text="Promote to Instructor",
            command=self.promote_user,
        )
        promote_button.grid(row=0, column=1, padx=10)

        # Courses Section
        courses_label = ttk.Label(self, text="All Courses:", font=("Helvetica", 14))
        courses_label.pack(pady=10)

        self.courses_tree = ttk.Treeview(
            self,
            columns=("ID", "Title", "Instructor", "Price"),
            show="headings",
            selectmode="browse",
        )
        self.courses_tree.heading("ID", text="ID")
        self.courses_tree.heading("Title", text="Title")
        self.courses_tree.heading("Instructor", text="Instructor")
        self.courses_tree.heading("Price", text="Price ($)")
        self.courses_tree.column("ID", width=50, anchor="center")
        self.courses_tree.column("Title", width=400, anchor="w")
        self.courses_tree.column("Instructor", width=200, anchor="center")
        self.courses_tree.column("Price", width=100, anchor="center")
        self.courses_tree.pack(pady=10, fill="both", expand=True, padx=50)

        delete_course_button = ttk.Button(
            self,
            text="Delete Selected Course",
            style="Accent.TButton",
            command=self.delete_course,
        )
        delete_course_button.pack(pady=5)

    def refresh(self):
        """Refreshes the dashboard data."""
        self.load_users()
        self.load_courses()

    def load_users(self, users=None):
        """Loads users into the treeview."""
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        if users is None:
            users = self.controller.db.get_all_users()
        for user in users:
            self.users_tree.insert(
                "",
                "end",
                values=(
                    user[0],
                    user[1],
                    user[2],
                ),
            )

    def search_users(self):
        """Searches users based on the search entry."""
        query = self.search_entry.get().strip().lower()
        if not query:
            messagebox.showwarning("Input Error", "Please enter a search term.")
            return
        all_users = self.controller.db.get_all_users()
        filtered = [user for user in all_users if query in user[1].lower()]
        self.load_users(filtered)

    def delete_user(self):
        """Deletes the selected user."""
        selected = self.users_tree.focus()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a user to delete.")
            return
        user = self.users_tree.item(selected)["values"]
        user_id = user[0]
        username = user[1]
        role = user[2]

        if username == self.controller.current_user["username"]:
            messagebox.showerror("Error", "You cannot delete your own account.")
            return

        confirm = messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete user '{username}'?"
        )
        if confirm:
            self.controller.db.delete_user(user_id)
            messagebox.showinfo("Success", f"User '{username}' has been deleted.")
            self.load_users()

    def promote_user(self):
        """Promotes a selected student to instructor."""
        selected = self.users_tree.focus()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a user to promote.")
            return
        user = self.users_tree.item(selected)["values"]
        user_id = user[0]
        username = user[1]
        role = user[2]

        if role != "Student":
            messagebox.showerror("Error", "Only students can be promoted to instructors.")
            return

        conn = self.controller.db.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = 'Instructor' WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", f"User '{username}' has been promoted to Instructor.")
        self.load_users()

    def load_courses(self):
        """Loads all courses into the treeview."""
        for item in self.courses_tree.get_children():
            self.courses_tree.delete(item)
        courses = self.controller.db.get_all_courses()
        for course in courses:
            self.courses_tree.insert(
                "",
                "end",
                values=(
                    course[0],
                    course[1],
                    course[3],
                    f"{course[4]:.2f}",
                ),
            )

    def delete_course(self):
        """Deletes the selected course."""
        selected = self.courses_tree.focus()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a course to delete.")
            return
        course = self.courses_tree.item(selected)["values"]
        course_id = course[0]
        course_title = course[1]

        confirm = messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete course '{course_title}'?"
        )
        if confirm:
            self.controller.db.delete_course(course_id)
            messagebox.showinfo("Success", f"Course '{course_title}' has been deleted.")
            self.load_courses()

# Course Details Frame
class CourseDetailsFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.view_mode = "student"  # or "instructor"

        # Widgets
        header = ttk.Label(self, text="Course Details", style="Header.TLabel")
        header.pack(pady=10)

        # Navigation Buttons
        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=5)
        self.back_button = ttk.Button(nav_frame, text="Back", command=lambda: controller.show_frame(self.previous_frame))
        self.back_button.grid(row=0, column=0, padx=5)
        self.logout_button = ttk.Button(nav_frame, text="Logout", command=controller.logout)
        self.logout_button.grid(row=0, column=1, padx=5)

        # Course Info
        info_frame = ttk.LabelFrame(self, text="Course Information")
        info_frame.pack(pady=10, fill="both", expand=True, padx=50)

        self.title_label = ttk.Label(info_frame, text="Title:", font=("Helvetica", 12, "bold"))
        self.title_label.pack(anchor="w", padx=10, pady=5)

        self.description_label = ttk.Label(info_frame, text="Description:", font=("Helvetica", 12, "bold"))
        self.description_label.pack(anchor="w", padx=10, pady=5)

        self.instructor_label = ttk.Label(info_frame, text="Instructor:", font=("Helvetica", 12, "bold"))
        self.instructor_label.pack(anchor="w", padx=10, pady=5)

        self.price_label = ttk.Label(info_frame, text="Price ($):", font=("Helvetica", 12, "bold"))
        self.price_label.pack(anchor="w", padx=10, pady=5)

        # For instructors to update progress
        self.progress_frame = ttk.LabelFrame(self, text="Manage Progress")
        self.progress_frame.pack(pady=10, fill="x", padx=50)
        self.progress_label = ttk.Label(self.progress_frame, text="Set Progress (%):")
        self.progress_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.progress_entry = ttk.Entry(self.progress_frame, width=10)
        self.progress_entry.grid(row=0, column=1, padx=10, pady=10)
        self.set_progress_button = ttk.Button(
            self.progress_frame,
            text="Update Progress",
            style="Accent.TButton",
            command=self.update_progress,
        )
        self.set_progress_button.grid(row=0, column=2, padx=10, pady=10)

    def refresh(self, view_mode):
        """Refreshes the course details based on the view mode."""
        self.view_mode = view_mode
        self.previous_frame = StudentDashboard if view_mode == "student" else InstructorDashboard

        # Get selected course
        if view_mode == "student":
            selected = self.controller.frames[StudentDashboard].courses_tree.focus()
            tree = self.controller.frames[StudentDashboard].courses_tree
        else:
            selected = self.controller.frames[InstructorDashboard].courses_tree.focus()
            tree = self.controller.frames[InstructorDashboard].courses_tree

        if not selected:
            messagebox.showwarning("Selection Error", "Please select a course to view details.")
            self.controller.show_frame(self.previous_frame)
            return

        course = tree.item(selected)["values"]
        course_id = course[0]

        # Fetch course details
        conn = self.controller.db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT courses.title, courses.description, users.username, courses.price
            FROM courses
            JOIN users ON courses.instructor_id = users.id
            WHERE courses.id = ?
        """, (course_id,))
        course_details = cursor.fetchone()
        conn.close()

        if course_details:
            self.title_label.config(text=f"Title: {course_details[0]}")
            self.description_label.config(text=f"Description: {course_details[1]}")
            self.instructor_label.config(text=f"Instructor: {course_details[2]}")
            self.price_label.config(text=f"Price ($): {course_details[3]:.2f}")
        else:
            messagebox.showerror("Error", "Course details not found.")
            self.controller.show_frame(self.previous_frame)

        # If student, hide progress management
        if view_mode == "student":
            self.progress_frame.pack_forget()
        else:
            self.progress_frame.pack(pady=10, fill="x", padx=50)

    def update_progress(self):
        """Updates the student's progress in the course."""
        progress = self.progress_entry.get().strip()
        if not progress.isdigit() or not (0 <= int(progress) <= 100):
            messagebox.showerror("Input Error", "Please enter a valid progress percentage (0-100).")
            return
        progress = int(progress)

        # Get selected course
        selected = self.controller.frames[InstructorDashboard].courses_tree.focus()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a course to update progress.")
            return
        course = self.controller.frames[InstructorDashboard].courses_tree.item(selected)["values"]
        course_id = course[0]

        # For simplicity, assume updating progress for all enrolled students
        conn = self.controller.db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT enrollments.id, users.username
            FROM enrollments
            JOIN users ON enrollments.student_id = users.id
            WHERE enrollments.course_id = ?
        """, (course_id,))
        enrollments = cursor.fetchall()
        if not enrollments:
            messagebox.showinfo("Info", "No students enrolled in this course.")
            conn.close()
            return

        # Update progress for all enrolled students
        for enrollment in enrollments:
            enrollment_id = enrollment[0]
            cursor.execute("""
                UPDATE enrollments SET progress = ? WHERE id = ?
            """, (progress, enrollment_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", f"Progress updated to {progress}% for all enrolled students.")

# Profile Frame
class ProfileFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Widgets
        header = ttk.Label(self, text="Profile", style="Header.TLabel")
        header.pack(pady=10)

        # Navigation Buttons
        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=5)
        self.back_button = ttk.Button(nav_frame, text="Back", command=self.go_back)
        self.back_button.grid(row=0, column=0, padx=5)
        self.logout_button = ttk.Button(nav_frame, text="Logout", command=controller.logout)
        self.logout_button.grid(row=0, column=1, padx=5)

        # Profile Info
        profile_frame = ttk.LabelFrame(self, text="User Information")
        profile_frame.pack(pady=10, fill="both", expand=True, padx=50)

        username_label = ttk.Label(profile_frame, text="Username:", font=("Helvetica", 12, "bold"))
        username_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.username_value = ttk.Label(profile_frame, text="")
        self.username_value.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        role_label = ttk.Label(profile_frame, text="Role:", font=("Helvetica", 12, "bold"))
        role_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.role_value = ttk.Label(profile_frame, text="")
        self.role_value.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # Change Password Section
        password_frame = ttk.LabelFrame(self, text="Change Password")
        password_frame.pack(pady=10, fill="x", padx=50)

        current_label = ttk.Label(password_frame, text="Current Password:")
        current_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.current_entry = ttk.Entry(password_frame, show="*", width=30)
        self.current_entry.grid(row=0, column=1, padx=10, pady=10)

        new_label = ttk.Label(password_frame, text="New Password:")
        new_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.new_entry = ttk.Entry(password_frame, show="*", width=30)
        self.new_entry.grid(row=1, column=1, padx=10, pady=10)

        confirm_label = ttk.Label(password_frame, text="Confirm Password:")
        confirm_label.grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.confirm_entry = ttk.Entry(password_frame, show="*", width=30)
        self.confirm_entry.grid(row=2, column=1, padx=10, pady=10)

        change_button = ttk.Button(
            password_frame,
            text="Change Password",
            style="Accent.TButton",
            command=self.change_password,
        )
        change_button.grid(row=3, column=1, padx=10, pady=10, sticky="e")

    def refresh(self):
        """Refreshes the profile data."""
        user = self.controller.current_user
        self.username_value.config(text=user["username"])
        self.role_value.config(text=user["role"])

    def go_back(self):
        """Navigates back to the appropriate dashboard."""
        role = self.controller.current_user["role"]
        if role == "Student":
            self.controller.show_frame(StudentDashboard)
        elif role == "Instructor":
            self.controller.show_frame(InstructorDashboard)
        elif role == "Admin":
            self.controller.show_frame(AdminDashboard)

    def change_password(self):
        """Handles password change."""
        current = self.current_entry.get().strip()
        new = self.new_entry.get().strip()
        confirm = self.confirm_entry.get().strip()

        if not current or not new or not confirm:
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        user = self.controller.db.get_user(self.controller.current_user["username"])
        if not bcrypt.checkpw(current.encode(), user[2]):
            messagebox.showerror("Error", "Current password is incorrect.")
            return

        if len(new) < 6:
            messagebox.showwarning("Input Error", "New password must be at least 6 characters long.")
            return

        if new != confirm:
            messagebox.showwarning("Input Error", "New passwords do not match.")
            return

        # Update password
        conn = self.controller.db.connect()
        cursor = conn.cursor()
        hashed = bcrypt.hashpw(new.encode(), bcrypt.gensalt())
        cursor.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (hashed, self.controller.current_user["id"]),
        )
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Password has been updated successfully.")
        self.current_entry.delete(0, tk.END)
        self.new_entry.delete(0, tk.END)
        self.confirm_entry.delete(0, tk.END)

# Run the application
if __name__ == "__main__":
    app = E_LearningApp()
    app.mainloop()
