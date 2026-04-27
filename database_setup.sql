-- FRBEAMS Database Setup Script
-- Facial Recognition Based Employee Attendance Management System

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS frbeams CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE frbeams;

-- Drop existing tables if they exist (for fresh setup)
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS departments;

-- Create roles table
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create departments table
CREATE TABLE departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    employee_id VARCHAR(50) UNIQUE NULL,
    role_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);

-- Create employees table
CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(20),
    department VARCHAR(50),
    position VARCHAR(50),
    hire_date DATE NOT NULL,
    salary DECIMAL(10, 2),
    user_id INT NOT NULL UNIQUE,
    face_image_path VARCHAR(255),
    face_encoding TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create attendance table
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    date DATE NOT NULL,
    check_in_time TIMESTAMP NULL,
    check_out_time TIMESTAMP NULL,
    status VARCHAR(20) DEFAULT 'present',
    work_hours DECIMAL(4, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE KEY unique_employee_date (employee_id, date)
);


-- Payroll Table
CREATE TABLE payroll (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    basic_salary DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    allowance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    deduction DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    taxable_salary DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    income_tax DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    gross_salary DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    net_salary DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    effective_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    INDEX idx_employee_id (employee_id),
    INDEX idx_effective_date (effective_date)
);

-- Create indexes for better performance
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_attendance_employee ON attendance(employee_id);
CREATE INDEX idx_employees_active ON employees(is_active);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_employees_department ON employees(department);

-- Insert default roles
INSERT INTO roles (name, description) VALUES
('Admin', 'System administrator with full access'),
('HR Officer', 'Human Resources officer with employee management access'),
('Finance Officer', 'Finance officer with report access'),
('Employee', 'Regular employee with attendance access'),
('Department', 'Department manager with attendance and reporting access');

-- Insert default departments
INSERT INTO departments (name, description) VALUES
('Admin', 'Administration and system management'),
('Finance', 'Financial management and accounting'),
('Human Resource', 'Human resources and personnel management'),
('Department', 'General departmental operations'),
('Employee', 'Employee services and support');

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, employee_id, role_id) VALUES
('admin', 'admin@company.com', '$2b$12$v5ECJmXbaJ2uJfF1bpLkj.VANHGWDXLy0SlCBYATJlwXnUotRskTm', NULL, 1);

-- Insert sample HR user (password: hr123)
INSERT INTO users (username, email, password_hash, employee_id, role_id) VALUES
('hr', 'hr@company.com', '$2b$12$8t73wdJlgEtX5WXSkM0Vnef8QZKwSjang.0K9dJzi5N150oVyille', 'EMP002', 2);

-- Insert sample Finance user (password: finance123)
INSERT INTO users (username, email, password_hash, employee_id, role_id) VALUES
('finance', 'finance@company.com', '$2b$12$x0V9iJCLcNzrAV4TAZGCR.MpdOz5zy2rKbBR2dK0IiDNpJ/ClrK72', 'EMP003', 3);

-- Insert sample Employee user (password: password123)
INSERT INTO users (username, email, password_hash, employee_id, role_id) VALUES
('it_employee', 'it.employee@company.com', '$2b$12$mrs8PoFSpTgsKF0Mm5.MSeLXWoT7eU6Zq961F4EuVk.VgsxpIRAl.', 'EMP001', 4);

-- Insert sample Department user (password: password123)
INSERT INTO users (username, email, password_hash, employee_id, role_id) VALUES
('department_user', 'department@company.com', '$2b$12$oxxpmbSNo7d1e0cJN3ld/OR6arj0/xpCEJsPYjdACv.m9agB/s8rW', NULL, 5);

-- Insert sample employees
INSERT INTO employees (
    employee_id, first_name, last_name, email, phone, department, position, 
    hire_date, salary, user_id
) VALUES
('EMP001', 'John', 'Doe', 'john.doe@company.com', '1234567890', 'IT', 'Software Engineer', '2024-01-15', 75000.00, 4),
('EMP002', 'Jane', 'Smith', 'jane.smith@company.com', '2345678901', 'HR', 'HR Manager', '2024-01-20', 65000.00, 2),
('EMP003', 'Mike', 'Johnson', 'mike.johnson@company.com', '3456789012', 'Finance', 'Accountant', '2024-02-01', 60000.00, 3);



-- Insert sample attendance data
INSERT INTO attendance (employee_id, date, check_in_time, check_out_time, status, work_hours) VALUES
(1, '2024-04-07', '2024-04-07 09:00:00', '2024-04-07 17:30:00', 'present', 8.5),
(2, '2024-04-07', '2024-04-07 08:45:00', '2024-04-07 17:15:00', 'present', 8.5),
(3, '2024-04-07', '2024-04-07 09:15:00', '2024-04-07 17:45:00', 'present', 8.5),
(1, '2024-04-06', '2024-04-06 09:10:00', '2024-04-06 17:20:00', 'present', 8.17),
(2, '2024-04-06', '2024-04-06 08:50:00', '2024-04-06 17:10:00', 'present', 8.33),
(3, '2024-04-06', '2024-04-06 09:05:00', '2024-04-06 17:25:00', 'present', 8.33);

