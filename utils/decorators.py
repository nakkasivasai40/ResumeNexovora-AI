from functools import wraps
from flask import session, redirect, url_for, flash

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "student":
            flash("Please log in with your Student account to access this page.", "warning")
            return redirect(url_for("student_login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Unauthorized access. Please log in via the Admin Portal.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function
