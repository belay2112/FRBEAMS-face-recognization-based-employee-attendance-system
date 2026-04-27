#!/bin/bash

# MySQL Database Setup for FRBEAMS
echo "Setting up MySQL database for FRBEAMS..."

# MySQL connection details
MYSQL_USER="root"
MYSQL_PASSWORD="password"
MYSQL_DATABASE="frbeams"

# Check if MySQL is running
if ! systemctl is-active --quiet mysql; then
    echo "Starting MySQL service..."
    sudo systemctl start mysql
    sudo systemctl enable mysql
fi

# Create database and user
echo "Creating database and user..."
mysql -u root -p <<MYSQL_SCRIPT
CREATE DATABASE IF NOT EXISTS frbeams;
CREATE USER IF NOT EXISTS 'frbeams_user'@'localhost' IDENTIFIED BY 'frbeams_pass';
GRANT ALL PRIVILEGES ON frbeams.* TO 'frbeams_user'@'localhost';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

# Import database schema
echo "Importing database schema..."
mysql -u root -p frbeams < database_setup.sql

echo "MySQL database setup completed!"
echo "Database: frbeams"
echo "User: frbeams_user"
echo "Password: frbeams_pass"
echo ""
echo "Update your .env file with:"
echo "DATABASE_URL=mysql+pymysql://frbeams_user:frbeams_pass@localhost/frbeams"
