import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from utils.db_setup import init_db, get_db, log_activity
from utils.decorators import student_required, admin_required
from utils.resume_parser import extract_text_from_file
from utils.ats_scorer import analyze_resume_text, match_job_description, ROLE_SKILLS

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize SQLite database & seed data on startup
init_db()

ROADMAPS = {
    "Full Stack Developer": [
        ("1. Build Strong Web Foundations", "Master semantic HTML5, modern CSS3 (Flexbox/Grid), and core JavaScript (ES6+)."),
        ("2. Frontend Framework & UI Craft", "Build interactive SPAs using React, state management, and responsive component design."),
        ("3. Backend APIs & Databases", "Develop RESTful services with Python (Flask/Django) or Node.js connected to SQL/NoSQL databases."),
        ("4. Full-Stack Capstone Projects", "Deploy 2+ end-to-end projects with authentication, Git version control, and cloud hosting."),
        ("5. Placement & Interview Readiness", "Practice DSA fundamentals, system design basics, and ATS-tailored applications.")
    ],
    "Data Analyst": [
        ("1. Spreadsheet & SQL Mastery", "Master advanced Excel formulas, pivot tables, and complex SQL joins & aggregations."),
        ("2. Python for Data Wrangling", "Use Pandas and NumPy to clean, transform, and explore real-world datasets."),
        ("3. BI Dashboards & Storytelling", "Build interactive executive dashboards in Power BI or Tableau."),
        ("4. Statistics & Predictive Basics", "Apply hypothesis testing, A/B testing, and regression modeling."),
        ("5. Portfolio & Case Studies", "Publish 3 end-to-end domain analysis case studies on GitHub.")
    ],
    "Cloud & DevOps Engineer": [
        ("1. Linux & Networking Essentials", "Gain command-line fluency, shell scripting, DNS, HTTP/S, and firewall fundamentals."),
        ("2. Core Cloud Platforms (AWS/Azure)", "Configure IAM, EC2/VMs, S3 storage, VPC networking, and serverless functions."),
        ("3. Containerization with Docker", "Package applications into lightweight Docker images and multi-container Compose stacks."),
        ("4. CI/CD Pipelines & Kubernetes", "Automate testing and deployments using GitHub Actions, Jenkins, and Kubernetes."),
        ("5. Infrastructure as Code & Monitoring", "Provision cloud infra with Terraform and monitor uptime with Prometheus/Grafana.")
    ],
    "IoT & Embedded Engineer": [
        ("1. Embedded C/C++ & Microcontrollers", "Program ARM Cortex, ESP32, and Arduino boards using GPIO, UART, SPI, and I2C."),
        ("2. Sensors, Actuators & Edge Logic", "Interface environmental/industrial sensors and implement real-time filtering."),
        ("3. IoT Protocols & Connectivity", "Implement MQTT, HTTP, BLE, and LoRaWAN telemetry pipelines."),
        ("4. Cloud IoT & Edge Analytics", "Stream device telemetry to AWS IoT / ThingsBoard with Python dashboards."),
        ("5. End-to-End Hardware Prototype", "Build and document a complete Industrial or Smart Home IoT prototype.")
    ],
    "AI / ML Engineer": [
        ("1. Python, Math & Data Foundations", "Master Python, linear algebra, probability, Pandas, and Scikit-Learn."),
        ("2. Supervised & Unsupervised ML", "Train and evaluate classification, regression, and clustering models."),
        ("3. Deep Learning & Neural Networks", "Build CNNs and Transformers using PyTorch or TensorFlow."),
        ("4. NLP & Applied LLM Systems", "Create RAG pipelines, embeddings search, and intelligent document analyzers."),
        ("5. Model Deployment & MLOps", "Serve ML models via FastAPI/Flask APIs with evaluation benchmarks.")
    ]
}

