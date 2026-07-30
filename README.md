# AI Face Detection Attendance System

A full-stack attendance system that uses face recognition to automatically mark
student attendance from a classroom/lab group photo, with an admin dashboard,
analytics, and downloadable reports.

**Stack:** Python (Flask) · MySQL · HTML5/CSS3/JavaScript (no Bootstrap) ·
OpenCV + face_recognition · Chart.js + Matplotlib · ReportLab · openpyxl

---

## 1. Project Structure

```
attendance_system/
├── app.py                     # Flask app & all routes
├── config.py                  # Configuration (reads .env)
├── requirements.txt
├── .env.example                # Copy to .env and fill in your values
├── database/
│   └── schema.sql              # MySQL schema (run once)
├── models/
│   └── db.py                   # DB connection pool + query helper
├── utils/
│   ├── face_utils.py           # Face detection / encoding / matching (AI core)
│   ├── report_utils.py         # PDF / Excel / CSV report generation
│   ├── notify_utils.py         # Email + WhatsApp sharing
│   └── analytics_utils.py      # Dashboard/analytics aggregation
├── templates/                  # Jinja2 HTML templates
├── static/
│   ├── css/style.css           # Blue-violet glassmorphism theme
│   ├── js/main.js              # Sidebar, flash messages, modal logic
│   └── js/charts.js            # Chart.js analytics rendering
├── uploads/
│   ├── students/                # Student profile photos
│   └── classroom/                # Classroom photos + annotated results
└── reports/                     # Generated PDF/Excel/CSV reports
```

---

## 2. Prerequisites

- Python 3.10 or 3.11 (face_recognition/dlib wheels are most reliable on these versions)
- MySQL Server 8.x
- On Windows, building `dlib` needs **CMake** and **Visual Studio Build Tools**
  (C++ workload). On Linux/macOS, install `cmake` and `build-essential` first:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install -y cmake build-essential libopenblas-dev liblapack-dev
  ```

## 3. Installation

```bash
# 1. Clone / unzip the project, then enter the folder
cd attendance_system

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

> If `dlib` fails to build, try: `pip install dlib --no-cache-dir` after
> installing CMake, or use a prebuilt wheel matching your Python version.

## 4. Database Setup

```bash
mysql -u root -p < database/schema.sql
```

This creates the `attendance_system` database with tables: `admins`,
`students`, `attendance`, `classroom_sessions`.

## 5. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and set:
- `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB` — your MySQL credentials
- `SECRET_KEY` — any long random string
- `SMTP_USERNAME` / `SMTP_PASSWORD` — only needed if you want to email reports
  (use a Gmail **App Password**, not your normal password)

## 6. Run the Application

```bash
python app.py
```

The app starts at **http://localhost:5000**. On first run it automatically
creates a default admin account:

- **Username:** `admin`
- **Password:** `Admin@123`

**Change this password immediately** by inserting a new hash into the
`admins` table, or add a "change password" admin flow if extending the system.

---

## 7. How to Use

1. **Log in** with the admin credentials above.
2. **Add Students** (Students → Add Student): fill in details and upload a
   clear, front-facing passport photo. The system detects the face and stores
   its 128-dimension encoding — this is the "face registration" step.
3. **Scan a Classroom Photo** (Classroom Scan): upload a group photo, enter
   subject/faculty/date. The system detects every face, compares it against
   all registered students, and:
   - Marks matched students **Present** (with a confidence score)
   - Marks all other registered students **Absent**
   - Shows an annotated image with bounding boxes and names
4. **Attendance** page: view/filter records by date, or add manual entries
   (e.g. for a student who was present but not clearly visible in the photo).
5. **Analytics**: pie chart (present/absent), bar chart (student-wise %),
   daily/monthly trend lines, highest/lowest attendance.
6. **Reports**: generate PDF / Excel / CSV (optionally filtered by date
   range), then share the last generated report via Email or WhatsApp
   (WhatsApp opens a pre-filled chat — attach the downloaded file manually,
   since WhatsApp does not support file delivery via URL).

---

## 8. Notes on the AI Pipeline

- Face detection/encoding uses the `face_recognition` library (built on dlib's
  HOG + ResNet face encoder), producing a 128-d vector per face.
- Matching uses Euclidean distance between encodings; a configurable
  `FACE_MATCH_TOLERANCE` (default `0.5`) controls strictness — lower = stricter.
- Confidence shown to the user is `(1 - distance) * 100`, clamped at 0.
- Duplicate attendance for the same student/date/subject is prevented at the
  database level via a `UNIQUE(student_id, attendance_date, subject)`
  constraint combined with `ON DUPLICATE KEY UPDATE`.
- Invalid images (no face / multiple faces in a profile photo, unreadable
  file, no faces in a classroom photo) raise a `FaceProcessingError` that is
  caught and shown to the admin as a friendly message — nothing crashes.

## 9. Extending the System

- Add a "Change Password" admin settings page.
- Add role-based access (e.g. faculty accounts limited to their own subject).
- Swap SQLite/PostgreSQL for MySQL by adjusting `models/db.py` only.
- Add pagination to the Students/Attendance tables for large datasets.
- Replace `face_recognition` (HOG) with a CNN or a more modern embedding
  model for higher accuracy on angled/low-light classroom photos.

---

## 10. Troubleshooting

| Issue | Fix |
|---|---|
| `dlib` fails to install | Install CMake + C++ build tools first, retry `pip install dlib` |
| `Access denied for user` (MySQL) | Check `.env` MYSQL_USER/PASSWORD match your MySQL setup |
| "No face detected" on a clear photo | Ensure good lighting, face facing the camera, no heavy shadows |
| Classroom scan misses students at the back | Use a higher-resolution photo; HOG detection is weaker on tiny/far faces |
| Emails not sending | Use an App Password (not account password) for Gmail; check SMTP host/port |

---

Built for academic demonstration — production hardening (rate limiting, CSRF
tokens, HTTPS, password policy enforcement, audit logging) is recommended
before any real deployment handling personal data / biometric information.
