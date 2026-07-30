"""
AI Face Detection Attendance System
Flask backend - main application file.
"""
import os
import json
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, jsonify, send_file, send_from_directory
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models.db import run_query, ensure_default_admin
from utils.face_utils import (
    encode_student_face, decode_encoding, recognize_faces_in_image,
    draw_annotated_image, FaceProcessingError
)
from utils.analytics_utils import (
    compute_dashboard_summary, compute_student_wise_percentage,
    compute_daily_trend, compute_monthly_trend, highest_lowest_attendance
)
from utils.report_utils import (
    generate_csv_report, generate_excel_report, generate_pdf_report
)
from utils.notify_utils import send_report_email, build_whatsapp_link

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(Config.UPLOAD_STUDENTS, exist_ok=True)
os.makedirs(Config.UPLOAD_CLASSROOM, exist_ok=True)
os.makedirs(Config.REPORTS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def get_all_students(active_only=True):
    query = "SELECT * FROM students"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY name ASC"
    return run_query(query, fetch=True)


def get_known_encodings(students):
    known_encodings, known_ids, known_names = [], [], []
    for s in students:
        if s.get("face_encoding"):
            known_encodings.append(decode_encoding(s["face_encoding"]))
            known_ids.append(s["id"])
            known_names.append(s["name"])
    return known_encodings, known_ids, known_names


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year, "admin_name": session.get("admin_name")}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("dashboard") if session.get("admin_id") else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = run_query("SELECT * FROM admins WHERE username = %s", (username,), fetchone=True)
        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin.get("full_name") or admin["username"]
            run_query("UPDATE admins SET last_login = %s WHERE id = %s",
                      (datetime.now(), admin["id"]), commit=True)
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    students = get_all_students()
    today = date.today()
    today_records = run_query(
        "SELECT * FROM attendance WHERE attendance_date = %s", (today,), fetch=True
    ) or []
    summary = compute_dashboard_summary(students, today_records)

    recent = run_query(
        """SELECT a.*, s.name, s.register_number FROM attendance a
           JOIN students s ON s.id = a.student_id
           ORDER BY a.created_at DESC LIMIT 10""",
        fetch=True
    ) or []

    return render_template("dashboard.html", summary=summary, recent=recent, students=students)


# ---------------------------------------------------------------------------
# Student management
# ---------------------------------------------------------------------------
@app.route("/students")
@login_required
def students_list():
    search = request.args.get("q", "").strip()
    if search:
        like = f"%{search}%"
        students = run_query(
            """SELECT * FROM students WHERE is_active = 1 AND
               (name LIKE %s OR register_number LIKE %s OR department LIKE %s)
               ORDER BY name""",
            (like, like, like), fetch=True
        )
    else:
        students = get_all_students()
    return render_template("students.html", students=students, search=search)