INTERVIEW_QUESTIONS = [
    ("Technical", "Explain how an ATS (Applicant Tracking System) parses and ranks student resumes.",
     "ATS software extracts plain text from PDF/DOCX files, categorizes standard sections (Education, Skills, Projects, Experience), and matches role-specific keywords and measurable outcomes against the job description."),
    ("Technical", "What is the difference between SQL and NoSQL databases, and when would you use each?",
     "SQL databases (like PostgreSQL, SQLite, MySQL) use structured tables with strict schemas and ACID transactions—ideal for user accounts and financial/application records. NoSQL databases (like MongoDB) store flexible JSON-like documents—great for rapidly evolving unstructured data."),
    ("Technical", "How do you secure user authentication in a web application?",
     "Never store plain-text passwords; hash them using salted algorithms like PBKDF2/bcrypt (Werkzeug), enforce role-based access control (RBAC) on protected routes, validate inputs, and use HTTP-only secure session cookies."),
    ("Behavioral", "Tell me about a project where you solved a real problem for students or users.",
     "Use the STAR method (Situation, Task, Action, Result): Describe the gap students faced in resume feedback, how you architected ResumeNexovora AI with Flask and SQLite, and quantify the result (e.g., automated ATS scoring in under 2 seconds)."),
    ("HR", "Why should we hire you as a fresher for this role?",
     "Highlight your strong fundamentals, hands-on full-stack/domain projects, quick adaptability, and proof of execution—such as building working software platforms and earning verified certifications.")
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


# ==================== PUBLIC LANDING & SEPARATE AUTH ====================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def student_login():
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ? AND role = 'student'", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            if user["status"] != "Active":
                log_activity(email, "student", "Blocked login attempt (Suspended account)", "Failed")
                flash("Your account is currently suspended. Contact platform administrator.", "error")
                return render_template("auth/student_login.html")

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_email"] = user["email"]
            session["role"] = "student"
            log_activity(email, "student", "Student logged in", "Success")
            return redirect(url_for("student_dashboard"))

        log_activity(email or "unknown", "student", "Failed student login attempt", "Failed")
        flash("Invalid student email or password. Please try again.", "error")

    return render_template("auth/student_login.html")


@app.route("/register", methods=["GET", "POST"])
def student_register():
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        target_role = request.form.get("target_role", "Full Stack Developer")
        college = request.form.get("college", "").strip() or "University Student"

        if not full_name or not email or len(password) < 6:
            flash("Please provide your name, valid email, and a password of at least 6 characters.", "error")
            return render_template("auth/student_signup.html", roles=list(ROLE_SKILLS.keys()))

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for("student_login"))

        cur = conn.cursor()
        cur.execute(
            """INSERT INTO users (full_name, email, password_hash, role, target_role, college)
               VALUES (?, ?, ?, 'student', ?, ?)""",
            (full_name, email, generate_password_hash(password), target_role, college)
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()

        session.clear()
        session["user_id"] = new_id
        session["user_name"] = full_name
        session["user_email"] = email
        session["role"] = "student"
        log_activity(email, "student", "New student account registered", "Success")
        flash(f"Welcome to ResumeNexovora AI, {full_name}! Upload your resume to get your ATS score.", "success")
        return redirect(url_for("student_dashboard"))

    return render_template("auth/student_signup.html", roles=list(ROLE_SKILLS.keys()))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        admin = conn.execute("SELECT * FROM users WHERE email = ? AND role = 'admin'", (email,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["user_id"] = admin["id"]
            session["user_name"] = admin["full_name"]
            session["user_email"] = admin["email"]
            session["role"] = "admin"
            log_activity(email, "admin", "Admin logged into Control Panel", "Success")
            return redirect(url_for("admin_dashboard"))

        log_activity(email or "unknown", "admin", "Unauthorized admin login attempt", "Failed")
        flash("Access Denied: Invalid Administrator credentials.", "error")

    return render_template("auth/admin_login.html")


@app.route("/logout")
def logout():
    email = session.get("user_email", "user")
    role = session.get("role", "guest")
    if email != "user":
        log_activity(email, role, "Logged out", "Success")
    session.clear()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("home"))


# ==================== STUDENT PORTAL ROUTES ====================

@app.route("/student/dashboard")
@student_required
def student_dashboard():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    resumes = conn.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC, id DESC",
        (session["user_id"],)
    ).fetchall()
    jobs = conn.execute("SELECT * FROM jobs WHERE is_active = 1 ORDER BY id DESC LIMIT 4").fetchall()
    apps = conn.execute(
        """SELECT a.*, j.title, j.company, j.job_type
           FROM applications a JOIN jobs j ON a.job_id = j.id
           WHERE a.user_id = ?""",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    latest_resume = resumes[0] if resumes else None
    ats_score = latest_resume["ats_score"] if latest_resume else 0
    readiness_score = latest_resume["readiness_score"] if latest_resume else 0
    skill_gaps_count = len([s for s in (latest_resume["missing_skills"] or "").split(",") if s.strip()]) if latest_resume else 5
    internship_count = sum(1 for a in apps if a["job_type"] == "Internship")
    roadmap_steps = ROADMAPS.get(user["target_role"], ROADMAPS["Full Stack Developer"])

    return render_template(
        "student/dashboard.html",
        active_page="dashboard",
        user=user,
        resumes=resumes[:4],
        total_resumes=len(resumes),
        ats_score=ats_score,
        readiness_score=readiness_score,
        jobs_applied=len(apps),
        internship_count=internship_count,
        skill_gaps_count=skill_gaps_count,
        recommended_jobs=jobs,
        roadmap_steps=roadmap_steps
    )


@app.route("/student/analyzer", methods=["GET", "POST"])
@student_required
def student_analyzer():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    analysis_result = None
    analyzed_filename = None

    if request.method == "POST":
        target_role = request.form.get("target_role") or user["target_role"]
        pasted_text = request.form.get("resume_text", "").strip()
        uploaded_file = request.files.get("resume_file")

        extracted_text = ""
        filename_label = "Pasted_Resume_Text.txt"

        if uploaded_file and uploaded_file.filename:
            if not allowed_file(uploaded_file.filename):
                conn.close()
                flash("Unsupported file format. Please upload PDF, DOCX, or TXT.", "error")
                return redirect(url_for("student_analyzer"))

            safe_name = secure_filename(uploaded_file.filename)
            timestamped_name = f"{session['user_id']}_{int(datetime.now().timestamp())}_{safe_name}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], timestamped_name)
            uploaded_file.save(save_path)
            extracted_text = extract_text_from_file(save_path)
            filename_label = safe_name
        elif pasted_text:
            extracted_text = pasted_text
            filename_label = f"Resume_Text_{datetime.now().strftime('%b_%d_%H%M')}.txt"
        else:
            conn.close()
            flash("Please upload a resume file (PDF/DOCX/TXT) or paste your resume text.", "warning")
            return redirect(url_for("student_analyzer"))

        result = analyze_resume_text(extracted_text, target_role=target_role)
        analysis_result = result
        analyzed_filename = filename_label

        conn.execute(
            """INSERT INTO resumes (user_id, file_name, raw_text, ats_score, readiness_score, matched_skills, missing_skills, suggestions)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session["user_id"],
                filename_label,
                extracted_text[:8000],
                result["ats_score"],
                result["readiness_score"],
                ", ".join(result["matched_skills"]),
                ", ".join(result["missing_skills"]),
                "|".join(result["suggestions"])
            )
        )
        conn.commit()
        log_activity(session["user_email"], "student", f"Analyzed resume: {filename_label} (ATS: {result['ats_score']}%)", "Success")
        flash(f"Resume analyzed! Your ATS Score is {result['ats_score']}%.", "success")

    conn.close()
    return render_template(
        "student/analyzer.html",
        active_page="analyzer",
        user=user,
        roles=list(ROLE_SKILLS.keys()),
        result=analysis_result,
        filename=analyzed_filename
    )


@app.route("/student/history")
@student_required
def student_history():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    resumes = conn.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC, id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("student/history.html", active_page="history", user=user, resumes=resumes)


@app.route("/student/history/delete/<int:resume_id>", methods=["POST"])
@student_required
def delete_resume(resume_id):
    conn = get_db()
    conn.execute("DELETE FROM resumes WHERE id = ? AND user_id = ?", (resume_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Resume record removed from history.", "info")
    return redirect(url_for("student_history"))


@app.route("/student/jd-matcher", methods=["GET", "POST"])
@student_required
def student_jd_matcher():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    resumes = conn.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC, id DESC",
        (session["user_id"],)
    ).fetchall()

    match_result = None
    jd_text = ""
    selected_resume_id = None

    if request.method == "POST":
        selected_resume_id = request.form.get("resume_id")
        jd_text = request.form.get("jd_text", "").strip()
        custom_resume = request.form.get("custom_resume_text", "").strip()

        resume_text = custom_resume
        if selected_resume_id and not resume_text:
            chosen = conn.execute(
                "SELECT raw_text FROM resumes WHERE id = ? AND user_id = ?",
                (selected_resume_id, session["user_id"])
            ).fetchone()
            if chosen:
                resume_text = chosen["raw_text"] or ""

        if not resume_text or not jd_text:
            flash("Please select a saved resume (or paste text) and enter a Job Description.", "warning")
        else:
            match_result = match_job_description(resume_text, jd_text)

    conn.close()
    return render_template(
        "student/jd_matcher.html",
        active_page="jd_matcher",
        user=user,
        resumes=resumes,
        match_result=match_result,
        jd_text=jd_text,
        selected_resume_id=selected_resume_id
    )


@app.route("/student/compare")
@student_required
def student_compare():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    resumes = conn.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC, id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    r1_id = request.args.get("r1", type=int)
    r2_id = request.args.get("r2", type=int)

    resume_a = None
    resume_b = None
    if len(resumes) >= 2:
        resume_a = next((r for r in resumes if r["id"] == r1_id), resumes[1])
        resume_b = next((r for r in resumes if r["id"] == r2_id), resumes[0])
    elif len(resumes) == 1:
        resume_a = resumes[0]

    return render_template(
        "student/compare.html",
        active_page="compare",
        user=user,
        resumes=resumes,
        resume_a=resume_a,
        resume_b=resume_b
    )


@app.route("/student/jobs")
@student_required
def student_jobs():
    job_type_filter = request.args.get("type", "All")
    query = request.args.get("q", "").strip().lower()

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    latest_resume = conn.execute(
        "SELECT matched_skills FROM resumes WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (session["user_id"],)
    ).fetchone()
    applied_rows = conn.execute("SELECT job_id FROM applications WHERE user_id = ?", (session["user_id"],)).fetchall()
    applied_ids = {row["job_id"] for row in applied_rows}

    jobs = conn.execute("SELECT * FROM jobs WHERE is_active = 1 ORDER BY id DESC").fetchall()
    conn.close()

    student_skills = set()
    if latest_resume and latest_resume["matched_skills"]:
        student_skills = {s.strip().lower() for s in latest_resume["matched_skills"].split(",") if s.strip()}

    enriched_jobs = []
    for j in jobs:
        if job_type_filter != "All" and j["job_type"] != job_type_filter:
            continue
        if query and query not in j["title"].lower() and query not in j["company"].lower() and query not in j["required_skills"].lower():
            continue

        req = [s.strip() for s in j["required_skills"].split(",") if s.strip()]
        matched_cnt = sum(1 for s in req if s.lower() in student_skills)
        fit_score = int((matched_cnt / max(len(req), 1)) * 100) if student_skills else 65
        enriched_jobs.append({
            "id": j["id"],
            "title": j["title"],
            "company": j["company"],
            "location": j["location"],
            "job_type": j["job_type"],
            "package": j["package"],
            "required_skills": req,
            "description": j["description"],
            "fit_score": max(35, fit_score),
            "applied": j["id"] in applied_ids
        })

    return render_template(
        "student/jobs.html",
        active_page="jobs",
        user=user,
        jobs=enriched_jobs,
        current_type=job_type_filter,
        search_query=query
    )


@app.route("/student/jobs/apply/<int:job_id>", methods=["POST"])
@student_required
def apply_job(job_id):
    conn = get_db()
    job = conn.execute("SELECT title, company FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job:
        conn.execute(
            "INSERT OR IGNORE INTO applications (user_id, job_id, status) VALUES (?, ?, 'Applied')",
            (session["user_id"], job_id)
        )
        conn.commit()
        log_activity(session["user_email"], "student", f"Applied for {job['title']} at {job['company']}", "Success")
        flash(f"Application submitted for {job['title']} at {job['company']}!", "success")
    conn.close()
    return redirect(url_for("student_jobs"))


@app.route("/student/applications")
@student_required
def student_applications():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    applications = conn.execute(
        """SELECT a.id, a.status, a.applied_at, j.title, j.company, j.location, j.job_type, j.package
           FROM applications a
           JOIN jobs j ON a.job_id = j.id
           WHERE a.user_id = ?
           ORDER BY a.applied_at DESC""",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("student/applications.html", active_page="applications", user=user, applications=applications)


@app.route("/student/roadmap")
@student_required
def student_roadmap():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    latest_resume = conn.execute(
        "SELECT matched_skills, missing_skills FROM resumes WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    selected_role = request.args.get("role") or user["target_role"]
    steps = ROADMAPS.get(selected_role, ROADMAPS["Full Stack Developer"])
    role_skills = ROLE_SKILLS.get(selected_role, ROLE_SKILLS["Full Stack Developer"])
    missing = [s.strip() for s in (latest_resume["missing_skills"] or "").split(",") if s.strip()] if latest_resume else role_skills[:5]

    return render_template(
        "student/roadmap.html",
        active_page="roadmap",
        user=user,
        roles=list(ROADMAPS.keys()),
        selected_role=selected_role,
        steps=steps,
        role_skills=role_skills,
        missing_skills=missing
    )


@app.route("/student/interview-prep")
@student_required
def student_interview_prep():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template(
        "student/interview_prep.html",
        active_page="interview",
        user=user,
        questions=INTERVIEW_QUESTIONS
    )


@app.route("/student/profile", methods=["GET", "POST"])
@student_required
def student_profile():
    conn = get_db()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        college = request.form.get("college", "").strip()
        target_role = request.form.get("target_role", "Full Stack Developer")
        if full_name:
            conn.execute(
                "UPDATE users SET full_name = ?, college = ?, target_role = ? WHERE id = ?",
                (full_name, college, target_role, session["user_id"])
            )
            conn.commit()
            session["user_name"] = full_name
            flash("Profile & career preferences updated!", "success")

    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template(
        "student/profile.html",
        active_page="profile",
        user=user,
        roles=list(ROLE_SKILLS.keys())
    )


# ==================== ADMIN CONTROL PANEL ROUTES ====================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()
    total_students = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    total_resumes = conn.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
    active_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0]
    total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    avg_ats_row = conn.execute("SELECT AVG(ats_score) FROM resumes").fetchone()[0]
    avg_ats = int(avg_ats_row) if avg_ats_row else 0

    recent_students = conn.execute(
        "SELECT id, full_name, email, target_role, status, created_at FROM users WHERE role = 'student' ORDER BY id DESC LIMIT 5"
    ).fetchall()
    recent_logs = conn.execute(
        "SELECT * FROM activity_logs ORDER BY id DESC LIMIT 8"
    ).fetchall()
    conn.close()

    return render_template(
        "admin/dashboard.html",
        active_page="admin_dashboard",
        total_students=total_students,
        total_resumes=total_resumes,
        active_jobs=active_jobs,
        total_apps=total_apps,
        avg_ats=avg_ats,
        recent_students=recent_students,
        recent_logs=recent_logs
    )


@app.route("/admin/jobs", methods=["GET", "POST"])
@admin_required
def admin_jobs():
    conn = get_db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "").strip()
        job_type = request.form.get("job_type", "Full-Time")
        package = request.form.get("package", "").strip()
        required_skills = request.form.get("required_skills", "").strip()
        description = request.form.get("description", "").strip()

        if title and company and required_skills:
            conn.execute(
                """INSERT INTO jobs (title, company, location, job_type, package, required_skills, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title, company, location or "India (Remote/Hybrid)", job_type, package or "Competitive", required_skills, description)
            )
            conn.commit()
            log_activity(session["user_email"], "admin", f"Posted new {job_type}: {title} ({company})", "Success")
            flash(f"New opportunity '{title}' at {company} published to Student Portal!", "success")
        else:
            flash("Please fill in Title, Company, and Required Skills.", "error")

    jobs = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/manage_jobs.html", active_page="admin_jobs", jobs=jobs)


@app.route("/admin/jobs/toggle/<int:job_id>", methods=["POST"])
@admin_required
def admin_toggle_job(job_id):
    conn = get_db()
    job = conn.execute("SELECT is_active, title FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job:
        new_state = 0 if job["is_active"] == 1 else 1
        conn.execute("UPDATE jobs SET is_active = ? WHERE id = ?", (new_state, job_id))
        conn.commit()
        flash(f"Updated visibility for '{job['title']}'.", "info")
    conn.close()
    return redirect(url_for("admin_jobs"))


@app.route("/admin/jobs/delete/<int:job_id>", methods=["POST"])
@admin_required
def admin_delete_job(job_id):
    conn = get_db()
    conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    flash("Job listing deleted.", "info")
    return redirect(url_for("admin_jobs"))


@app.route("/admin/users")
@admin_required
def admin_users():
    conn = get_db()
    students = conn.execute(
        """SELECT u.*,
                  COUNT(r.id) AS resume_count,
                  COALESCE(MAX(r.ats_score), 0) AS best_ats
           FROM users u
           LEFT JOIN resumes r ON u.id = r.user_id
           WHERE u.role = 'student'
           GROUP BY u.id
           ORDER BY u.id DESC"""
    ).fetchall()
    conn.close()
    return render_template("admin/manage_users.html", active_page="admin_users", students=students)


@app.route("/admin/users/toggle/<int:user_id>", methods=["POST"])
@admin_required
def admin_toggle_user(user_id):
    conn = get_db()
    student = conn.execute("SELECT status, email FROM users WHERE id = ? AND role = 'student'", (user_id,)).fetchone()
    if student:
        new_status = "Suspended" if student["status"] == "Active" else "Active"
        conn.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        log_activity(session["user_email"], "admin", f"Changed status of {student['email']} to {new_status}", "Success")
        flash(f"Student account ({student['email']}) is now {new_status}.", "info")
    conn.close()
    return redirect(url_for("admin_users"))


@app.route("/admin/applications", methods=["GET", "POST"])
@admin_required
def admin_applications():
    conn = get_db()
    if request.method == "POST":
        app_id = request.form.get("app_id")
        new_status = request.form.get("status")
        if app_id and new_status:
            conn.execute("UPDATE applications SET status = ? WHERE id = ?", (new_status, app_id))
            conn.commit()
            flash("Application status updated!", "success")

    applications = conn.execute(
        """SELECT a.id, a.status, a.applied_at,
                  u.full_name AS student_name, u.email AS student_email,
                  j.title AS job_title, j.company
           FROM applications a
           JOIN users u ON a.user_id = u.id
           JOIN jobs j ON a.job_id = j.id
           ORDER BY a.applied_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("admin/applications.html", active_page="admin_apps", applications=applications)


@app.route("/admin/logs")
@admin_required
def admin_logs():
    conn = get_db()
    logs = conn.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return render_template("admin/security_logs.html", active_page="admin_logs", logs=logs)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
