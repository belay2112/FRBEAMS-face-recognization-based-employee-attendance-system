#!/bin/bash

# FRBEAMS Startup Script
echo "🚀 Starting FRBEAMS - Facial Recognition Employee Attendance Management System"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo " Activating virtual environment..."
source venv/bin/activate

# Install core dependencies
echo " Installing core dependencies..."
pip install Flask==2.3.3 Flask-SQLAlchemy==3.0.5 Flask-Login==0.6.3 Flask-CORS==4.0.0 Werkzeug==2.3.7 python-dotenv bcrypt PyMySQL

# Check if face recognition dependencies are available
echo " Checking face recognition dependencies..."
pip install opencv-python numpy Pillow > /dev/null 2>&1

if python -c "import cv2" 2>/dev/null; then
    echo " OpenCV installed successfully"    
    # Try to install face recognition (may fail on some systems)   
    pip install face-recognition > /dev/null 2>&1                                     
    if python -c "import face_recognition" 2>/dev/null; then
        echo " Face recognition library installed successfully"
        echo " Running FRBEAMS with MySQL database..."
        python app.py
    else
        echo "  Face recognition library not available, running basic version..."
        echo " To install face recognition, you may need: cmake, dlib, and build tools"
        python app.py
    fi
else
    echo " OpenCV installation failed, running basic version..."
    python app.py
fi
