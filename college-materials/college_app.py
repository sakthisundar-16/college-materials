import os
import mysql.connector
from flask import Flask, render_template, request, redirect, send_from_directory, flash, url_for, jsonify, abort
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import os

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'zip', 'txt', 'jpg', 'png'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB limit

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev_secret_key_change_in_production')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email, password_hash, role, name, user_key=None):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.name = name
        self.user_key = user_key
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

def load_user_from_row(row):
    """Load user from database row, handling both dict and tuple formats"""
    if not row:
        return None
    
    if isinstance(row, dict):
        # Handle dictionary format (MySQL connector with dictionary=True)
        return User(
            row.get('id'),
            row.get('email'),
            row.get('password_hash'),
            row.get('role'),
            row.get('name'),
            row.get('user_key')
        )
    else:
        # Handle tuple/list format
        return User(
            row[0],  # id
            row[1],  # email
            row[2],  # password_hash
            row[3],  # role
            row[4],  # name
            row[5] if len(row) > 5 else None  # user_key
        )

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id=%s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return load_user_from_row(row) if row else None
    return None

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- AUTH SETUP ---
auth = HTTPBasicAuth()
users = {
    "sakthi": generate_password_hash("sakthi")
}
@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

def get_db():
    """Get MySQL database connection to college_db"""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='2005',
            database='college_db',
            auth_plugin='caching_sha2_password'
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to college_db: {e}")
        return None

def create_database():
    """Create the college_db database if it doesn't exist"""
    conn = get_db()
    if not conn:
        print("Failed to connect to MySQL server")
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS college_db")
        cursor.close()
        conn.close()
        return True
    except mysql.connector.Error as e:
        print(f"Error creating database: {e}")
        return False

def get_db_connection():
    """Get connection to college_db database"""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='2005',
            database='college_db',
            auth_plugin='caching_sha2_password'
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to college_db: {e}")
        return None

