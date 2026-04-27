#!/usr/bin/env python3
"""
Script to add sample attendance data for testing report generation
"""

import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def add_sample_attendance():
    """Add sample attendance data for testing"""
    try:
        # Database connection
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'frbeams'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Check if there are any employees
            cursor.execute("SELECT COUNT(*) as count FROM employees")
            result = cursor.fetchone()
            
            if result['count'] == 0:
                print("No employees found. Adding sample employees first...")
                
                # Add sample employees
                sample_employees = [
                    ('EMP001', 'John', 'Doe', 'IT', 'Software Engineer', 'john.doe@company.com'),
                    ('EMP002', 'Jane', 'Smith', 'HR', 'HR Manager', 'jane.smith@company.com'),
                    ('EMP003', 'Mike', 'Johnson', 'Finance', 'Accountant', 'mike.johnson@company.com'),
                    ('EMP004', 'Sarah', 'Williams', 'IT', 'Developer', 'sarah.williams@company.com'),
                    ('EMP005', 'David', 'Brown', 'Operations', 'Operations Manager', 'david.brown@company.com')
                ]
                
                for emp in sample_employees:
                    cursor.execute("""
                        INSERT INTO employees (employee_id, first_name, last_name, department, position, email, is_active, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (*emp, True, datetime.now()))
                
                connection.commit()
                print("Sample employees added successfully!")
            
            # Get employees
            cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees WHERE is_active = 1")
            employees = cursor.fetchall()
            
            if not employees:
                print("No active employees found!")
                return
            
            # Add sample attendance data for the last 7 days
            print("Adding sample attendance data...")
            
            for days_ago in range(7, 0, -1):
                attendance_date = datetime.now() - timedelta(days=days_ago)
                
                for emp in employees:
                    # Randomly decide if present (80% chance)
                    import random
                    if random.random() < 0.8:
                        # Present
                        check_in = datetime.combine(attendance_date, datetime.min.time()) + timedelta(hours=random.randint(8, 10))
                        check_out = check_in + timedelta(hours=random.randint(7, 10))
                        work_hours = (check_out - check_in).total_seconds() / 3600
                        
                        cursor.execute("""
                            INSERT INTO attendance (employee_id, date, check_in, check_out, status, work_hours, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (emp['id'], attendance_date.date(), check_in, check_out, 'present', round(work_hours, 2), datetime.now()))
                    else:
                        # Absent
                        cursor.execute("""
                            INSERT INTO attendance (employee_id, date, status, created_at)
                            VALUES (%s, %s, %s, %s)
                        """, (emp['id'], attendance_date.date(), 'absent', datetime.now()))
            
            connection.commit()
            print(f"Sample attendance data added for {len(employees)} employees over the last 7 days!")
            
    except Exception as e:
        print(f"Error adding sample attendance data: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    add_sample_attendance()
