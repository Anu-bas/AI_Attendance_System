"""
Database access layer.
Uses mysql-connector-python with a simple connection-per-request pattern,
plus a lightweight connection pool for efficiency.
"""
import mysql.connector
from mysql.connector import pooling
from werkzeug.security import generate_password_hash
from config import Config

_pool = None


def init_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="attendance_pool",
            pool_size=8,
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            port=Config.MYSQL_PORT,
        )
    return _pool


def get_conn():
    return init_pool().get_connection()


def run_query(query, params=None, fetch=False, fetchone=False, commit=False):
    """Generic helper: run a query and optionally fetch/commit."""
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        result = None
        if fetchone:
            result = cur.fetchone()
        elif fetch:
            result = cur.fetchall()
        if commit:
            conn.commit()
            result = cur.lastrowid
        return result
    finally:
        cur.close()
        conn.close()


def ensure_default_admin():
    """Create the admins table's first row if none exists yet."""
    admins = run_query("SELECT COUNT(*) AS c FROM admins", fetchone=True)
    if admins and admins["c"] == 0:
        run_query(
            "INSERT INTO admins (username, password_hash, full_name) VALUES (%s, %s, %s)",
            (
                Config.DEFAULT_ADMIN_USERNAME,
                generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD),
                "System Administrator",
            ),
            commit=True,
        )
        print(
            f"[setup] Created default admin '{Config.DEFAULT_ADMIN_USERNAME}' "
            f"with password '{Config.DEFAULT_ADMIN_PASSWORD}'. Please change it after first login."
        )