-- Create stored procedure for marking attendance
CREATE PROCEDURE sp_mark_attendance(
    IN p_employee_id INT,
    IN p_attendance_date DATE,
    IN p_check_in_time TIMESTAMP,
    IN p_check_out_time TIMESTAMP,
    IN p_status VARCHAR(20),
    IN p_work_hours DECIMAL(4,2),
    IN p_notes TEXT
)
BEGIN
    DECLARE v_count INT;
    
    -- Check if attendance already exists for this employee and date
    SELECT COUNT(*) INTO v_count 
    FROM attendance 
    WHERE employee_id = p_employee_id AND date = p_attendance_date;
    
    IF v_count = 0 THEN
        -- Insert new attendance record
        INSERT INTO attendance (
            employee_id, date, check_in_time, check_out_time, 
            status, work_hours, notes
        ) VALUES (
            p_employee_id, p_attendance_date, p_check_in_time, p_check_out_time,
            p_status, p_work_hours, p_notes
        );
        SELECT 'Attendance marked successfully' AS message;
    ELSE
        SELECT 'Attendance already exists for this date' AS message;
    END IF;
END;

-- Create views for common queries
CREATE VIEW employee_attendance_summary AS
SELECT 
    e.id,
    e.employee_id,
    CONCAT(e.first_name, ' ', e.last_name) AS full_name,
    e.department,
    e.position,
    COUNT(a.id) AS total_days,
    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) AS present_days,
    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS absent_days,
    SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) AS late_days,
    SUM(a.work_hours) AS total_work_hours,
    AVG(a.work_hours) AS avg_work_hours
FROM employees e
LEFT JOIN attendance a ON e.id = a.employee_id
WHERE e.is_active = TRUE
GROUP BY e.id, e.employee_id, e.first_name, e.last_name, e.department, e.position;

-- Create stored procedures for common operations
DELIMITER //

CREATE PROCEDURE sp_mark_attendance(
    IN p_employee_id INT,
    IN p_attendance_date DATE,
    IN p_check_in_time TIMESTAMP,
    IN p_check_out_time TIMESTAMP,
    IN p_status VARCHAR(20),
    IN p_work_hours DECIMAL(4,2),
    IN p_notes TEXT
)
BEGIN
    DECLARE v_count INT;
    
    -- Check if attendance already exists for this employee and date
    SELECT COUNT(*) INTO v_count 
    FROM attendance 
    WHERE employee_id = p_employee_id AND date = p_attendance_date;
    
    IF v_count = 0 THEN
        -- Insert new attendance record
        INSERT INTO attendance (
            employee_id, date, check_in_time, check_out_time, 
            status, work_hours, notes
        ) VALUES (
            p_employee_id, p_attendance_date, p_check_in_time, p_check_out_time,
            p_status, p_work_hours, p_notes
        );
        SELECT 'Attendance marked successfully' AS message;
    ELSE
        SELECT 'Attendance already exists for this date' AS message;
    END IF;
END //

CREATE PROCEDURE sp_get_attendance_report(
    IN p_start_date DATE,
    IN p_end_date DATE,
    IN p_department VARCHAR(50)
)
BEGIN
    SELECT 
        e.employee_id,
        CONCAT(e.first_name, ' ', e.last_name) AS employee_name,
        e.department,
        e.position,
        COUNT(a.id) AS total_days,
        SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) AS present_days,
        SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS absent_days,
        SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) AS late_days,
        SUM(a.work_hours) AS total_work_hours,
        AVG(a.work_hours) AS avg_work_hours,
        ROUND((SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) / COUNT(a.id)) * 100, 2) AS attendance_percentage
    FROM employees e
    LEFT JOIN attendance a ON e.id = a.employee_id 
        AND a.date BETWEEN p_start_date AND p_end_date
    WHERE e.is_active = TRUE
        AND (p_department IS NULL OR p_department = '' OR e.department = p_department)
    GROUP BY e.id, e.employee_id, e.first_name, e.last_name, e.department, e.position
    ORDER BY e.employee_id;
END //

DELIMITER ;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON frbeams.* TO 'frbeams_user'@'localhost' IDENTIFIED BY 'secure_password';
-- FLUSH PRIVILEGES;


-- Insert sample payroll data
INSERT INTO payroll (employee_id, full_name, role, basic_salary, allowance, deduction, taxable_salary, income_tax, gross_salary, net_salary, effective_date) VALUES
('EMP001', 'John Doe', 'Software Engineer', 5000.00, 500.00, 200.00, 5300.00, 795.00, 5500.00, 4505.00, '2024-01-01'),
('EMP002', 'Jane Smith', 'HR Manager', 4500.00, 300.00, 150.00, 4650.00, 697.50, 4800.00, 3952.50, '2024-01-01'),
('EMP003', 'Mike Johnson', 'Accountant', 4000.00, 400.00, 100.00, 4300.00, 645.00, 4400.00, 3655.00, '2024-01-01');

-- Show database structure
SHOW TABLES;
DESCRIBE roles;
DESCRIBE users;
DESCRIBE employees;
DESCRIBE attendance;
DESCRIBE payroll;

