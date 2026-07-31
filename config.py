import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # ---- MySQL (Aiven) ----
    MYSQL_HOST = "mysql-2e59f8d0-anushree24anu-c996.i.aivencloud.com"
    MYSQL_PORT = 21652
    MYSQL_USER = "avnadmin"
    MYSQL_PASSWORD = "REMOVED"
    MYSQL_DB = "attendance_system"

    # ---- Default admin (created automatically if admins table is empty) ----
    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")

    # ---- Face recognition ----
    FACE_MATCH_TOLERANCE = float(os.getenv("FACE_MATCH_TOLERANCE", 0.5))

    # ---- Folders ----
    UPLOAD_STUDENTS = os.path.join(BASE_DIR, "uploads", "students")
    UPLOAD_CLASSROOM = os.path.join(BASE_DIR, "uploads", "classroom")
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")

    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # ---- Email ----
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Attendance System")

    # ---- WhatsApp ----
    WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "true").lower() == "true"

    # ---- Session ----
    SESSION_TYPE = "filesystem"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 4