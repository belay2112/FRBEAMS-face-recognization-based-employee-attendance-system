#!/usr/bin/env python3
"""
Database migration script to add employee_id column to users table
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def add_employee_id_column():
    """Add employee_id column to users table"""
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
            # Check if column already exists
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'frbeams' 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'employee_id'
            """)
            
            result = cursor.fetchone()
            
            if result:
                print("employee_id column already exists in users table")
                return
            
            # Add the employee_id column
            print("Adding employee_id column to users table...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN employee_id VARCHAR(50) UNIQUE NULL
            """)
            
            # Create index for better performance
            cursor.execute("""
                CREATE INDEX idx_users_employee_id 
                ON users(employee_id)
            """)
            
            connection.commit()
            print("employee_id column added successfully!")
            
    except Exception as e:
        print(f"Error adding employee_id column: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    add_employee_id_column()
