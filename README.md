# ResumeNexovora AI — Student Resume Analyzer & Career Platform

Full-stack Python (Flask + SQLite) career platform designed for college students and freshers, featuring **separate Student and Admin authentication portals**, AI/ATS resume scoring, Job Description (JD) matching, resume version comparison, curated job/internship applications, and a complete Administrator Control Panel.

## How to Run on Your Laptop

1. **Extract the ZIP file** (`ResumeNexovora_AI.zip`) into a folder on your computer.
2. Open the folder in **VS Code** or Terminal / Command Prompt.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python app.py
   ```
   *(On Windows, you can also simply double-click `run.bat`!)*
5. Open your browser and visit: **http://127.0.0.1:5000**

## Separate Login Portals & Default Credentials

- **Public Landing Page:** `http://127.0.0.1:5000/`
- **Student Login (`/login`):**
  - Email: `rahul@student.com`
  - Password: `Student@123`
  - *(Or click "Create Student Account" at `/register` to sign up as a new student!)*
- **Admin Control Panel Login (`/admin/login`):**
  - Email: `admin@resumenexovora.com`
  - Password: `Admin@123`
