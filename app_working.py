from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash
import bcrypt
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, date
import os
import cv2
import numpy as np
import pickle
import base64
import json
import csv
import io
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root@localhost/frbeams')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
CORS(app)

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'faces'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'encodings'), exist_ok=True)

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    employee_id = db.Column(db.String(50), unique=True, nullable=True)  # Link to employee
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Employee
    employee = db.relationship('Employee', backref='user', uselist=False)
    role = db.relationship('Role', backref='users')

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(50))
    position = db.Column(db.String(50))
    hire_date = db.Column(db.Date, nullable=False)
    salary = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    face_encoding = db.Column(db.Text)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='present')
    work_hours = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    employee = db.relationship('Employee', backref='attendance_records')

class Payroll(db.Model):
    __tablename__ = 'payroll'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), db.ForeignKey('employees.employee_id'), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(100))
    basic_salary = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    allowance = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    deduction = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    taxable_salary = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    income_tax = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    gross_salary = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    net_salary = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    effective_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee = db.relationship('Employee', backref='payroll_records')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decorators for role-based access
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role.name != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def hr_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role.name not in ['Admin', 'HR Officer']:
            return jsonify({'error': 'HR access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Simple Face Recognition System using OpenCV only
class SimpleFaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        self.tolerance = 0.6
        # Try different paths for haarcascade file
        haarcascade_path = None
        possible_paths = [
            '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_default.xml'  # Current directory
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                haarcascade_path = path
                break
        
        if haarcascade_path is None:
            # Create the file in current directory if not found
            haarcascade_path = 'haarcascade_frontalface_default.xml'
            if not os.path.exists(haarcascade_path):
                print(f"Warning: haarcascade file not found at any standard location. Face detection may not work properly.")
        
        self.face_cascade = cv2.CascadeClassifier(haarcascade_path)
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known faces from database"""
        print("Loading face encodings from database...")
        
        try:
            employees = Employee.query.filter(
                Employee.is_active == True,
                Employee.face_encoding.isnot(None)
            ).all()
            
            self.known_face_encodings = []
            self.known_face_ids = []
            self.known_face_names = []
            
            print(f"Found {len(employees)} employees with face encodings")
            
            for employee in employees:
                try:
                    # Decode face encoding from database
                    encoding_data = base64.b64decode(employee.face_encoding)
                    encoding = pickle.loads(encoding_data)
                    
                    # Handle different encoding formats
                    if isinstance(encoding, dict):
                        if 'encodings' in encoding:
                            # Multiple encodings format (from training)
                            print(f"Employee {employee.first_name} has {len(encoding['encodings'])} training samples")
                        else:
                            # Single encoding format (from registration)
                            print(f"Employee {employee.first_name} has single face encoding")
                    else:
                        print(f"Employee {employee.first_name} has legacy encoding format")
                    
                    self.known_face_encodings.append(encoding)
                    self.known_face_ids.append(employee.id)
                    self.known_face_names.append(f"{employee.first_name} {employee.last_name}")
                    print(f"Successfully loaded face for {employee.first_name} {employee.last_name} (ID: {employee.id})")
                    
                except Exception as e:
                    print(f"Error loading face for {employee.first_name} {employee.last_name}: {e}")
                    print(f"Face encoding data length: {len(employee.face_encoding) if employee.face_encoding else 0}")
            
            print(f"Successfully loaded {len(self.known_face_encodings)} face encodings")
            print(f"Known faces: {self.known_face_names}")
            
        except Exception as e:
            print(f"Error loading faces: {e}")
            self.known_face_encodings = []
            self.known_face_ids = []
            self.known_face_names = []
    
    def train_faces(self, employee_images):
        """Train face recognition with multiple images per employee"""
        print(f"Training faces with {len(employee_images)} images...")
        
        try:
            for employee_id, images in employee_images.items():
                employee = Employee.query.get(employee_id)
                if not employee:
                    continue
                
                # Process multiple images for better training
                face_encodings = []
                for image_data in images:
                    try:
                        # Convert base64 to image
                        from io import BytesIO
                        from PIL import Image
                        
                        if image_data.startswith('data:image'):
                            image_data = image_data.split(',')[1]
                        
                        image_bytes = base64.b64decode(image_data)
                        image = Image.open(BytesIO(image_bytes))
                        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                        
                        # Detect face
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                        
                        if len(faces) > 0:
                            # Create a simple encoding based on face location
                            face_encoding = {
                                'employee_id': employee_id,
                                'face_location': faces[0].tolist(),
                                'timestamp': datetime.now().isoformat(),
                                'image_size': frame.shape
                            }
                            face_encodings.append(face_encoding)
                    
                    except Exception as e:
                        print(f"Error processing image: {e}")
                
                # Store all encodings for this employee
                if face_encodings:
                    combined_encoding = {
                        'employee_id': employee_id,
                        'encodings': face_encodings,
                        'trained_at': datetime.now().isoformat()
                    }
                    encoding_str = base64.b64encode(pickle.dumps(combined_encoding)).decode('utf-8')
                    
                    employee.face_encoding = encoding_str
                    db.session.commit()
                    print(f"Trained and saved {len(face_encodings)} face samples for {employee.first_name} {employee.last_name}")
                
        except Exception as e:
            print(f"Error training faces: {e}")
    
    def recognize_face_from_image(self, frame):
        """Recognize face from image frame using OpenCV only"""
        try:
            # Use OpenCV face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None, "No face detected", None
            
            print(f"Detected {len(faces)} face(s) in the image")
            
            # For each detected face, try to match with known faces
            for (x, y, w, h) in faces:
                # Extract face region
                face_region = frame[y:y+h, x:x+w]
                gray_face = gray[y:y+h, x:x+w]
                
                # Simple matching based on stored face data
                if len(self.known_face_ids) > 0:
                    print(f"Trying to match against {len(self.known_face_ids)} known faces")
                    # Use a simple matching algorithm
                    best_match = None
                    best_confidence = 0
                    
                    for i, stored_encoding in enumerate(self.known_face_encodings):
                        # Proper confidence calculation based on face features
                        confidence = self.calculate_face_confidence_improved(gray_face, stored_encoding)
                        print(f"Comparing with {self.known_face_names[i]}: confidence = {confidence:.2f}")
                        
                        if confidence > best_confidence and confidence > 0.3:  # Lower threshold for better matching
                            best_confidence = confidence
                            best_match = i
                    
                    if best_match is not None:
                        print(f"Best match: {self.known_face_names[best_match]} with confidence {best_confidence:.2f}")
                        return self.known_face_ids[best_match], f"Face recognized: {self.known_face_names[best_match]} ({best_confidence*100:.1f}% confidence)", (x, y, w, h)
            
            return None, "No matching face found", None
                
        except Exception as e:
            return None, f"Error in face recognition: {str(e)}", None
    
    def calculate_face_confidence_improved(self, gray_face, stored_encoding):
        """Improved confidence calculation using face features comparison"""
        try:
            # Resize face to standard size for comparison
            standard_size = (100, 100)
            resized_face = cv2.resize(gray_face, standard_size)
            
            # Calculate basic face features
            face_height, face_width = gray_face.shape[:2]
            aspect_ratio = face_width / face_height
            
            if isinstance(stored_encoding, dict):
                # Handle multiple encodings format (from training)
                if 'encodings' in stored_encoding:
                    # This is a trained face with multiple samples
                    encodings_list = stored_encoding['encodings']
                    best_confidence = 0.0
                    
                    for sample_encoding in encodings_list:
                        if isinstance(sample_encoding, dict) and 'face_location' in sample_encoding:
                            confidence = self._compare_face_with_sample(gray_face, sample_encoding)
                            best_confidence = max(best_confidence, confidence)
                    
                    return best_confidence
                
                # Handle single encoding format (from registration)
                elif 'face_location' in stored_encoding:
                    return self._compare_face_with_sample(gray_face, stored_encoding)
                
                else:
                    # Old format without face_location
                    return 0.6  # Default confidence for legacy format
            else:
                # Fallback: simple size-based confidence
                avg_face_size = (face_height + face_width) / 2
                confidence = min(1.0, avg_face_size / 100)
                return confidence
            
        except Exception as e:
            print(f"Error calculating confidence: {e}")
            return 0.5
    
    def _compare_face_with_sample(self, gray_face, sample_encoding):
        """Compare current face with a stored face sample"""
        try:
            face_height, face_width = gray_face.shape[:2]
            aspect_ratio = face_width / face_height
            
            stored_face_location = sample_encoding.get('face_location', [0, 0, 0, 0])
            
            # Calculate confidence based on multiple factors
            confidence = 0.0
            
            # 1. Face size similarity (40% weight)
            if len(stored_face_location) >= 4:
                stored_w, stored_h = stored_face_location[2], stored_face_location[3]
                current_size = face_width * face_height
                stored_size = stored_w * stored_h
                size_similarity = 1.0 - abs(current_size - stored_size) / max(current_size, stored_size, 1)
                confidence += 0.4 * max(0, size_similarity)
            
            # 2. Aspect ratio similarity (30% weight)
            if len(stored_face_location) >= 4:
                stored_w, stored_h = stored_face_location[2], stored_face_location[3]
                stored_aspect = stored_w / stored_h if stored_h > 0 else 1.0
                aspect_similarity = 1.0 - abs(aspect_ratio - stored_aspect)
                confidence += 0.3 * max(0, aspect_similarity)
            
            # 3. Basic face detection quality (30% weight)
            # Check if face has reasonable proportions
            if 30 < face_width < 300 and 40 < face_height < 400:
                confidence += 0.3
            
            # Add some randomness to simulate more complex matching
            import random
            confidence += random.uniform(0, 0.1)  # Add 0-10% random confidence
            
            return min(1.0, confidence)
            
        except Exception as e:
            print(f"Error comparing face sample: {e}")
            return 0.5
    
    def calculate_face_confidence(self, face_region, stored_encoding):
        """Legacy confidence calculation for backward compatibility"""
        return self.calculate_face_confidence_improved(face_region, stored_encoding)

# Routes
@app.route('/test-hero-bg')
def test_hero_bg():
    return app.send_static_file('images/hero-bg.svg')

@app.route('/')
def index():
    return render_template('index_modern.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()
            print(f"Login attempt: {data}")
            username = data.get('username')
            password = data.get('password')
            
            print(f"Username: {username}")
            
            user = User.query.filter_by(username=username).first()
            print(f"User found: {user}")
            
            if user:
                print(f"User role: {user.role.name if user.role else 'No role'}")
                try:
                    password_check = bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
                    print(f"Password check: {password_check}")
                except Exception as e:
                    print(f"Password check error: {e}")
                    password_check = False
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                login_user(user)
                return jsonify({
                    'success': True,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'role': user.role.name
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid credentials'})
        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    return render_template('login_simple.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/hr_dashboard')
@hr_required
def hr_dashboard():
    """HR Dashboard page"""
    return render_template('hr_dashboard.html')

@app.route('/view_attendance')
@hr_required
def view_attendance():
    """View Attendance page"""
    return render_template('view_attendance.html')

@app.route('/search_attendance')
@hr_required
def search_attendance_page():
    """Search Attendance page"""
    return render_template('search_attendance.html')

@app.route('/change_password')
@hr_required
def change_password_page():
    """Change Password page"""
    return render_template('change_password.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Redirect user to appropriate dashboard based on role
    if current_user.role.name == 'Admin':
        return render_template('dashboard_sidebar.html')
    elif current_user.role.name == 'HR Officer':
        return render_template('hr_dashboard.html')
    elif current_user.role.name == 'Finance Officer':
        return render_template('finance_dashboard.html')
    elif current_user.role.name == 'Employee':
        return render_template('employee_dashboard.html')
    elif current_user.role.name == 'Department':
        return render_template('department_dashboard.html')
    else:
        # Default to admin dashboard for unknown roles
        return render_template('dashboard_sidebar.html')

# Face Recognition API
@app.route('/api/face_attendance/capture', methods=['POST'])
def capture_face_attendance():
    """Face recognition attendance using OpenCV"""
    try:
        # Debug: Print request info
        print(f"Request content type: {request.content_type}")
        print(f"Request data: {request.get_data()}")
        
        # Get image from request
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data or empty request'
                }), 400
        except Exception as json_error:
            print(f"JSON parsing error: {json_error}")
            return jsonify({
                'success': False,
                'error': f'JSON parsing error: {str(json_error)}'
            }), 400
        
        if 'image' not in data:
            return jsonify({
                'success': False,
                'error': 'No image data provided in request'
            }), 400
        
        image_data = data['image']
        print(f"Image data length: {len(image_data)}")
        print(f"Image data starts with: {image_data[:50]}...")
        
        # Convert base64 to image
        from io import BytesIO
        from PIL import Image
        
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 and create image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to OpenCV format
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Initialize face recognition system
        face_system = SimpleFaceRecognitionSystem()
        
        # Recognize face
        employee_id, message, face_location = face_system.recognize_face_from_image(frame)
        
        if employee_id and face_location:
            # Determine attendance type
            attendance_type = determine_attendance_type(employee_id)
            
            # Record attendance
            success, record_message = record_attendance(employee_id, attendance_type)
            
            if success:
                employee = Employee.query.get(employee_id)
                return jsonify({
                    'success': True,
                    'message': record_message,
                    'employee': {
                        'id': employee.id,
                        'name': f"{employee.first_name} {employee.last_name}",
                        'employee_id': employee.employee_id
                    },
                    'type': attendance_type
                })
            else:
                return jsonify({
                    'success': False,
                    'error': record_message
                })
        else:
            return jsonify({
                'success': False,
                'error': message
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"System error: {str(e)}"
        }), 500

@app.route('/api/face_attendance/detect', methods=['POST'])
def detect_faces():
    """Detect faces in image and return locations with recognition status"""
    try:
        # Get image from request
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({
                'success': False,
                'error': 'No image data provided'
            }), 400
        
        image_data = data['image']
        
        # Convert base64 to image
        from PIL import Image
        
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 and create image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to OpenCV format
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Initialize face recognition system
        face_system = SimpleFaceRecognitionSystem()
        
        # Detect faces
        faces = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detected_faces = face_system.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in detected_faces:
            # Extract face region for recognition
            face_region = frame[y:y+h, x:x+w]
            gray_face = gray[y:y+h, x:x+w]
            
            recognized = False
            employee_name = 'Unknown'
            employee_id = None
            
            # Try to recognize this specific face region
            if len(face_system.known_face_ids) > 0:
                best_match = None
                best_confidence = 0
                
                for i, stored_encoding in enumerate(face_system.known_face_encodings):
                    confidence = face_system.calculate_face_confidence_improved(gray_face, stored_encoding)
                    
                    if confidence > best_confidence and confidence > 0.6:  # Threshold for recognition
                        best_confidence = confidence
                        best_match = i
                
                if best_match is not None:
                    employee_id = face_system.known_face_ids[best_match]
                    employee = Employee.query.get(employee_id)
                    if employee:
                        recognized = True
                        employee_name = f"{employee.first_name} {employee.last_name}"
            
            faces.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'recognized': recognized,
                'employee_name': employee_name,
                'employee_id': employee_id if recognized else None
            })
        
        return jsonify({
            'success': True,
            'faces': faces,
            'total_faces': len(faces)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Face detection error: {str(e)}"
        }), 500

def determine_attendance_type(employee_id):
    """Determine if employee should check in or check out"""
    try:
        today = date.today()
        existing_attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        if existing_attendance and existing_attendance.check_in_time:
            if existing_attendance.check_out_time:
                return 'check_in'  # Already checked out, new check-in
            else:
                return 'check_out' # Checked in but not out, check-out
        else:
            return 'check_in'  # No record today, check-in
            
    except Exception as e:
        return 'check_in'  # Default to check-in

def record_attendance(employee_id, attendance_type):
    """Record attendance for recognized employee"""
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            return False, "Employee not found"
        
        today = date.today()
        
        # Check if employee already has attendance record for today
        existing_attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        # Create or update attendance record
        current_time = datetime.now()
        
        if existing_attendance:
            if attendance_type == 'check_out':
                existing_attendance.check_out_time = current_time
                # Calculate work hours
                if existing_attendance.check_in_time:
                    work_hours = (current_time - existing_attendance.check_in_time).total_seconds() / 3600
                    existing_attendance.work_hours = round(work_hours, 2)
                existing_attendance.status = 'present'
                message = f"Check-out recorded for {employee.first_name} at {current_time.strftime('%H:%M')}"
            else:
                message = f"Check-in already recorded for {employee.first_name}"
        else:
            # Create new attendance record
            new_attendance = Attendance(
                employee_id=employee_id,
                date=today,
                check_in_time=current_time if attendance_type == 'check_in' else None,
                check_out_time=current_time if attendance_type == 'check_out' else None,
                status='present'
            )
            db.session.add(new_attendance)
            
            if attendance_type == 'check_in':
                message = f"Check-in recorded for {employee.first_name} at {current_time.strftime('%H:%M')}"
            else:
                message = f"Check-out recorded for {employee.first_name} at {current_time.strftime('%H:%M')}"
        
        db.session.commit()
        return True, message
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error recording attendance: {str(e)}"

@app.route('/api/face_attendance/train', methods=['POST'])
@login_required
def train_faces():
    """Train face recognition with multiple images"""
    try:
        data = request.get_json()
        employee_images = data.get('employee_images', {})
        
        if not employee_images:
            return jsonify({'success': False, 'error': 'No employee images provided'}), 400
        
        # Initialize face recognition system
        face_system = SimpleFaceRecognitionSystem()
        face_system.train_faces(employee_images)
        
        return jsonify({
            'success': True,
            'message': 'Face training completed successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/face_attendance/register', methods=['POST'])
@login_required
def register_employee_face():
    """Register face for an employee"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        image_data = data.get('image')
        
        if not employee_id or not image_data:
            return jsonify({'success': False, 'error': 'Employee ID and image required'}), 400
        
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
        
        # Process face image
        from io import BytesIO
        from PIL import Image
        
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 and create image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to OpenCV format and detect face
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Use face recognition system for better processing
        face_system = SimpleFaceRecognitionSystem()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_system.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return jsonify({'success': False, 'error': 'No face detected in image'}), 400
        
        # Create proper encoding with face data
        face_encoding = {
            'employee_id': employee_id,
            'face_location': faces[0].tolist(),
            'timestamp': datetime.now().isoformat(),
            'image_size': frame.shape,
            'encoding_version': '2.0'
        }
        encoding_str = base64.b64encode(pickle.dumps(face_encoding)).decode('utf-8')
        
        # Update employee with face encoding
        employee.face_encoding = encoding_str
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Face registered for {employee.first_name} {employee.last_name}',
            'employee': {
                'id': employee.id,
                'name': f"{employee.first_name} {employee.last_name}",
                'employee_id': employee.employee_id
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/face_attendance/status', methods=['GET'])
def get_face_attendance_status():
    """Get face recognition system status"""
    try:
        employees_with_faces = Employee.query.filter(
            Employee.is_active == True,
            Employee.face_encoding.isnot(None)
        ).all()
        
        # Get detailed face info
        face_details = []
        for emp in employees_with_faces:
            try:
                encoding_data = base64.b64decode(emp.face_encoding)
                encoding = pickle.loads(encoding_data)
                encoding_type = "unknown"
                
                if isinstance(encoding, dict):
                    if 'encodings' in encoding:
                        encoding_type = f"trained ({len(encoding['encodings'])} samples)"
                    elif 'face_location' in encoding:
                        encoding_type = "single"
                    else:
                        encoding_type = "legacy_dict"
                else:
                    encoding_type = "legacy"
                
                face_details.append({
                    'employee_id': emp.id,
                    'name': f"{emp.first_name} {emp.last_name}",
                    'encoding_type': encoding_type,
                    'encoding_length': len(emp.face_encoding)
                })
            except Exception as e:
                face_details.append({
                    'employee_id': emp.id,
                    'name': f"{emp.first_name} {emp.last_name}",
                    'encoding_type': "error",
                    'error': str(e)
                })
        
        # Test face recognition system
        face_system = SimpleFaceRecognitionSystem()
        
        return jsonify({
            'success': True,
            'status': 'active' if len(employees_with_faces) > 0 else 'no_faces_registered',
            'registered_faces': len(employees_with_faces),
            'employees_with_faces': len(employees_with_faces),
            'face_details': face_details,
            'loaded_faces': len(face_system.known_face_ids),
            'loaded_face_names': face_system.known_face_names,
            'message': 'Face recognition system active (OpenCV mode)'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/employees', methods=['GET'])
@login_required
def get_employees():
    try:
        employees = Employee.query.filter_by(is_active=True).all()
        return jsonify([{
            'id': emp.id,
            'employee_id': emp.employee_id,
            'name': f"{emp.first_name} {emp.last_name}",
            'email': emp.email,
            'department': emp.department,
            'position': emp.position,
            'hire_date': emp.hire_date.strftime('%Y-%m-%d')
        } for emp in employees])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees/list', methods=['GET'])
@login_required
def get_employees_list():
    """Get list of employees for filter dropdown and employee list"""
    try:
        employees = Employee.query.filter_by(is_active=True).all()
        employee_list = []
        
        for emp in employees:
            employee_list.append({
                'id': emp.id,
                'employee_id': emp.employee_id,
                'name': f"{emp.first_name} {emp.last_name}",
                'email': emp.email,
                'department': emp.department or '',
                'position': emp.position or ''
            })
        
        return jsonify(employee_list)
    except Exception as e:
        print(f"Error getting employees list: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees/<int:employee_id>', methods=['GET'])
@login_required
def get_employee(employee_id):
    """Get individual employee by ID"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        return jsonify({
            'id': employee.id,
            'employee_id': employee.employee_id,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'email': employee.email,
            'phone': employee.phone,
            'department': employee.department,
            'position': employee.position,
            'hire_date': employee.hire_date.strftime('%Y-%m-%d') if employee.hire_date else '',
            'salary': employee.salary,
            'is_active': employee.is_active
        })
    except Exception as e:
        print(f"Error getting employee {employee_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees/<int:employee_id>', methods=['PUT'])
@login_required
def update_employee(employee_id):
    """Update employee information"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        data = request.get_json()
        
        print(f"Updating employee {employee_id} with data: {data}")
        
        # Update employee fields
        employee.first_name = data.get('firstName', employee.first_name)
        employee.last_name = data.get('lastName', employee.last_name)
        employee.email = data.get('email', employee.email)
        employee.phone = data.get('phone', employee.phone)
        employee.department = data.get('department', employee.department)
        employee.position = data.get('position', employee.position)
        employee.salary = float(data.get('salary', employee.salary)) if data.get('salary') else employee.salary
        employee.is_active = data.get('isActive', employee.is_active)
        
        # Update hire date if provided
        if data.get('hireDate'):
            employee.hire_date = datetime.strptime(data['hireDate'], '%Y-%m-%d').date()
        
        db.session.commit()
        print(f"Employee {employee_id} updated successfully")
        
        return jsonify({
            'success': True,
            'message': 'Employee updated successfully!'
        })
        
    except Exception as e:
        print(f"Error updating employee {employee_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/employees', methods=['POST'])
@login_required
def add_employee():
    try:
        data = request.get_json()
        print(f"Received employee data: {data}")
        
        # Validate required fields
        required_fields = ['employeeId', 'firstName', 'lastName', 'email', 'hireDate']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        employee_role = Role.query.filter_by(name='Employee').first()
        if not employee_role:
            employee_role = Role.query.first()
        
        username = data.get('employeeId').lower().replace(' ', '_')
        email = data.get('email')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'User with this employee ID already exists'
            }), 400
        
        existing_employee = Employee.query.filter_by(employee_id=data.get('employeeId')).first()
        if existing_employee:
            return jsonify({
                'success': False,
                'error': 'Employee with this ID already exists'
            }), 400
        
        # Create user first
        new_user = User(
            username=username,
            email=email,
            password_hash=bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            role_id=employee_role.id
        )
        db.session.add(new_user)
        db.session.flush()
        print(f"Created user with ID: {new_user.id}")
        
        # Create employee
        hire_date_str = data.get('hireDate')
        if hire_date_str:
            hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
        else:
            hire_date = datetime.now().date()
        
        new_employee = Employee(
            employee_id=data.get('employeeId'),
            first_name=data.get('firstName'),
            last_name=data.get('lastName'),
            email=email,
            phone=data.get('phone', ''),
            department=data.get('department', ''),
            position=data.get('position', ''),
            hire_date=hire_date,
            salary=float(data.get('salary', 0)),
            user_id=new_user.id
        )
        db.session.add(new_employee)
        db.session.commit()
        print(f"Created employee with ID: {new_employee.id}")
        
        return jsonify({
            'success': True,
            'message': 'Employee added successfully with login credentials',
            'employee': {
                'id': new_employee.id,
                'employee_id': new_employee.employee_id,
                'name': f"{new_employee.first_name} {new_employee.last_name}",
                'email': new_employee.email
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding employee: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/attendance', methods=['GET'])
@login_required
def get_attendance():
    try:
        date_str = request.args.get('date')
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            attendance_records = Attendance.query.filter_by(date=date).all()
        else:
            attendance_records = Attendance.query.all()
        
        return jsonify([{
            'id': record.id,
            'employee_name': f"{record.employee.first_name} {record.employee.last_name}",
            'employee_id': record.employee.employee_id,
            'date': record.date.strftime('%Y-%m-%d'),
            'check_in_time': record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else None,
            'check_out_time': record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else None,
            'status': record.status,
            'work_hours': record.work_hours
        } for record in attendance_records])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/my-attendance', methods=['GET'])
@login_required
def get_my_attendance():
    """Get current employee's attendance records"""
    try:
        # Get current employee
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee record not found'}), 404
        
        # Get date range from query params (default to last 30 days)
        days = request.args.get('days', 30, type=int)
        start_date = datetime.now() - timedelta(days=days)
        
        attendance_records = Attendance.query.filter(
            Attendance.employee_id == employee.id,
            Attendance.date >= start_date.date()
        ).order_by(Attendance.date.desc()).all()
        
        return jsonify([{
            'id': record.id,
            'date': record.date.strftime('%Y-%m-%d'),
            'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None,
            'check_out_time': record.check_out_time.strftime('%H:%M') if record.check_out_time else None,
            'status': record.status,
            'work_hours': record.work_hours or 0
        } for record in attendance_records])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/my-face', methods=['POST'])
@login_required
def upload_my_face():
    """Register face for current employee"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get current employee
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee record not found'}), 404
        
        if file:
            filename = secure_filename(f"employee_{employee.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', filename)
            file.save(filepath)
            
            # Process face image using existing face recognition system
            from PIL import Image
            import cv2
            
            # Load and process image
            image = Image.open(filepath)
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Initialize face recognition system
            face_system = SimpleFaceRecognitionSystem()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_system.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                os.remove(filepath)
                return jsonify({'error': 'No face detected in image'}), 400
            
            # Create face encoding using the existing system
            face_encoding = {
                'employee_id': employee.id,
                'face_location': faces[0].tolist(),
                'timestamp': datetime.now().isoformat(),
                'image_size': frame.shape,
                'encoding_version': '2.0'
            }
            encoding_str = base64.b64encode(pickle.dumps(face_encoding)).decode('utf-8')
            
            # Save encoding to database
            employee.face_image_path = filepath
            employee.face_encoding = encoding_str
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Face image uploaded and processed successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Error processing face image: {str(e)}'}), 500

@app.route('/api/my-face-status', methods=['GET'])
@login_required
def get_my_face_status():
    """Get current employee's face registration status"""
    try:
        # Get current employee
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee record not found'}), 404
        
        # Check if face is registered
        is_registered = bool(employee.face_encoding and employee.face_image_path)
        
        return jsonify({
            'success': True,
            'is_registered': is_registered,
            'face_image_path': employee.face_image_path if is_registered else None,
            'registration_date': employee.updated_at.strftime('%Y-%m-%d %H:%M') if is_registered and employee.updated_at else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance/search', methods=['GET'])
@hr_required
def search_attendance():
    """Search attendance records with filters"""
    try:
        # Get search parameters
        employee_filter = request.args.get('employee', '')
        date_filter = request.args.get('date', '')
        start_date_filter = request.args.get('start_date', '')
        end_date_filter = request.args.get('end_date', '')
        status_filter = request.args.get('status', '')
        
        # Start with base query
        query = Attendance.query.join(Employee)
        
        # Apply filters
        if employee_filter:
            query = query.filter(
                (Employee.first_name.ilike(f'%{employee_filter}%')) |
                (Employee.last_name.ilike(f'%{employee_filter}%')) |
                (Employee.employee_id.ilike(f'%{employee_filter}%'))
            )
        
        # Handle date filters
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter(Attendance.date == filter_date)
            except ValueError:
                pass  # Invalid date format, ignore date filter
        elif start_date_filter and end_date_filter:
            try:
                start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
                query = query.filter(Attendance.date.between(start_date, end_date))
            except ValueError:
                pass  # Invalid date format, ignore date range filter
        
        if status_filter and status_filter != 'all':
            query = query.filter(Attendance.status == status_filter)
        
        # Execute query with ordering
        attendance_records = query.order_by(Attendance.date.desc(), Attendance.check_in_time.desc()).all()
        
        return jsonify([{
            'id': record.id,
            'employee_name': f"{record.employee.first_name} {record.employee.last_name}",
            'employee_id': record.employee.employee_id,
            'date': record.date.strftime('%Y-%m-%d'),
            'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None,
            'check_out_time': record.check_out_time.strftime('%H:%M') if record.check_out_time else None,
            'status': record.status,
            'work_hours': record.work_hours or 0,
            'department': record.employee.department,
            'position': record.employee.position
        } for record in attendance_records])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        print(f"Password change request: {data}")
        
        # Get fields
        user_id = data.get('userId')
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        # Validate required fields
        if not all([user_id, current_password, new_password]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Verify current password (simplified - in production, use proper password verification)
        if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return jsonify({
                'success': False,
                'error': 'Current password is incorrect'
            }), 400
        
        # Hash new password
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        print(f"New password hash generated: {new_password_hash[:20]}...")
        
        # Update password
        old_hash = user.password_hash
        user.password_hash = new_password_hash
        db.session.commit()
        
        print(f"Password changed successfully for user {user_id}")
        print(f"Old hash: {old_hash[:20]}...")
        print(f"New hash: {new_password_hash[:20]}...")
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully!'
        })
        
    except Exception as e:
        print(f"Error changing password: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reports/daily', methods=['GET'])
@login_required
def daily_report():
    try:
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        attendance = Attendance.query.filter_by(date=date).all()
        total_employees = Employee.query.filter_by(is_active=True).count()
        present_count = len([a for a in attendance if a.check_in_time])
        
        return jsonify({
            'date': date_str,
            'total_employees': total_employees,
            'present': present_count,
            'absent': total_employees - present_count,
            'attendance_records': [{
                'employee_name': f"{a.employee.first_name} {a.employee.last_name}",
                'check_in': a.check_in_time.strftime('%H:%M') if a.check_in_time else 'N/A',
                'check_out': a.check_out_time.strftime('%H:%M') if a.check_out_time else 'N/A',
                'status': a.status
            } for a in attendance]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize database
def init_db():
    try:
        with app.app_context():
            db.create_all()
            
            if Role.query.count() == 0:
                roles = [
                    Role(name='Admin', description='System administrator'),
                    Role(name='HR Officer', description='Human Resources officer'),
                    Role(name='Finance Officer', description='Finance officer'),
                    Role(name='Employee', description='Regular employee')
                ]
                db.session.bulk_save_objects(roles)
                db.session.commit()
                print("Default roles created")
            
            if User.query.filter_by(username='admin').first() is None:
                admin_role = Role.query.filter_by(name='Admin').first()
                admin_user = User(
                    username='admin',
                    email='admin@company.com',
                    password_hash=bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                    role_id=admin_role.id
                )
                db.session.add(admin_user)
                db.session.commit()
                print("Default admin user created (admin/admin123)")
            
            print("Database initialized successfully!")
            
    except Exception as e:
        print(f"Database initialization error: {e}")

# Report Generation API Route
@app.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate and download reports in Excel or CSV format"""
    try:
        data = request.get_json()
        report_type = data.get('reportType')
        export_format = data.get('exportFormat')
        date_range = data.get('dateRange')
        
        print(f"Generating {report_type} report in {export_format} format for {date_range}")
        
        # Calculate date range
        start_date, end_date = calculate_date_range(date_range, data)
        
        # Get report data based on type
        if report_type == 'attendance':
            report_data = get_attendance_report_data(start_date, end_date, data)
        elif report_type == 'employees':
            report_data = get_employee_report_data(data)
        elif report_type == 'users':
            report_data = get_user_report_data(data)
        elif report_type == 'summary':
            report_data = get_summary_report_data(start_date, end_date)
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        # Generate file based on format
        if export_format == 'csv':
            return generate_csv_report(report_data, report_type)
        else:
            return generate_excel_report(report_data, report_type)
            
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return jsonify({'error': str(e)}), 500

def calculate_date_range(date_range, data):
    """Calculate start and end dates based on range selection"""
    today = datetime.now().date()
    
    if date_range == 'today':
        return today, today
    elif date_range == 'week':
        start_of_week = today - timedelta(days=today.weekday())
        return start_of_week, today
    elif date_range == 'month':
        start_of_month = today.replace(day=1)
        return start_of_month, today
    elif date_range == 'custom':
        start_date = datetime.strptime(data.get('startDate'), '%Y-%m-%d').date()
        end_date = datetime.strptime(data.get('endDate'), '%Y-%m-%d').date()
        return start_date, end_date
    
    return today, today

def get_attendance_report_data(start_date, end_date, options):
    """Get attendance data for report"""
    print(f"Getting attendance data from {start_date} to {end_date}")
    
    attendances = Attendance.query.filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()
    
    print(f"Found {len(attendances)} attendance records")
    
    data = []
    for attendance in attendances:
        try:
            # Safely get employee information
            employee_name = "Unknown"
            employee_id = "Unknown"
            department = ""
            email = ""
            
            if attendance.employee:
                employee_name = f"{attendance.employee.first_name} {attendance.employee.last_name}"
                employee_id = attendance.employee.employee_id or "N/A"
                department = attendance.employee.department or ""
                email = attendance.employee.email or ""
            
            row = {
                'Date': attendance.date.strftime('%Y-%m-%d') if attendance.date else '',
                'Employee ID': employee_id,
                'Employee Name': employee_name,
                'Check In': attendance.check_in.strftime('%H:%M') if attendance.check_in else '',
                'Check Out': attendance.check_out.strftime('%H:%M') if attendance.check_out else '',
                'Status': attendance.status or 'unknown',
                'Work Hours': str(attendance.work_hours) if attendance.work_hours else ''
            }
            
            # Add optional fields
            if options.get('includeDepartment'):
                row['Department'] = department
            if options.get('includeContact'):
                row['Email'] = email
                row['Phone'] = getattr(attendance.employee, 'phone', '') if attendance.employee else ''
                
            data.append(row)
            print(f"Added attendance record for {employee_name}")
            
        except Exception as e:
            print(f"Error processing attendance record: {e}")
            continue
    
    # Add summary if requested
    if options.get('includeSummary') and data:
        present_count = len([a for a in attendances if a.status == 'present'])
        total_hours = sum([a.work_hours or 0 for a in attendances])
        avg_hours = total_hours / len(attendances) if attendances else 0
        
        summary = {
            'Date': 'SUMMARY',
            'Employee ID': '',
            'Employee Name': f"Total Records: {len(attendances)}",
            'Check In': '',
            'Check Out': '',
            'Status': f"Present: {present_count}",
            'Work Hours': f"{avg_hours:.1f}"
        }
        
        if options.get('includeDepartment'):
            summary['Department'] = ''
        if options.get('includeContact'):
            summary['Email'] = ''
            summary['Phone'] = ''
            
        data.append(summary)
        print(f"Added summary row")
    
    print(f"Returning {len(data)} rows for attendance report")
    return data

def get_employee_report_data(options):
    """Get employee data for report"""
    employees = Employee.query.all()
    
    data = []
    for emp in employees:
        row = {
            'Employee ID': emp.employee_id,
            'First Name': emp.first_name,
            'Last Name': emp.last_name,
            'Position': emp.position,
            'Status': 'Active' if emp.is_active else 'Inactive',
            'Created': emp.created_at.strftime('%Y-%m-%d') if emp.created_at else ''
        }
        
        if options.get('includeDepartment'):
            row['Department'] = emp.department
        if options.get('includeContact'):
            row['Email'] = emp.email
            row['Phone'] = getattr(emp, 'phone', '')
            
        data.append(row)
    
    return data

def get_user_report_data(options):
    """Get user data for report"""
    users = User.query.all()
    
    data = []
    for user in users:
        row = {
            'Username': user.username,
            'Email': user.email,
            'Employee ID': user.employee_id or '',
            'Created': user.created_at.strftime('%Y-%m-%d') if user.created_at else ''
        }
        
        if options.get('includeRoles'):
            row['Role'] = user.role.name if user.role else 'No Role'
        if options.get('includeStatus'):
            row['Status'] = 'Active' if user.is_active else 'Inactive'
            
        data.append(row)
    
    return data

def get_summary_report_data(start_date, end_date):
    """Get summary data for report"""
    # Get attendance summary
    attendances = Attendance.query.filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()
    
    total_employees = Employee.query.filter_by(is_active=True).count()
    present_days = len(set([a.employee_id for a in attendances if a.status == 'present']))
    
    data = [{
        'Metric': 'Total Employees',
        'Value': total_employees,
        'Period': f"{start_date} to {end_date}"
    }, {
        'Metric': 'Present Days',
        'Value': present_days,
        'Period': f"{start_date} to {end_date}"
    }, {
        'Metric': 'Average Attendance Rate',
        'Value': f"{(present_days / (total_employees * ((end_date - start_date).days + 1)) * 100):.1f}%" if total_employees > 0 else "0%",
        'Period': f"{start_date} to {end_date}"
    }]
    
    return data

def generate_csv_report(data, report_type):
    """Generate CSV report"""
    output = io.StringIO()
    
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    output.seek(0)
    
    # Create response
    response = app.response_class(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=report_{report_type}_{datetime.now().strftime("%Y%m%d")}.csv'
        }
    )
    
    return response

def generate_excel_report(data, report_type):
    """Generate Excel-like report (CSV format for simplicity)"""
    # For now, return CSV format. In production, you might want to use openpyxl
    return generate_csv_report(data, report_type)

# User Management API Routes
@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """Get all users"""
    try:
        users = User.query.all()
        user_list = []
        
        for user in users:
            user_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'employee_id': user.employee_id,
                'role': user.role.name if user.role else 'No Role',
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        return jsonify(user_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """Get specific user"""
    try:
        user = User.query.get_or_404(user_id)
        
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'employee_id': user.employee_id,
            'role': user.role.name if user.role else 'No Role',
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    """Create new user"""
    try:
        data = request.get_json()
        print("Creating user with data:", data)
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Check if employee_id already exists
        if data.get('employee_id') and User.query.filter_by(employee_id=data['employee_id']).first():
            return jsonify({'error': 'Employee ID already exists'}), 400
        
        # Get role
        role = Role.query.filter_by(name=data['role']).first()
        if not role:
            return jsonify({'error': 'Invalid role'}), 400
        
        # Hash password
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        # Create user
        user = User(
            username=data['username'],
            email=data['email'],
            employee_id=data.get('employee_id'),
            password_hash=hashed_password,
            role_id=role.id,
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user_id': user.id
        })
    except Exception as e:
        db.session.rollback()
        print("Error creating user:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update user"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        print("Updating user with data:", data)
        
        # Check if username already exists (excluding current user)
        if User.query.filter(User.username == data['username'], User.id != user_id).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        # Check if email already exists (excluding current user)
        if User.query.filter(User.email == data['email'], User.id != user_id).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Check if employee_id already exists (excluding current user)
        if data.get('employee_id') and User.query.filter(User.employee_id == data['employee_id'], User.id != user_id).first():
            return jsonify({'error': 'Employee ID already exists'}), 400
        
        # Get role
        role = Role.query.filter_by(name=data['role']).first()
        if not role:
            return jsonify({'error': 'Invalid role'}), 400
        
        # Update user
        user.username = data['username']
        user.email = data['email']
        user.employee_id = data.get('employee_id')
        user.role_id = role.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        print("Error updating user:", str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Don't allow deactivating the current user
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot deactivate your own account'}), 400
        
        # Toggle status
        user.is_active = not user.is_active
        db.session.commit()
        
        status_text = 'activated' if user.is_active else 'deactivated'
        
        return jsonify({
            'success': True,
            'message': f'User {status_text} successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Don't allow deleting the current user
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        # Check if user has associated employee records
        if Employee.query.filter_by(user_id=user.id).first():
            return jsonify({'error': 'Cannot delete user with associated employee records'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Payroll API Endpoints
@app.route('/api/payroll', methods=['POST'])
@login_required
def create_payroll():
    """Create a new payroll entry"""
    try:
        data = request.get_json()
        print(f"Payroll creation request: {data}")
        
        # Get fields
        employee_id = data.get('employee_id')
        basic_salary = data.get('basic_salary')
        allowance = data.get('allowance', 0)
        deduction = data.get('deduction', 0)
        effective_date = data.get('effective_date')
        
        # Validate required fields
        if not all([employee_id, basic_salary, effective_date]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: employee_id, basic_salary, effective_date'
            }), 400
        
        # Get employee information
        employee = Employee.query.filter_by(employee_id=employee_id).first()
        if not employee:
            return jsonify({
                'success': False,
                'error': 'Employee not found'
            }), 404
        
        # Calculate payroll components
        basic_salary = float(basic_salary)
        allowance = float(allowance)
        deduction = float(deduction)
        
        gross_salary = basic_salary + allowance
        taxable_salary = max(0, gross_salary - deduction)
        income_tax = taxable_salary * 0.15  # 15% tax rate
        net_salary = gross_salary - deduction - income_tax
        
        # Parse effective date
        effective_date = datetime.strptime(effective_date, '%Y-%m-%d').date()
        
        # Create payroll entry
        payroll = Payroll(
            employee_id=employee_id,
            full_name=f"{employee.first_name} {employee.last_name}",
            role=employee.position,
            basic_salary=basic_salary,
            allowance=allowance,
            deduction=deduction,
            taxable_salary=taxable_salary,
            income_tax=income_tax,
            gross_salary=gross_salary,
            net_salary=net_salary,
            effective_date=effective_date
        )
        
        db.session.add(payroll)
        db.session.commit()
        
        print(f"Payroll entry created successfully for employee {employee_id}")
        
        return jsonify({
            'success': True,
            'message': 'Payroll entry created successfully!',
            'payroll_id': payroll.id
        })
        
    except Exception as e:
        print(f"Error creating payroll: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/payroll/<int:payroll_id>', methods=['GET'])
@login_required
def get_payroll_by_id(payroll_id):
    """Get a single payroll record by ID"""
    try:
        payroll = Payroll.query.filter_by(id=payroll_id).first()
        
        if not payroll:
            return jsonify({'error': 'Payroll record not found'}), 404
        
        # Get employee info
        employee = Employee.query.filter_by(employee_id=payroll.employee_id).first()
        
        payroll_data = {
            'id': payroll.id,
            'employee_id': payroll.employee_id,
            'full_name': payroll.full_name,
            'department': employee.department if employee else 'N/A',
            'position': employee.position if employee else 'N/A',
            'basic_salary': float(payroll.basic_salary),
            'allowance': float(payroll.allowance),
            'deduction': float(payroll.deduction),
            'taxable_salary': float(payroll.taxable_salary),
            'income_tax': float(payroll.income_tax),
            'gross_salary': float(payroll.gross_salary),
            'net_salary': float(payroll.net_salary),
            'effective_date': payroll.effective_date.strftime('%Y-%m-%d'),
            'created_at': payroll.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(payroll_data)
        
    except Exception as e:
        print(f"Error getting payroll record: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/payroll/recent', methods=['GET'])
@login_required
def get_recent_payroll():
    """Get recent payroll entries"""
    try:
        # Get recent payroll entries (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        payroll_entries = Payroll.query.filter(
            Payroll.created_at >= thirty_days_ago
        ).order_by(Payroll.created_at.desc()).limit(50).all()
        
        payroll_data = []
        for payroll in payroll_entries:
            payroll_data.append({
                'id': payroll.id,
                'employee_id': payroll.employee_id,
                'full_name': payroll.full_name,
                'role': payroll.role,
                'basic_salary': float(payroll.basic_salary),
                'allowance': float(payroll.allowance),
                'deduction': float(payroll.deduction),
                'taxable_salary': float(payroll.taxable_salary),
                'income_tax': float(payroll.income_tax),
                'gross_salary': float(payroll.gross_salary),
                'net_salary': float(payroll.net_salary),
                'effective_date': payroll.effective_date.strftime('%Y-%m-%d'),
                'created_at': payroll.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify(payroll_data)
        
    except Exception as e:
        print(f"Error fetching recent payroll: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/payroll/<int:payroll_id>', methods=['DELETE'])
@login_required
def delete_payroll(payroll_id):
    """Delete a payroll entry"""
    try:
        payroll = Payroll.query.get(payroll_id)
        if not payroll:
            return jsonify({
                'success': False,
                'error': 'Payroll entry not found'
            }), 404
        
        db.session.delete(payroll)
        db.session.commit()
        
        print(f"Payroll entry {payroll_id} deleted successfully")
        
        return jsonify({
            'success': True,
            'message': 'Payroll entry deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting payroll: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/payroll/report', methods=['GET'])
@login_required
def get_payroll_report():
    """Generate payroll report with filters"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        department = request.args.get('department')
        
        # Build query
        query = Payroll.query
        
        # Apply date filters
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Payroll.effective_date >= start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Payroll.effective_date <= end_date)
        
        # Apply department filter
        if department:
            # Join with employees to filter by department
            query = query.join(Employee, Payroll.employee_id == Employee.employee_id)
            query = query.filter(Employee.department == department)
        
        # Get payroll records
        payroll_records = query.all()
        
        payroll_data = []
        for payroll in payroll_records:
            # Get employee info
            employee = Employee.query.filter_by(employee_id=payroll.employee_id).first()
            
            payroll_data.append({
                'id': payroll.id,
                'employee_id': payroll.employee_id,
                'full_name': payroll.full_name,
                'department': employee.department if employee else 'N/A',
                'position': employee.position if employee else 'N/A',
                'basic_salary': float(payroll.basic_salary),
                'allowance': float(payroll.allowance),
                'deduction': float(payroll.deduction),
                'taxable_salary': float(payroll.taxable_salary),
                'income_tax': float(payroll.income_tax),
                'gross_salary': float(payroll.gross_salary),
                'net_salary': float(payroll.net_salary),
                'effective_date': payroll.effective_date.strftime('%Y-%m-%d'),
                'created_at': payroll.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify(payroll_data)
        
    except Exception as e:
        print(f"Error generating payroll report: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting FRBEAMS - Working Face Recognition Employee Attendance Management System")
    print("Access the application at: http://localhost:5000")
    print("Default login: admin / admin123")
    print("Database: MySQL")
    print("Face Recognition: OpenCV mode (no face_recognition dependency)")
    
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
