#!/usr/bin/env python3
"""
FRBEAMS - Facial Recognition Based Employee Attendance Management System
Main application entry point
"""

import os
import sys
from app import app, db, init_db
from config import config

def main():
    # Get configuration from environment
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[env])
    
    # Ensure upload directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'faces'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'encodings'), exist_ok=True)
    
    # Initialize database
    with app.app_context():
        init_db()
        print("Database initialized successfully!")
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = env == 'development'
    
    print(f"Starting FRBEAMS server on {host}:{port}")
    print(f"Environment: {env}")
    print(f"Debug mode: {debug}")
    print("\nDefault login credentials:")
    print("  Admin: admin / admin123")
    print("  HR: hr / hr123")
    print("  Finance: finance / finance123")
    print("\nAccess the application at: http://localhost:5000")
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
