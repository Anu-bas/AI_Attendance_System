-- =====================================================================
-- AI Face Detection Attendance System - Database Schema
-- Run this once:  mysql -u root -p < database/schema.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS attendance_system
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE attendance_system;

-- ---------------------------------------------------------------------
-- Admins (system users who can log in to manage the system)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(100) DEFAULT NULL,
    email           VARCHAR(120) DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      DATETIME DEFAULT NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Students
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    register_number  VARCHAR(30)  NOT NULL UNIQUE,
    name             VARCHAR(100) NOT NULL,
    department       VARCHAR(80)  NOT NULL,
    year             VARCHAR(20)  NOT NULL,
    section          VARCHAR(10)  DEFAULT NULL,
    email            VARCHAR(120) DEFAULT NULL,
    phone            VARCHAR(20)  DEFAULT NULL,
    photo_path       VARCHAR(255) DEFAULT NULL,   -- relative path under /uploads/students
    face_encoding    LONGTEXT     DEFAULT NULL,    -- JSON array (128-d face_recognition encoding)
    is_active        TINYINT(1)   DEFAULT 1,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_department (department),
    INDEX idx_year_section (year, section)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Attendance records
-- One row per (student, date, subject) to prevent duplicate marking
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT NOT NULL,
    attendance_date DATE NOT NULL,
    attendance_time TIME NOT NULL,
    subject         VARCHAR(100) NOT NULL DEFAULT 'General',
    faculty_name    VARCHAR(100) DEFAULT NULL,
    status          ENUM('Present','Absent') NOT NULL DEFAULT 'Absent',
    confidence      DECIMAL(5,2) DEFAULT NULL,   -- match confidence % when auto-marked
    marked_by       ENUM('AI','Manual') DEFAULT 'AI',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_attendance_student FOREIGN KEY (student_id)
        REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_student_day_subject (student_id, attendance_date, subject),
    INDEX idx_date (attendance_date)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Classroom sessions (each group-photo upload batch)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS classroom_sessions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    image_path      VARCHAR(255) NOT NULL,
    subject         VARCHAR(100) NOT NULL,
    faculty_name    VARCHAR(100) DEFAULT NULL,
    session_date    DATE NOT NULL,
    total_faces_detected INT DEFAULT 0,
    total_matched   INT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Seed a default admin (username: admin / password: Admin@123)
-- Password hash below = werkzeug generate_password_hash('Admin@123')
-- The app also auto-creates this on first run if the table is empty,
-- so this INSERT is optional / a convenience fallback.
-- ---------------------------------------------------------------------
INSERT INTO admins (username, password_hash, full_name)
SELECT 'admin', 'scrypt:32768:8:1$PLACEHOLDER$REPLACE_ON_FIRST_RUN', 'System Administrator'
WHERE NOT EXISTS (SELECT 1 FROM admins WHERE username = 'admin');
