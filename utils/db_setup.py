import os
import sqlite3
from werkzeug.security import generate_password_hash
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(user_email, role, action, status="Success"):
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO activity_logs (user_email, role, action, status) VALUES (?, ?, ?, ?)",
            (user_email, role, action, status)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        target_role TEXT DEFAULT 'Full Stack Developer',
        college TEXT DEFAULT 'St. Ann''s College of Engineering & Technology',
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        raw_text TEXT,
        ats_score INTEGER NOT NULL,
        readiness_score INTEGER NOT NULL,
        matched_skills TEXT,
        missing_skills TEXT,
        suggestions TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT NOT NULL,
        job_type TEXT NOT NULL DEFAULT 'Full-Time',
        package TEXT NOT NULL,
        required_skills TEXT NOT NULL,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        status TEXT DEFAULT 'Applied',
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, job_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        role TEXT NOT NULL,
        action TEXT NOT NULL,
        status TEXT DEFAULT 'Success',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed Default Admin if not exists
    admin_email = os.environ.get("ADMIN_EMAIL", "sivasainakka35@gmail.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "sivasai_7013")

    admin_exists = cur.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
    if not admin_exists:
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, role, target_role) VALUES (?, ?, ?, ?, ?)",
            ("Sivasai Nakka", admin_email, generate_password_hash(admin_password), "admin", "System Admin")
        )

    # Seed Demo Student if not exists
    student_exists = cur.execute("SELECT id FROM users WHERE email = ?", ("rahul@student.com",)).fetchone()
    if not student_exists:
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, role, target_role, college) VALUES (?, ?, ?, ?, ?, ?)",
            ("Rahul Kumar", "rahul@student.com", generate_password_hash("Student@123"), "student", "Full Stack Developer", "St. Ann's College of Engineering & Technology")
        )
        student_id = cur.lastrowid

        sample_resumes = [
            (
                student_id,
                "Rahul_Resume_v1.pdf",
                "Rahul Kumar | rahul@student.com | +91 9876543210 | github.com/rahulkumar | Education: B.Tech CSE | Skills: Python, HTML, CSS, SQL, Git | Projects: Student Portal Website developed using Python and SQL.",
                72,
                68,
                "Python, HTML, CSS, SQL, Git",
                "JavaScript, React, REST API, Docker",
                "Add clickable LinkedIn URL.|Strengthen Full Stack Developer alignment with React and REST APIs.|Quantify project impact with metrics."
            ),
            (
                student_id,
                "Rahul_FullStack_2026.pdf",
                "Rahul Kumar | rahul@student.com | +91 9876543210 | github.com/rahulkumar | linkedin.com/in/rahulkumar | Education: B.Tech CSE (CGPA 8.6) | Technical Skills: Python, Flask, JavaScript, HTML, CSS, React, SQL, Git, REST API | Projects: Developed ResumeNexovora AI career platform improving resume ATS readiness by 40%. | Internship: Web Developer Intern | Certifications: NPTEL Cloud Computing",
                86,
                82,
                "Python, Flask, JavaScript, HTML, CSS, React, SQL, Git, REST API",
                "Node.js, Docker, TypeScript",
                "Great structure! Tailor your top 3 project bullets specifically to each Job Description before applying."
            )
        ]
        cur.executemany(
            """INSERT INTO resumes (user_id, file_name, raw_text, ats_score, readiness_score, matched_skills, missing_skills, suggestions)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            sample_resumes
        )

    # Seed Initial Jobs & Internships if empty
    job_count = cur.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    if job_count == 0:
        initial_jobs = [
            ("Frontend & Full Stack Developer", "TCS", "Hyderabad / Bengaluru", "Full-Time", "4.5 - 7.0 LPA", "HTML, CSS, JavaScript, React, Python, SQL", "Build modern enterprise web applications for global clients."),
            ("Python & Cloud Associate Engineer", "Infosys", "Bengaluru / Pune", "Full-Time", "5.0 - 6.5 LPA", "Python, SQL, Linux, AWS, Git, REST API", "Develop scalable backend APIs and cloud-native microservices."),
            ("Data Analyst Trainee", "Accenture", "Hyderabad / Chennai", "Full-Time", "4.5 LPA", "Python, SQL, Excel, Power BI, Statistics", "Analyze business datasets and create interactive executive dashboards."),
            ("Software Developer Intern (2026 Batch)", "Zoho", "Chennai", "Internship", "₹25,000 / month", "Python, JavaScript, HTML, CSS, SQL, Git", "Work alongside product engineers on SaaS modules with PPO opportunity."),
            ("IoT & Edge Systems Engineer", "Bosch Global", "Bengaluru / Coimbatore", "Full-Time", "6.0 - 8.0 LPA", "Python, C++, Embedded C, IoT, MQTT, Linux", "Design smart industrial IoT sensor pipelines and edge telemetry."),
            ("AI / ML Research Intern", "Microsoft Research India", "Hyderabad", "Internship", "₹45,000 / month", "Python, Machine Learning, Deep Learning, PyTorch, NLP", "Assist in building LLM evaluation and document intelligence workflows.")
        ]
        cur.executemany(
            """INSERT INTO jobs (title, company, location, job_type, package, required_skills, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            initial_jobs
        )

        if not student_exists:
            cur.execute("INSERT OR IGNORE INTO applications (user_id, job_id, status) VALUES (2, 1, 'Shortlisted')")

    conn.commit()
    conn.close()