"""
Database access layer.
Uses mysql-connector-python with a connection pool.
Configured for Aiven MySQL with SSL.
"""

import mysql.connector
from mysql.connector import pooling
from werkzeug.security import generate_password_hash
from config import Config

_pool = None


def init_pool():
    """
    Initialize MySQL connection pool.
    """
    global _pool

    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="attendance_pool",
            pool_size=8,

            # Aiven MySQL Configuration
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            port=Config.MYSQL_PORT,

            # Aiven SSL
            ssl_ca="ca.pem",
            ssl_verify_cert=True
        )

    return _pool


def get_conn():
    """
    Get database connection from pool.
    """
    return init_pool().get_connection()


def run_query(query, params=None, fetch=False, fetchone=False, commit=False):
    """
    Execute SQL queries.

    fetch=True      -> return all rows
    fetchone=True   -> return one row
    commit=True     -> commit changes
    """

    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query, params or ())

        result = None

        if fetchone:
            result = cursor.fetchone()

        elif fetch:
            result = cursor.fetchall()

        if commit:
            conn.commit()
            result = cursor.lastrowid

        return result

    finally:
        cursor.close()
        conn.close()


def ensure_default_admin():
    """
    Create default admin if admins table is empty.
    """

    admins = run_query(
        "SELECT COUNT(*) AS c FROM admins",
        fetchone=True
    )

    if admins and admins["c"] == 0:

        run_query(
            """
            INSERT INTO admins
            (username, password_hash, full_name)
            VALUES (%s, %s, %s)
            """,
            (
                Config.DEFAULT_ADMIN_USERNAME,
                generate_password_hash(
                    Config.DEFAULT_ADMIN_PASSWORD
                ),
                "System Administrator"
            ),
            commit=True
        )

        print(
            f"[setup] Created default admin "
            f"'{Config.DEFAULT_ADMIN_USERNAME}' "
            f"with password "
            f"'{Config.DEFAULT_ADMIN_PASSWORD}'"
        )