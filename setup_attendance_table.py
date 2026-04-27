#!/usr/bin/env python3
"""
Script to setup attendance table with proper structure
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def setup_attendance_table():
    """Create attendance table if it doesn't exist"""
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
            # Check if attendance table exists
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'frbeams' 
                AND TABLE_NAME = 'attendance'
            """)
            
            result = cursor.fetchone()
            
            if result:
                print("Attendance table already exists. Checking structure...")
                
                # Check table structure
                cursor.execute("DESCRIBE attendance")
                columns = cursor.fetchall()
                print("Current attendance table structure:")
                for col in columns:
                    print(f"  {col['Field']}: {col['Type']} {'NULL' if col['Null'] == 'YES' else 'NOT NULL'}")
                
                # Add missing columns if needed
                existing_columns = [col['Field'] for col in columns]
                
                if 'check_in' not in existing_columns:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN check_in TIME NULL")
                    print("Added check_in column")
                
                if 'check_out' not in existing_columns:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN check_out TIME NULL")
                    print("Added check_out column")
                
                if 'work_hours' not in existing_columns:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN work_hours DECIMAL(5,2) NULL")
                    print("Added work_hours column")
                
                if 'status' not in existing_columns:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN status VARCHAR(20) DEFAULT 'present'")
                    print("Added status column")
                
                connection.commit()
                
            else:
                print("Creating attendance table...")
                cursor.execute("""
                    CREATE TABLE attendance (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        employee_id INT NOT NULL,
                        date DATE NOT NULL,
                        check_in TIME NULL,
                        check_out TIME NULL,
                        status VARCHAR(20) DEFAULT 'present',
                        work_hours DECIMAL(5,2) NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees(id),
                        INDEX idx_attendance_date (date),
                        INDEX idx_attendance_employee (employee_id)
                    )
                """)
                print("Attendance table created successfully!")
            
            connection.commit()
            
    except Exception as e:
        print(f"Error setting up attendance table: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    setup_attendance_table()