def init_db():
    # First create the database
    if not create_database():
        return
    
    # Then connect to the specific database
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to college_db database")
        return
    
    cursor = conn.cursor()
    
    # Create tables with MySQL syntax - ORDER MATTERS!
    # First create users table since other tables reference it
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL CHECK(role IN ('admin','faculty','student')),
            name VARCHAR(255)
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS semesters (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            department_id INT,
            UNIQUE(name, department_id),
            FOREIGN KEY(department_id) REFERENCES departments(id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            semester_id INT,
            UNIQUE(name, semester_id),
            FOREIGN KEY(semester_id) REFERENCES semesters(id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subject_id INT,
            filename VARCHAR(255),
            original_filename VARCHAR(255),
            uploader_id INT,
            FOREIGN KEY(subject_id) REFERENCES subjects(id),
            FOREIGN KEY(uploader_id) REFERENCES users(id)
        );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INT AUTO_INCREMENT PRIMARY KEY,
        department_id INT,
        title VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        author VARCHAR(255),
        event_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        image_url TEXT,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS department_achievements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            department_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(department_id) REFERENCES departments(id)
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            material_id INT NOT NULL,
            sender_id INT NOT NULL,
            receiver_id INT NOT NULL,
            encrypted_message TEXT NOT NULL,
            reply_to INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(reply_to) REFERENCES messages(id) ON DELETE CASCADE
        );
    ''')

    # === Populate Departments, Semesters, and Subjects ===
    departments = [
        ('CSE',), ('EEE',), ('MECH',), ('ECE',), ('CIVIL',), ('AIDS',), ('IT',)
    ]
    
    # Use INSERT IGNORE for MySQL
    insert_dept_query = "INSERT IGNORE INTO departments (name) VALUES (%s)"
    cursor.executemany(insert_dept_query, departments)

    # Example structure for CSE. You can expand for other departments.
    SEMESTER_STRUCTURE = {
         "CSE": {
            "Semester I": [
                "Professional English",
                "Matrices and Calculus",
                "Engineering Physics",
                "CY3151 Engineering Chemistry",
                "GE3151 Problem Solving and Python Programming",
                "GE3152 தமிழர்மரபு / Heritage of Tamils"
            ],
            "Semester II": [
                "HS3252 Professional English II",
                "MA3251 Statistics and Numerical Methods",
                "PH3256 Physics for Information Science",
                "BE3251 Basic Electrical and Electronics Engineering",
                "GE3251 Engineering Graphics",
                "CS3251 Programming in C",
                "GE3252 தமிழரும் தொழில்நுட்பமும் / Tamils and Technology"
            ],
            "Semester III": [
                "MA3354 Discrete Mathematics",
                "CS3351 Digital Principles and Computer Organization",
                "CS3352 Foundations of Data Science",
                "CS3301 Data Structures",
                "CS3391 Object Oriented Programming"
            ],
            "Semester IV": [
                "CS3452 Theory of Computation",
                "CS3491 Artificial Intelligence and Machine Learning",
                "CS3492 Database Management Systems",
                "CS3401 Algorithms",
                "CS3451 Introduction to Operating Systems",
                "GE3451 Environmental Sciences and Sustainability"
            ],
            "Semester V": [
                "CS3591 Computer Networks",
                "CS3501 Compiler Design",
                "CB3491 Cryptography and Cyber Security"
            ],
            "Semester VI": [
                "CCS356 Object Oriented Software Engineering",
                "CCS356 Object Oriented Software Engineering",
                "CS3691 Embedded Systems and IoT"
            ],
            "Semester VII": [
                "GE3791 Human Values and Ethics"
            ]
        },
        "EEE": {
            "Semester I": [
                "HS3152 Professional English - I",
                "MA3151 Matrices and Calculus",
                "PH3151 Engineering Physics",
                "CY3151 Engineering Chemistry",
                "GE3151 Problem Solving and Python Programming",
                "GE3152 த௘ழர்மர௖ / Heritage of Tamils"
            ],
            "Semester II": [
                "HS3252 Professional English - II",
                "MA3251 Statistics and Numerical Methods",
                "PH3202 Physics for Electrical Engineering",
                "BE3255 Basic Civil and Mechanical Engineering",
                "GE3251 Engineering Graphics",
                "EE3251 Electric Circuit Analysis",
                "GE3252 தமிழரும் தொழில்நுட்பமும் / Tamils and Technology"
            ],
            "Semester III": [
                "MA3303 Probability and Complex Functions",
                "EE3301 Electromagnetic Fields",
                "EE3302 Digital Logic Circuits",
                "EC3301 Electron Devices and Circuits",
                "EE3303 Electrical Machines - I",
                "CS3353 C Programming and Data Structures"
            ],
            "Semester IV": [
                "GE3451 Environmental Sciences and Sustainability",
                "EE3401 Transmission and Distribution",
                "EE3402 Linear Integrated Circuits",
                "EE3403 Measurements and Instrumentation",
                "EE3404 Microprocessor and Microcontroller",
                "EE3405 Electrical Machines - II"
            ],
            "Semester V": [
                "EE3501 Power System Analysis",
                "EE3591 Power Electronics",
                "EE3503 Control Systems"
            ],
            "Semester VI": [
                "EE3601 Protection and Switchgear",
                "EE3602 Power System Operation and Control"
            ],
            "Semester VII": [
                "EE3701 High Voltage Engineering",
                "GE3791 Human Values and Ethics"
            ]
        },
        "MECH": {
            "Semester I": [
                "HS3152 Professional English - I",
                "MA3151 Matrices and Calculus",
                "PH3151 Engineering Physics",
                "CY3151 Engineering Chemistry",
                "GE3151 Problem Solving and Python Programming",
                "GE3152 தமிழர்மரபு/Heritage of Tamils"
            ],
            "Semester II": [
                "HS3252 Professional English - II",
                "MA3251 Statistics and Numerical Methods",
                "PH3251 Materials Science",
                "BE3251 Basic Electrical and Electronics Engineering",
                "GE3251 Engineering Graphics",
                "GE3252 தமிழரும் ததொழில்நுட்பமும் / Tamils and Technology"
            ],
            "Semester III": [
                "MA3351 Transforms and Partial Differential Equations",
                "ME3351 Engineering Mechanics",
                "ME3391 Engineering Thermodynamics",
                "CE3391 Fluid Mechanics and Machinery",
                "ME3392 Engineering Materials and Metallurgy",
                "ME3393 Manufacturing Processes"
            ],
            "Semester IV": [
                "ME3491 Theory of Machines",
                "ME3451 Thermal Engineering",
                "ME3492 Hydraulics and Pneumatics",
                "ME3493 Manufacturing Technology",
                "CE3491 Strength of Materials",
                "GE3451 Environmental Sciences and Sustainability"
            ],
            "Semester V": [
                "ME3591 Design of Machine Elements",
                "ME3592 Metrology and Measurements"
            ],
            "Semester VI": [
                "ME3691 Heat and Mass Transfer"
            ],
            "Semester VII": [
                "ME3791 Mechatronics and IoT",
                "ME3792 Computer Integrated Manufacturing",
                "GE3791 Human Values and Ethics",
                "GE3792 Industrial Management"
            ]
        },
        "ECE": {
            "Semester I": [
                "HS3152 Professional English - I",
                "MA3151 Matrices and Calculus",
                "PH3151 Engineering Physics",
                "CY3151 Engineering Chemistry",
                "GE3151 Problem Solving and Python Programming",
                "GE3152 தமிழர்மரபு /Heritage of Tamils"
            ],
            "Semester II": [
                "HS3252 Professional English - II",
                "MA3251 Statistics and Numerical Methods",
                "PH3254 Physics for Electronics Engineering",
                "BE3254 Electrical and Instrumentation Engineering",
                "GE3251 Engineering Graphics",
                "EC3251 Circuit Analysis",
                "GE3252 தமிழரும் தொழில்நுட்பமும் /Tamils and Technology"
            ],
            "Semester III": [
                "MA3355 Random Processes and Linear Algebra",
                "CS3353 C Programming and Data Structures",
                "EC3354 Signals and Systems",
                "EC3353 Electronic Devices and Circuits",
                "EC3351 Control Systems",
                "EC3352 Digital Systems Design"
            ],
            "Semester IV": [
                "EC3452 Electromagnetic Fields",
                "EC3401 Networks and Security",
                "EC3451 Linear Integrated Circuits",
                "EC3492 Digital Signal Processing",
                "EC3491 Communication Systems",
                "GE3451 Environmental Sciences and Sustainability"
            ],
            "Semester V": [
                "EC3501 Wireless Communication",
                "EC3552 VLSI and Chip Design",
                "EC3551 Transmission lines and RF Systems"
            ],
            "Semester VI": [
                "ET3491 Embedded Systems and IOT Design",
                "CS3491 Artificial Intelligence and Machine Learning"
            ],
            "Semester VII": [
                "GE3791 Human Values and Ethics"
            ]
        },
        "CIVIL": {
            "Semester I": [
                "HS3152 Professional English - I",
                "MA3151 Matrices and Calculus",
                "PH3151 Engineering Physics",
                "CY3151 Engineering Chemistry",
                "GE3151 Problem Solving and Python Programming",
                "GE3152 தமிழர்மரபு / Heritage of Tamils"
            ],
            "Semester II": [
                "HS3252 Professional English - II",
                "MA3251 Statistics and Numerical Methods",
                "PH3201 Physics for Civil Engineering",
                "BE3252 Basic Electrical, Electronics and Instrumentation Engineering",
                "GE3251 Engineering Graphics",
                "GE3252 தமிழரும் தொழில்நுட்பமும் / Tamils and Technology"
            ],
            "Semester III": [
                "MA3351 Transforms and Partial Differential Equations",
                "ME3351 Engineering Mechanics",
                "CE3301 Fluid Mechanics",
                "CE3302 Construction Materials and Technology",
                "CE3303 Water Supply and Wastewater Engineering",
                "CE3351 Surveying and Levelling"
            ],
            "Semester IV": [
                "CE3401 Applied Hydraulics Engineering",
                "CE3402 Strength of Materials",
                "CE3403 Concrete Technology",
                "CE3404 Soil Mechanics",
                "CE3405 Highway and Railway Engineering",
                "GE3451 Environmental Sciences and Sustainability"
            ],
            "Semester V": [
                "CE3501 Design of Reinforced Concrete Structural Elements",
                "CE3502 Structural Analysis I",
                "CE3503 Foundation Engineering"
            ],
            "Semester VI": [
                "CE3601 Design of Steel Structural Elements",
                "CE3602 Structural Analysis II",
                "AG3601 Engineering Geology"
            ],
            "Semester VII": [
                "CE3701 Estimation, Costing and Valuation Engineering",
                "AI3404 Hydrology and Water Resources Engineering",
                "GE3791 Human Values and Ethics",
                "GE3752 Total Quality Management"
            ]
        },
        "AIDS": {
            "Semester I": [
                "HS3152 Professional English - I",
                "MA3151 Matrices and Calculus",
                "PH3151 Engineering Physics",
                "CY3151 Engineering Chemistry",
                "GE3151 Problem Solving and Python Programming",
                "GE3152 தமிழர்மரபு /Heritage of Tamils"
            ],
            "Semester II": [
                "HS3252 Professional English - II",
                "MA3251 Statistics and Numerical Methods",
                "PH3256 Physics for Information Science",
                "BE3251 Basic Electrical and Electronics Engineering",
                "GE3251 Engineering Graphics",
                "AD3251 Data Structures Design",
                "GE3252 தமிழரும் தொழில்நுட்பமும் /Tamils and Technology"
            ],
            "Semester III": [
                "MA3354 Discrete Mathematics",
                "CS3351 Digital Principles and Computer Organization",
                "AD3391 Database Design and Management",
                "AD3351 Design and Analysis of Algorithms",
                "AD3301 Data Exploration and Visualization",
                "AL3391 Artificial Intelligence"
            ],
            "Semester IV": [
                "MA3391 Probability and Statistics",
                "AL3452 Operating Systems",
                "AL3451 Machine Learning",
                "AD3491 Fundamentals of Data Science and Analytics",
                "CS3591 Computer Networks",
                "GE3451 Environmental Sciences and Sustainability"
            ],
            "Semester V": [
                "AD3501 Deep Learning",
                "CW3551 Data and Information Security",
                "CS3551 Distributed Computing P",
                "CCS334 Big Data Analytics"
            ],
            "Semester VI": [
                "CS3691 Embedded Systems and IoT"
            ],
            "Semester VII": [
                "GE3791 Human Values and Ethics"
            ]
        },
        "IT": {
            "Semester I": [
                "HS3152 Professional English - I",
                "MA3151 Matrices and Calculus",
                "PH3151 Engineering Physics",
                "CY3151 Engineering Chemistry",
                "GE3151 Problem Solving and Python Programming",
                "GE3152 தமிழர்மரபு /Heritage of Tamils"
            ],
            "Semester II": [
                "HS3252 Professional English - II",
                "MA3251 Statistics and Numerical Methods",
                "PH3256 Physics for Information Science",
                "BE3251 Basic Electrical and Electronics Engineering",
                "GE3251 Engineering Graphics",
                "CS3251 Programming in C",
                "GE3252 தமிழரும் தொழில்நுட்பமும் /Tamils and Technology"
            ],
            "Semester III": [
                "MA3354 Discrete Mathematics",
                "CS3351 Digital Principles and Computer Organization",
                "CS3352 Foundations of Data Science",
                "CD3291 Data Structures and Algorithms",
                "CS3391 Object Oriented Programming"
            ],
            "Semester IV": [
                "CS3452 Theory of Computation",
                "CS3491 Artificial Intelligence and Machine Learning",
                "CS3492 Database Management Systems",
                "IT3401 Web Essentials",
                "CS3451 Introduction to Operating Systems",
                "GE3451 Environmental Sciences and Sustainability"
            ],
            "Semester V": [
                "CS3591 Computer Networks",
                "IT3501 Full Stack Web Development",
                "CS3551 Distributed Computing",
                "CS3691 Embedded Systems and IoT"
            ],
            "Semester VI": [
                "CCS356 Object Oriented Software Engineering"
            ],
            "Semester VII": [
                "GE3791 Human Values and Ethics"
            ]
        }
    }


    for dept_name, semesters in SEMESTER_STRUCTURE.items():
        cursor.execute('SELECT id FROM departments WHERE name=%s', (dept_name,))
        dept_id_row = cursor.fetchone()
        if not dept_id_row:
            continue
        dept_id = dept_id_row[0]
        for sem_name, subjects in semesters.items():
            cursor.execute('INSERT IGNORE INTO semesters (name, department_id) VALUES (%s, %s)', (sem_name, dept_id))
            cursor.execute('SELECT id FROM semesters WHERE name=%s AND department_id=%s', (sem_name, dept_id))
            sem_id = cursor.fetchone()[0]
            for subject in subjects:
                cursor.execute('INSERT IGNORE INTO subjects (name, semester_id) VALUES (%s, %s)', (subject, sem_id))

    # --- lightweight migration: ensure uploader_id exists ---
    try:
        cursor.execute('PRAGMA table_info(materials)')
        cols = [r[1] for r in cursor.fetchall()]
        if 'uploader_id' not in cols:
            cursor.execute('ALTER TABLE materials ADD COLUMN uploader_id INTEGER')
    except Exception:
        pass
    
    # --- Add missing columns to users table ---
    try:
        cursor.execute('DESCRIBE users')
        existing_columns = [col[0] for col in cursor.fetchall()]
        
        if 'department' not in existing_columns:
            cursor.execute('ALTER TABLE users ADD COLUMN department VARCHAR(50)')
            print("Added department column to users table")
        
        if 'created_at' not in existing_columns:
            cursor.execute('ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            print("Added created_at column to users table")
        
        if 'last_login' not in existing_columns:
            cursor.execute('ALTER TABLE users ADD COLUMN last_login TIMESTAMP NULL')
            print("Added last_login column to users table")
    except Exception as e:
        print(f"Error adding columns to users table: {e}")
    
    conn.commit()
    conn.close()



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_all_departments():
    with get_db() as conn:
        departments = conn.execute('SELECT * FROM departments').fetchall()
    return departments

init_db()

# ========== SAMPLE USERS SETUP ==========
def create_sample_users():
    """Create sample users for testing different roles"""
    from werkzeug.security import generate_password_hash
    
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return
    
    try:
        cursor = conn.cursor()
        # Check if users already exist
        cursor.execute('SELECT COUNT(*) as count FROM users')
        existing_users = cursor.fetchone()[0]
        if existing_users > 0:
            print("Users already exist, skipping sample user creation.")
            return
        
        # Create sample users
        sample_users = [
            ('admin@college.local', 'adminpass', 'admin', 'System Administrator'),
            ('faculty@college.local', 'facultypass', 'faculty', 'Dr. Faculty Member'),
            ('student@college.local', 'studentpass', 'student', 'John Student')
        ]
        
        for email, password, role, name in sample_users:
            password_hash = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (email, password_hash, role, name) VALUES (%s, %s, %s, %s)',
                (email, password_hash, role, name)
            )
        
        conn.commit()
        print("Sample users added successfully!")
    except Exception as e:
        print(f"Error creating sample users: {e}")
    finally:
        conn.close()

# Create sample users on startup
create_sample_users()

# == ROUTES: STUDENT SIDE ==
@app.route('/')
def college_home():
    conn = get_db_connection()
    if not conn:
        return "Database connection error", 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT e.*, d.name as department_name
            FROM events e
            JOIN departments d ON e.department_id = d.id
            ORDER BY event_date DESC, created_at DESC
            LIMIT 5
        ''')
        events = cursor.fetchall()
        
        cursor.execute('SELECT * FROM departments')
        departments = cursor.fetchall()
        cursor.close()
        
        return render_template('college_home.html', current_year=datetime.now().year, events=events, departments=departments)
    finally:
        conn.close()