@app.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        form = request.form
        photo = request.files.get("photo")

        if not photo or photo.filename == "":
            flash("Please upload a profile photo.", "error")
            return redirect(url_for("add_student"))
        if not allowed_file(photo.filename):
            flash("Only JPG/PNG images are allowed.", "error")
            return redirect(url_for("add_student"))

        existing = run_query("SELECT id FROM students WHERE register_number = %s",
                              (form["register_number"],), fetchone=True)
        if existing:
            flash("A student with this Register Number already exists.", "error")
            return redirect(url_for("add_student"))

        filename = secure_filename(f"{form['register_number']}_{photo.filename}")
        save_path = os.path.join(Config.UPLOAD_STUDENTS, filename)
        photo.save(save_path)

        try:
            encoding_json = encode_student_face(save_path)
        except FaceProcessingError as e:
            os.remove(save_path)
            flash(str(e), "error")
            return redirect(url_for("add_student"))

        run_query(
            """INSERT INTO students
               (register_number, name, department, year, section, email, phone,
                photo_path, face_encoding)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (form["register_number"], form["name"], form["department"], form["year"],
             form.get("section"), form.get("email"), form.get("phone"),
             filename, encoding_json),
            commit=True
        )
        flash(f"Student '{form['name']}' added and face registered successfully.", "success")
        return redirect(url_for("students_list"))

    return render_template("add_student.html")


@app.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    student = run_query("SELECT * FROM students WHERE id = %s", (student_id,), fetchone=True)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("students_list"))

    if request.method == "POST":
        form = request.form
        photo = request.files.get("photo")
        photo_path = student["photo_path"]
        encoding_json = student["face_encoding"]

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                flash("Only JPG/PNG images are allowed.", "error")
                return redirect(url_for("edit_student", student_id=student_id))
            filename = secure_filename(f"{form['register_number']}_{photo.filename}")
            save_path = os.path.join(Config.UPLOAD_STUDENTS, filename)
            photo.save(save_path)
            try:
                encoding_json = encode_student_face(save_path)
            except FaceProcessingError as e:
                os.remove(save_path)
                flash(str(e), "error")
                return redirect(url_for("edit_student", student_id=student_id))
            photo_path = filename

        run_query(
            """UPDATE students SET register_number=%s, name=%s, department=%s, year=%s,
               section=%s, email=%s, phone=%s, photo_path=%s, face_encoding=%s
               WHERE id=%s""",
            (form["register_number"], form["name"], form["department"], form["year"],
             form.get("section"), form.get("email"), form.get("phone"),
             photo_path, encoding_json, student_id),
            commit=True
        )
        flash("Student details updated.", "success")
        return redirect(url_for("students_list"))

    return render_template("edit_student.html", student=student)


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    run_query("UPDATE students SET is_active = 0 WHERE id = %s", (student_id,), commit=True)
    flash("Student removed.", "success")
    return redirect(url_for("students_list"))


# ---------------------------------------------------------------------------
# Classroom photo upload + AI recognition + auto attendance marking
# ---------------------------------------------------------------------------
@app.route("/classroom/upload", methods=["GET", "POST"])
@login_required
def classroom_upload():
    if request.method == "POST":
        photo = request.files.get("classroom_photo")
        subject = request.form.get("subject", "General").strip()
        faculty = request.form.get("faculty_name", "").strip()
        attendance_date = request.form.get("attendance_date") or str(date.today())

        if not photo or photo.filename == "" or not allowed_file(photo.filename):
            flash("Please upload a valid JPG/PNG classroom photo.", "error")
            return redirect(url_for("classroom_upload"))

        filename = secure_filename(f"class_{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}")
        save_path = os.path.join(Config.UPLOAD_CLASSROOM, filename)
        photo.save(save_path)

        students = get_all_students()
        known_encodings, known_ids, known_names = get_known_encodings(students)

        try:
            result = recognize_faces_in_image(save_path, known_encodings, known_ids, known_names)
        except FaceProcessingError as e:
            flash(str(e), "error")
            return redirect(url_for("classroom_upload"))

        annotated_filename = f"annotated_{filename}"
        annotated_path = os.path.join(Config.UPLOAD_CLASSROOM, annotated_filename)
        draw_annotated_image(save_path, result["matches"], result["unmatched_boxes"], annotated_path)

        now_time = datetime.now().strftime("%H:%M:%S")
        matched_ids = set()
        for m in result["matches"]:
            matched_ids.add(m["student_id"])
            run_query(
                """INSERT INTO attendance
                   (student_id, attendance_date, attendance_time, subject, faculty_name,
                    status, confidence, marked_by)
                   VALUES (%s,%s,%s,%s,%s,'Present',%s,'AI')
                   ON DUPLICATE KEY UPDATE
                     status='Present', attendance_time=%s, confidence=%s, marked_by='AI'""",
                (m["student_id"], attendance_date, now_time, subject, faculty,
                 m["confidence"], now_time, m["confidence"]),
                commit=True
            )

        # Anyone registered but not matched in the photo -> Absent
        for s in students:
            if s["id"] not in matched_ids:
                run_query(
                    """INSERT INTO attendance
                       (student_id, attendance_date, attendance_time, subject, faculty_name, status, marked_by)
                       VALUES (%s,%s,%s,%s,%s,'Absent','AI')
                       ON DUPLICATE KEY UPDATE status = status""",  # don't overwrite an existing Present
                    (s["id"], attendance_date, now_time, subject, faculty),
                    commit=True
                )

        run_query(
            """INSERT INTO classroom_sessions
               (image_path, subject, faculty_name, session_date, total_faces_detected, total_matched)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (annotated_filename, subject, faculty, attendance_date,
             result["total_faces"], len(result["matches"])),
            commit=True
        )

        flash(
            f"Detected {result['total_faces']} face(s): "
            f"{len(result['matches'])} matched and marked Present.",
            "success"
        )
        return render_template(
            "classroom_result.html", result=result, annotated_image=annotated_filename,
            subject=subject, faculty=faculty, attendance_date=attendance_date
        )

    return render_template("classroom_upload.html", today=str(date.today()))


# ---------------------------------------------------------------------------
# Attendance management
# ---------------------------------------------------------------------------
@app.route("/attendance")
@login_required
def attendance_list():
    filter_date = request.args.get("date", str(date.today()))
    records = run_query(
        """SELECT a.*, s.name, s.register_number, s.department FROM attendance a
           JOIN students s ON s.id = a.student_id
           WHERE a.attendance_date = %s ORDER BY s.name""",
        (filter_date,), fetch=True
    ) or []
    students = get_all_students()
    return render_template("attendance.html", records=records, filter_date=filter_date,
                           students=students)


@app.route("/attendance/manual", methods=["POST"])
@login_required
def manual_attendance():
    student_id = request.form["student_id"]
    status = request.form["status"]
    subject = request.form.get("subject", "General")
    faculty = request.form.get("faculty_name", "")
    attendance_date = request.form.get("attendance_date", str(date.today()))
    now_time = datetime.now().strftime("%H:%M:%S")

    run_query(
        """INSERT INTO attendance
           (student_id, attendance_date, attendance_time, subject, faculty_name, status, marked_by)
           VALUES (%s,%s,%s,%s,%s,%s,'Manual')
           ON DUPLICATE KEY UPDATE status=%s, attendance_time=%s, marked_by='Manual'""",
        (student_id, attendance_date, now_time, subject, faculty, status, status, now_time),
        commit=True
    )
    flash("Attendance updated manually.", "success")
    return redirect(url_for("attendance_list", date=attendance_date))


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@app.route("/analytics")
@login_required
def analytics():
    students = get_all_students()
    all_records = run_query("SELECT * FROM attendance", fetch=True) or []

    student_wise = compute_student_wise_percentage(students, all_records)
    highest, lowest = highest_lowest_attendance(student_wise)
    total_present = sum(1 for r in all_records if r["status"] == "Present")
    total_absent = sum(1 for r in all_records if r["status"] == "Absent")

    return render_template(
        "analytics.html",
        student_wise=student_wise,
        highest=highest,
        lowest=lowest,
        total_present=total_present,
        total_absent=total_absent,
    )