@app.route('/college_home')
@login_required
def college_home_redirect():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments')
    departments = cursor.fetchall()
    cursor.close()
    return render_template('index.html', departments=departments)


@app.route("/materials")
@login_required
def index():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)  # dictionary=True gives rows as dicts
    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()
    cursor.close()
    return render_template("index.html", departments=departments)


@app.route('/department/<int:department_id>')
def show_semesters(department_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments WHERE id=%s', (department_id,))
    department = cursor.fetchone()
    if not department:
        cursor.close()
        abort(404)
    cursor.execute('SELECT * FROM semesters WHERE department_id=%s', (department_id,))
    semesters = cursor.fetchall()
    cursor.close()
    return render_template('semesters.html', department=department, semesters=semesters)


@app.route('/semesters/<int:department_id>')
@login_required
def show_semesters_login_required(department_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments WHERE id=%s', (department_id,))
    department = cursor.fetchone()
    if not department:
        cursor.close()
        abort(404)
    cursor.execute('SELECT * FROM semesters WHERE department_id=%s', (department_id,))
    semesters = cursor.fetchall()
    cursor.close()
    return render_template('semesters.html', department=department, semesters=semesters)


@app.route('/department/<int:department_id>/semester/<int:semester_id>')
def show_subjects(department_id, semester_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments WHERE id=%s', (department_id,))
    department = cursor.fetchone()
    if not department:
        cursor.close()
        abort(404)
    cursor.execute('SELECT * FROM semesters WHERE id=%s AND department_id=%s', (semester_id, department_id))
    semester = cursor.fetchone()
    if not semester:
        cursor.close()
        abort(404)
    cursor.execute('SELECT * FROM subjects WHERE semester_id=%s', (semester_id,))
    subjects = cursor.fetchall()
    cursor.close()
    return render_template('subjects.html',
                           department=department,
                           semester=semester,
                           subjects=subjects,
                           department_id=department_id)


@app.route("/materials/<int:subject_id>")
@login_required
def show_materials(subject_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM subjects WHERE id=%s", (subject_id,))
    subject = cursor.fetchone()

    cursor.execute("SELECT * FROM materials WHERE subject_id=%s", (subject_id,))
    materials = cursor.fetchall()

    # Fetch all questions for these materials
    cursor.execute("""
        SELECT m.id as msg_id, m.encrypted_message, m.created_at,
               u.name as student_name, mat.original_filename as file_name, mat.id as material_id
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        JOIN materials mat ON m.material_id = mat.id
        WHERE mat.subject_id = %s AND m.reply_to IS NULL
        ORDER BY m.created_at DESC
    """, (subject_id,))
    questions = cursor.fetchall()

    # Organize into {material_id: {q_id: {q, replies}}}
    q_dict = {}
    for q in questions:
        cursor.execute("""
            SELECT m.encrypted_message, m.created_at, u.name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.reply_to = %s
            ORDER BY m.created_at ASC
        """, (q["msg_id"],))
        replies = cursor.fetchall()

        if q["material_id"] not in q_dict:
            q_dict[q["material_id"]] = {}
        q_dict[q["material_id"]][q["msg_id"]] = {"q": q, "replies": replies}

    cursor.close()
    return render_template("materials.html", subject=subject, materials=materials, questions=q_dict)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT original_filename FROM materials WHERE filename=%s', (filename,))
    mat = cursor.fetchone()
    cursor.close()
    if mat:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, download_name=mat['original_filename'])
    abort(404)


@app.route('/gpa-cgpa')
def gpa_cgpa_page():
    return render_template('gpa_cgpa.html')


# == ROUTES: ADMIN SIDE ==
@app.route('/admin/events/new', methods=['GET', 'POST'])
@auth.login_required
def admin_events_new():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments')
    departments = cursor.fetchall()

    if request.method == 'POST':
        department_id = request.form['department_id']
        title = request.form['title']
        content = request.form['content']
        author = request.form.get('author')
        event_date = request.form.get('event_date')
        image_url = request.form.get('image_url') or None

        cursor.execute(
            '''INSERT INTO events (department_id, title, content, author, event_date, image_url)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (department_id, title, content, author, event_date, image_url)
        )
        conn.commit()
        cursor.close()
        flash("Event posted!")
        return redirect(url_for('events_all'))

    cursor.close()
    return render_template('admin_events_new.html', departments=departments)


@app.route('/admin/upload', methods=['GET', 'POST'])
@auth.login_required
def admin_upload():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments')
    departments = cursor.fetchall()

    if request.method == 'POST':
        department_id = request.form.get('department')
        semester_id = request.form.get('semester')
        subject_id = request.form.get('subject')
        file = request.files.get('file')
        if not department_id or not semester_id or not subject_id or not file or not allowed_file(file.filename):
            cursor.close()
            flash('Please select department, semester, subject, and a valid file.')
            return redirect(request.url)

        original_filename = file.filename
        saved_filename = f"{subject_id}_{original_filename}".replace(" ", "_")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        file.save(filepath)

        cursor.execute(
            'INSERT INTO materials (subject_id, filename, original_filename) VALUES (%s, %s, %s)',
            (subject_id, saved_filename, original_filename)
        )
        conn.commit()
        cursor.close()
        flash('File uploaded successfully!')
        return redirect(url_for('admin_upload'))

    cursor.close()
    return render_template('admin_upload.html', departments=departments)


@app.route('/admin/semesters/<int:department_id>')
@auth.login_required
def admin_get_semesters(department_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM semesters WHERE department_id=%s', (department_id,))
    semesters = cursor.fetchall()
    cursor.close()
    data = [{'id': s['id'], 'name': s['name']} for s in semesters]
    return jsonify({"semesters": data})


@app.route('/admin/subjects/<int:semester_id>')
@auth.login_required
def admin_get_subjects(semester_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM subjects WHERE semester_id=%s', (semester_id,))
    subjects = cursor.fetchall()
    cursor.close()
    data = [{'id': s['id'], 'name': s['name']} for s in subjects]
    return jsonify({"subjects": data})


@app.route('/admin/delete_material/<int:material_id>', methods=['POST'])
@login_required
def delete_material(material_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM materials WHERE id = %s', (material_id,))
    material = cursor.fetchone()
    if not material:
        cursor.close()
        flash('Material not found', 'warning')
        return redirect(request.referrer or url_for('index'))

    can_delete = False
    if current_user.role == 'admin':
        can_delete = True
    elif current_user.role == 'faculty':
        can_delete = (material.get('uploader_id') == current_user.id)

    if not can_delete:
        cursor.close()
        flash('You are not allowed to delete this material.', 'danger')
        return redirect(request.referrer or url_for('index'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], material['filename'])
    if os.path.exists(filepath):
        os.remove(filepath)

    cursor.execute('DELETE FROM materials WHERE id = %s', (material_id,))
    conn.commit()
    cursor.close()
    flash('Material deleted successfully!', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/admin/department-achievements/new', methods=['GET', 'POST'])
@auth.login_required
def admin_department_achievement_new():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments')
    departments = cursor.fetchall()

    if request.method == 'POST':
        department_id = request.form['department_id']
        title = request.form['title']
        description = request.form['description']
        image_url = request.form.get('image_url') or None

        if not department_id or not title:
            cursor.close()
            flash('Department and Title are required!')
            return redirect(request.url)

        cursor.execute('''
            INSERT INTO department_achievements (department_id, title, description, image_url)
            VALUES (%s, %s, %s, %s)
        ''', (department_id, title, description, image_url))
        conn.commit()
        cursor.close()
        flash('Achievement added successfully!')
        return redirect(url_for('admin_department_achievement_new'))

    cursor.close()
    return render_template('admin_department_achievement_new.html', departments=departments)


# == API ENDPOINTS ==
@app.route('/api/departments')
def api_get_departments():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments')
    departments = cursor.fetchall()
    cursor.close()
    data = [{'id': d['id'], 'name': d['name']} for d in departments]
    return jsonify(data)


@app.route('/events')
def events_all():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT e.*, d.name as department_name FROM events e
        JOIN departments d ON e.department_id = d.id
        ORDER BY event_date DESC, created_at DESC
    ''')
    events = cursor.fetchall()
    cursor.close()
    return render_template('events.html', events=events)


@app.route('/events/<int:department_id>')
def events_by_dept(department_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments WHERE id=%s', (department_id,))
    dept = cursor.fetchone()
    cursor.execute('''
        SELECT * FROM events WHERE department_id=%s
        ORDER BY event_date DESC, created_at DESC
    ''', (department_id,))
    events = cursor.fetchall()
    cursor.close()
    return render_template('events.html', department=dept, events=events)


@app.route('/api/semesters/<int:department_id>')
def api_get_semesters(department_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM semesters WHERE department_id=%s', (department_id,))
    semesters = cursor.fetchall()
    cursor.close()
    data = [{'id': s['id'], 'name': s['name']} for s in semesters]
    return jsonify(data)


@app.route('/api/subjects/<int:semester_id>')
def api_get_subjects(semester_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM subjects WHERE semester_id=%s', (semester_id,))
    subjects = cursor.fetchall()
    cursor.close()
    data = [{'id': s['id'], 'name': s['name']} for s in subjects]
    return jsonify(data)


@app.route('/api/materials/<int:subject_id>')
def api_get_materials(subject_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM materials WHERE subject_id=%s', (subject_id,))
    materials = cursor.fetchall()
    cursor.close()
    data = [{'id': m['id'], 'filename': m['filename'], 'original_filename': m['original_filename']} for m in materials]
    return jsonify(data)


@app.route('/api/upload', methods=['POST'])
@auth.login_required
def api_upload():
    file = request.files.get('file')
    subject_id = request.form.get('subject')
    if not subject_id or not file or not allowed_file(file.filename):
        return jsonify({'error': 'Missing subject or invalid file'}), 400

    original_filename = file.filename
    saved_filename = f"{subject_id}_{original_filename}".replace(" ", "_")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(filepath)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        'INSERT INTO materials (subject_id, filename, original_filename) VALUES (%s, %s, %s)',
        (subject_id, saved_filename, original_filename)
    )
    conn.commit()
    cursor.close()
    return jsonify({'message': 'File uploaded successfully'})


@app.route('/api/materials/<int:material_id>', methods=['DELETE'])
@auth.login_required
def api_delete_material(material_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM materials WHERE id = %s', (material_id,))
    material = cursor.fetchone()
    if not material:
        cursor.close()
        return jsonify({'error': 'Material not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], material['filename'])
    if os.path.exists(filepath):
        os.remove(filepath)

    cursor.execute('DELETE FROM materials WHERE id = %s', (material_id,))
    conn.commit()
    cursor.close()
    return jsonify({'message': 'Material deleted successfully'})


@app.route('/verify_departments')
def verify_departments():
    # If get_all_departments() already returns dicts, keep it. Otherwise fetch with MySQL as shown elsewhere.
    departments = get_all_departments()
    department_list = [dict(dept) for dept in departments]
    return jsonify({"departments": department_list})


@app.route('/department-highlights')
def department_highlights():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments')
    departments = cursor.fetchall()
    cursor.close()
    return render_template('department_highlights.html', departments=departments)


@app.route('/department/<int:department_id>/achievements')
def department_achievements(department_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments WHERE id=%s', (department_id,))
    department = cursor.fetchone()
    if not department:
        cursor.close()
        abort(404)

    cursor.execute('''
        SELECT * FROM department_achievements 
        WHERE department_id=%s
        ORDER BY created_at DESC
    ''', (department_id,))
    achievements = cursor.fetchall()
    cursor.close()
    return render_template('department_achievements.html',
                           department=department,
                           achievements=achievements)


# == TEMPLATE FILTERS ==
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%b %d, %Y'):
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value
    return value.strftime(format)


@app.template_filter("b64decode")
def b64decode_filter(s):
    try:
        return base64.b64decode(s).decode("utf-8")
    except Exception:
        return "[Invalid/Corrupted message]"


# == AUTHENTICATION ROUTES ==
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form['email'].strip()
        password = request.form['password']
        selected_role = request.form['role']

        conn = get_db_connection()
        if not conn:
            flash("Database connection error", "danger")
            return render_template('login.html')
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            row = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if row:
            user = load_user_from_row(row)
            if user.check_password(password):
                if user.role != selected_role:
                    flash(f"You selected role '{selected_role}', but your account is registered as '{user.role}'. Please select the correct role.", "warning")
                    return redirect(url_for('login'))
                login_user(user)
                flash("Logged in successfully.", "success")
                if user.role == 'faculty':
                    return redirect(url_for('faculty_dashboard'))
                elif user.role == 'student':
                    return redirect(url_for('index'))
                elif user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
            else:
                flash("Invalid password.", "danger")
        else:
            flash("User not found.", "danger")
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))


# == REGISTER ROUTE ==
@app.route("/register", methods=["GET", "POST"])
def user_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password")
        role = request.form.get("role")

        if not (name and email and password and role):
            flash("All fields are required.", "warning")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                """,
                (name, email, hashed_pw, role),
            )
            conn.commit()
            flash("✅ Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception:
            conn.rollback()
            flash("❌ Email already exists. Please log in.", "danger")
        finally:
            cursor.close()

    return render_template("register.html")


# == DASHBOARD ROUTES ==
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        abort(403)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE role='faculty'")
    faculties = cursor.fetchall()
    cursor.execute("SELECT * FROM users WHERE role='student'")
    students = cursor.fetchall()
    cursor.close()
    return render_template('admin_dashboard.html', faculties=faculties, students=students)


@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != "student":
        abort(403)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT m.*, s.name as subject_name
        FROM materials m
        JOIN subjects s ON m.subject_id = s.id
        ORDER BY m.id DESC LIMIT 10
    ''')
    recent_materials = cursor.fetchall()
    cursor.close()
    return render_template('student_dashboard.html', materials=recent_materials)


@app.route('/download/<int:material_id>')
@login_required
def download_material(material_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM materials WHERE id=%s', (material_id,))
    material = cursor.fetchone()
    cursor.close()
    if not material:
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], material['filename'], as_attachment=True, download_name=material['original_filename'])


@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != "admin":
        abort(403)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        email = request.form['email']
        name = request.form.get('name', '')
        password = request.form['password']
        role = request.form['role']
        department = request.form.get('department', '')

        cursor.execute('SELECT 1 FROM users WHERE email=%s', (email,))
        exists = cursor.fetchone()
        if exists:
            flash('User already exists', 'warning')
        else:
            pw_hash = generate_password_hash(password)
            cursor.execute('INSERT INTO users (email, password_hash, role, name, department) VALUES (%s, %s, %s, %s, %s)',
                           (email, pw_hash, role, name, department))
            conn.commit()
            flash('User added.', 'success')

    cursor.execute('SELECT * FROM departments')
    departments = cursor.fetchall()
    
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    cursor.close()
    return render_template('manage_users.html', users=users, departments=departments)

@app.route('/admin/add_user', methods=['POST'])
@login_required
def add_user():
    if current_user.role != "admin":
        abort(403)

    email = request.form['email']
    name = request.form['name']
    password = request.form['password']
    role = request.form.get('role', 'student')  # Get role from form
    department = request.form.get('department', '')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT 1 FROM users WHERE email=%s', (email,))
    exists = cursor.fetchone()
    if exists:
        flash('Student already exists', 'warning')
    else:
        pw_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (email, password_hash, role, name, department) VALUES (%s, %s, %s, %s, %s)',
                       (email, pw_hash, role, name, department))
        conn.commit()
        flash('Student added successfully.', 'success')

    cursor.close()
    return redirect(url_for('manage_users'))


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        abort(403)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('DELETE FROM users WHERE id=%s AND role != %s', (user_id, 'admin'))
    conn.commit()
    cursor.close()
    flash("User deleted.", "success")
    return redirect(url_for('manage_users'))

@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    if current_user.role != "admin":
        abort(403)

    name = request.form['name']
    email = request.form['email']
    department = request.form.get('department', '')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('UPDATE users SET name=%s, email=%s, department=%s WHERE id=%s', 
                   (name, email, department, user_id))
    conn.commit()
    cursor.close()
    flash("User updated successfully.", "success")
    return redirect(url_for('student_records'))


@app.route("/admin/students")
def student_records():
    department = request.args.get('department', '')
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if department:
        cursor.execute("SELECT * FROM users WHERE role='student' AND department=%s", (department,))
    else:
        cursor.execute("SELECT * FROM users WHERE role='student'")
        
    students = cursor.fetchall()
    cursor.close()
    return render_template("student_records.html", students=students, selected_department=department)


# == FACULTY ROUTES ==
@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != 'faculty':
        flash("Access denied.", "danger")
        return redirect(url_for("index"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # fetch materials uploaded by this faculty
    cursor.execute(
        "SELECT * FROM materials WHERE uploader_id = %s", (current_user.id,)
    )
    materials = cursor.fetchall()

    # fetch all student questions for those materials
    cursor.execute("""
        SELECT m.id as msg_id, m.encrypted_message, m.created_at,
               s.name as student_name, mat.original_filename as file_name
        FROM messages m
        JOIN users s ON m.sender_id = s.id
        JOIN materials mat ON m.material_id = mat.id
        WHERE mat.uploader_id = %s AND m.reply_to IS NULL
        ORDER BY m.created_at DESC
    """, (current_user.id,))
    questions = cursor.fetchall()

    # fetch replies for each question
    q_dict = {}
    for q in questions:
        cursor.execute("""
            SELECT m.encrypted_message, m.created_at, u.name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.reply_to = %s
            ORDER BY m.created_at ASC
        """, (q["msg_id"],))
        replies = cursor.fetchall()
        q_dict[q["msg_id"]] = {"q": q, "replies": replies}

    cursor.close()
    return render_template(
        "faculty_dashboard.html",
        materials=materials,
        questions=q_dict
    )


@app.route('/faculty/my-materials')
@login_required
def faculty_my_materials():
    if current_user.role != 'faculty':
        flash("Access denied.", "danger")
        return redirect(url_for("index"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT m.id, m.original_filename, m.filename,
               s.name AS subject_name,
               sem.name AS semester_name,
               d.name AS department_name
        FROM materials m
        JOIN subjects s ON m.subject_id = s.id
        JOIN semesters sem ON s.semester_id = sem.id
        JOIN departments d ON sem.department_id = d.id
        WHERE m.uploader_id = %s
        ORDER BY m.id DESC
        """,
        (current_user.id,),
    )
    materials = cursor.fetchall()
    cursor.close()
    return render_template("faculty_my_materials.html", materials=materials)


@app.route('/faculty/delete-material/<int:material_id>', methods=['POST'])
@login_required
def faculty_delete_material(material_id):
    if current_user.role != 'faculty':
        flash("Access denied.", "danger")
        return redirect(url_for("index"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM materials WHERE id=%s AND uploader_id=%s",
        (material_id, current_user.id)
    )
    mat = cursor.fetchone()

    if not mat:
        cursor.close()
        flash("You don't have permission to delete this file.", "danger")
        return redirect(url_for("faculty_my_materials"))

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], mat["filename"])
    if os.path.exists(filepath):
        os.remove(filepath)

    cursor.execute("DELETE FROM materials WHERE id=%s", (material_id,))
    conn.commit()
    cursor.close()

    flash("Material deleted successfully.", "success")
    return redirect(url_for("faculty_my_materials"))


@app.route('/faculty/semesters/<int:dept_id>')
@login_required
def faculty_semesters(dept_id):
    if current_user.role != 'faculty':
        return jsonify({"error": "Access denied"}), 403

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM semesters WHERE department_id=%s", (dept_id,)
    )
    semesters = cursor.fetchall()
    cursor.close()
    return jsonify({"semesters": [dict(row) for row in semesters]})


@app.route('/faculty/subjects/<int:semester_id>')
@login_required
def faculty_subjects(semester_id):
    if current_user.role != 'faculty':
        return jsonify({"error": "Access denied"}), 403

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM subjects WHERE semester_id=%s", (semester_id,)
    )
    subjects = cursor.fetchall()
    cursor.close()
    return jsonify({"subjects": [dict(row) for row in subjects]})


@app.route('/faculty/upload', methods=['GET', 'POST'])
@login_required
def faculty_upload():
    if current_user.role != 'faculty':
        flash("Access denied.", "danger")
        return redirect(url_for("index"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM departments')
    departments = cursor.fetchall()

    if request.method == 'POST':
        department_id = request.form.get('department')
        semester_id = request.form.get('semester')
        subject_id = request.form.get('subject')
        file = request.files.get('file')

        if not department_id or not semester_id or not subject_id or not file or not allowed_file(file.filename):
            cursor.close()
            flash('Please select department, semester, subject, and a valid file.', 'warning')
            return redirect(request.url)

        original_filename = file.filename
        saved_filename = f"{subject_id}_{secure_filename(original_filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        file.save(filepath)

        cursor.execute(
            'INSERT INTO materials (subject_id, filename, original_filename, uploader_id) VALUES (%s, %s, %s, %s)',
            (subject_id, saved_filename, original_filename, current_user.id)
        )
        conn.commit()
        cursor.close()
        flash('Material uploaded successfully!', 'success')
        return redirect(url_for('faculty_my_materials'))

    cursor.close()
    return render_template('faculty_upload.html', departments=departments)


# == QUESTION/ANSWER SYSTEM ==
@app.route("/ask/<int:material_id>", methods=["POST"])
@login_required
def ask_question(material_id):
    if current_user.role != "student":
        flash("Login as student to ask questions.")
        return redirect(url_for("login"))

    encrypted_msg = request.form.get("encrypted_message")
    if not encrypted_msg:
        flash("Message cannot be empty.")
        return redirect(url_for("show_materials", subject_id=request.form.get("subject_id")))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT uploader_id FROM materials WHERE id=%s",
        (material_id,)
    )
    material = cursor.fetchone()
    if not material:
        cursor.close()
        flash("Invalid material.")
        return redirect(url_for("index"))

    receiver_id = material["uploader_id"]

    cursor.execute("""
        INSERT INTO messages (material_id, sender_id, receiver_id, encrypted_message)
        VALUES (%s, %s, %s, %s)
    """, (material_id, current_user.id, receiver_id, encrypted_msg))
    conn.commit()
    cursor.close()

    flash("Your question has been sent securely!")
    return redirect(url_for("show_materials", subject_id=request.form.get("subject_id")))


# Faculty/Admin → view questions with replies
@app.route("/faculty/questions")
@login_required
def faculty_questions():
    if current_user.role not in ("faculty", "admin"):
        flash("Login as faculty/admin to view questions.")
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # fetch top-level questions
    cursor.execute("""
        SELECT m.id, m.encrypted_message, m.created_at,
               s.name AS student_name, mat.original_filename AS file_name
        FROM messages m
        JOIN users s   ON m.sender_id = s.id
        JOIN materials mat ON m.material_id = mat.id
        WHERE m.receiver_id = %s AND m.reply_to IS NULL
        ORDER BY m.created_at DESC
    """, (current_user.id,))
    questions = cursor.fetchall()

    # attach replies
    q_list = []
    for q in questions:
        cursor.execute("""
            SELECT r.id, r.encrypted_message, r.created_at,
                   u.name AS sender_name
            FROM messages r
            JOIN users u ON r.sender_id = u.id
            WHERE r.reply_to = %s
            ORDER BY r.created_at ASC
        """, (q["id"],))
        replies = cursor.fetchall()

        q_dict = dict(q)
        q_dict["replies"] = [dict(r) for r in replies]
        q_list.append(q_dict)

    cursor.close()
    return render_template("faculty_questions.html", questions=q_list)


# Faculty/Admin → reply
@app.route("/reply/<int:msg_id>", methods=["POST"])
@login_required
def reply_question(msg_id):
    if current_user.role not in ("faculty", "admin"):
        flash("Login as faculty/admin to reply.")
        return redirect(url_for("login"))

    encrypted_msg = (request.form.get("encrypted_message") or "").strip()
    if not encrypted_msg:
        flash("Reply cannot be empty.")
        return redirect(url_for("faculty_questions"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT sender_id, material_id FROM messages WHERE id=%s",
        (msg_id,)
    )
    parent = cursor.fetchone()
    if not parent:
        cursor.close()
        flash("Original message not found.")
        return redirect(url_for("faculty_questions"))

    cursor.execute("""
        INSERT INTO messages (material_id, sender_id, receiver_id, encrypted_message, reply_to)
        VALUES (%s, %s, %s, %s, %s)
    """, (parent["material_id"], current_user.id, parent["sender_id"], encrypted_msg, msg_id))
    conn.commit()
    cursor.close()

    flash("Reply sent securely!")
    return redirect(url_for("faculty_questions"))


if __name__ == "__main__":
    app.run(debug=True)