@app.route("/api/analytics/data")
@login_required
def analytics_data():
    """JSON feed consumed by Chart.js on the analytics page."""
    students = get_all_students()
    all_records = run_query("SELECT * FROM attendance", fetch=True) or []

    student_wise = compute_student_wise_percentage(students, all_records)
    daily = compute_daily_trend(all_records)
    monthly = compute_monthly_trend(all_records)
    total_present = sum(1 for r in all_records if r["status"] == "Present")
    total_absent = sum(1 for r in all_records if r["status"] == "Absent")

    return jsonify({
        "pie": {"present": total_present, "absent": total_absent},
        "student_wise": student_wise[:20],
        "daily_trend": daily,
        "monthly_trend": monthly,
    })


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def _gather_report_data(start_date=None, end_date=None):
    query = """SELECT a.*, s.name, s.register_number, s.department, s.year, s.section
               FROM attendance a JOIN students s ON s.id = a.student_id"""
    params = []
    if start_date and end_date:
        query += " WHERE a.attendance_date BETWEEN %s AND %s"
        params = [start_date, end_date]
    query += " ORDER BY a.attendance_date DESC, s.name"
    records = run_query(query, tuple(params), fetch=True) or []

    students = get_all_students()
    student_wise = compute_student_wise_percentage(students, run_query("SELECT * FROM attendance", fetch=True) or [])

    total_present = sum(1 for r in records if r["status"] == "Present")
    total_absent = sum(1 for r in records if r["status"] == "Absent")
    summary = {
        "Total Students": len(students),
        "Total Records": len(records),
        "Present Students": total_present,
        "Absent Students": total_absent,
        "Attendance Percentage": round((total_present / len(records)) * 100, 2) if records else 0.0,
        "Report Generated On": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    }
    return records, summary, student_wise


@app.route("/reports")
@login_required
def reports_page():
    return render_template("reports.html", students=get_all_students())


@app.route("/reports/generate/<fmt>", methods=["POST"])
@login_required
def generate_report(fmt):
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    records, summary, student_wise = _gather_report_data(start_date, end_date)

    if fmt == "pdf":
        path = generate_pdf_report(records, summary, student_wise)
    elif fmt == "excel":
        path = generate_excel_report(records, summary)
    elif fmt == "csv":
        path = generate_csv_report(records, summary)
    else:
        flash("Unknown report format.", "error")
        return redirect(url_for("reports_page"))

    session["last_report_path"] = path
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@app.route("/reports/share/email", methods=["POST"])
@login_required
def share_report_email():
    to_email = request.form.get("email")
    report_path = session.get("last_report_path")
    if not report_path or not os.path.exists(report_path):
        flash("Please generate a report first, then share it.", "error")
        return redirect(url_for("reports_page"))
    try:
        send_report_email(
            to_email,
            subject="Attendance Report - AI Face Detection Attendance System",
            body_html="<p>Please find the attached attendance report.</p>",
            attachment_path=report_path,
        )
        flash(f"Report emailed to {to_email}.", "success")
    except Exception as e:
        flash(f"Could not send email: {e}", "error")
    return redirect(url_for("reports_page"))


@app.route("/reports/share/whatsapp", methods=["POST"])
@login_required
def share_report_whatsapp():
    phone = request.form.get("phone", "")
    report_path = session.get("last_report_path")
    if not report_path or not os.path.exists(report_path):
        return jsonify({"error": "Please generate a report first, then share it."}), 400
    message = (
        f"Attendance report generated on "
        f"{datetime.now().strftime('%d %b %Y')} - "
        f"please find it attached (download it from the system and attach here)."
    )
    link = build_whatsapp_link(phone, message)
    return jsonify({"whatsapp_link": link})


# ---------------------------------------------------------------------------
# Serve uploaded images (student photos + classroom photos)
# ---------------------------------------------------------------------------
@app.route("/uploads/students/<path:filename>")
@login_required
def uploaded_student_photo(filename):
    return send_from_directory(Config.UPLOAD_STUDENTS, filename)


@app.route("/uploads/classroom/<path:filename>")
@login_required
def uploaded_classroom_photo(filename):
    return send_from_directory(Config.UPLOAD_CLASSROOM, filename)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Something went wrong on our end"), 500


if __name__ == "__main__":
    with app.app_context():
        ensure_default_admin()
    app.run(debug=True, host="0.0.0.0", port=5000)
