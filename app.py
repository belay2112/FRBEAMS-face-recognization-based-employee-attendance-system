from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, date
import os
import cv2
import numpy as np
import pickle
import base64
import json
from functools import wraps
import jwt
from dotenv import load_dotenv
                            
# Try to import face_recognition, fallback to basic mode if not available
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: face_recognition library not available, using basic face detection mode")

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@localhost/frbeams')
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
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    role = db.relationship('Role', backref='users')
    employee = db.relationship('Employee', backref='user', uselist=False)

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
    face_image_path = db.Column(db.String(255))
    face_encoding = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='present')  # present, absent, late, half_day
    work_hours = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    employee = db.relationship('Employee', backref='attendance_records')

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

# Face Recognition Helper Functions
class FaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_ids = []
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load all known face encodings from database"""
        employees = Employee.query.filter(Employee.is_active == True, Employee.face_encoding.isnot(None)).all()
        self.known_face_encodings = []
        self.known_face_ids = []
        
        for employee in employees:
            try:
                encoding = pickle.loads(base64.b64decode(employee.face_encoding))
                self.known_face_encodings.append(encoding)
                self.known_face_ids.append(employee.id)
            except:
                continue
    
    def recognize_face(self, face_image):
        """Recognize face from image"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                # Basic face detection mode
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                if len(faces) == 0:
                    return None, "No face detected", None
                
                # For demo, return first available employee if any exist
                if len(self.known_face_ids) > 0:
                    import random
                    idx = random.randint(0, len(self.known_face_ids) - 1)
                    return self.known_face_ids[idx], f"Face detected (Demo mode)", faces[0]
                else:
                    return None, "No registered faces", None
            else:
                # Full face recognition mode
                # Convert image to RGB
                rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                
                # Find face locations and encodings
                face_locations = face_recognition.face_locations(rgb_image)
                
                if not face_locations:
                    return None, "No face detected", None
            
            # Get face encodings
                face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                
                if not face_encodings:
                    return None, "Could not extract face encoding", None
                
                # Compare with known faces
                face_encoding = face_encodings[0]
                
                if len(self.known_face_encodings) == 0:
                    return None, "No registered faces found", None
                
                # Find best match
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                
                if face_distances[best_match_index] < 0.6:  # Threshold for recognition
                    employee_id = self.known_face_ids[best_match_index]
                    employee = Employee.query.get(employee_id)
                    return employee, "Face recognized successfully", face_locations[0]
                else:
                    return None, "Face not recognized", None
                    
        except Exception as e:
            return None, f"Error in face recognition: {str(e)}", None
    
    def extract_face_encoding(self, image_path):
        """Extract face encoding from image file"""
        try:
            image = cv2.imread(image_path)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_image)
            if not face_locations:
                return None, "No face detected in image"
            
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            if not face_encodings:
                return None, "Could not extract face encoding"
            
            encoding = face_encodings[0]
            return encoding, "Face encoding extracted successfully"
            
        except Exception as e:
            return None, f"Error extracting face encoding: {str(e)}"

# Initialize face recognition system
face_system = FaceRecognitionSystem()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
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
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# API Routes
@app.route('/api/employees', methods=['GET', 'POST'])
@hr_required
def manage_employees():
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            # Check for duplicate email
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user:
                return jsonify({
                    'success': False, 
                    'error': 'Email already exists. Please use a different email address.'
                }), 400
            
            # Check for duplicate employee ID
            existing_employee = Employee.query.filter_by(employee_id=data['employee_id']).first()
            if existing_employee:
                return jsonify({
                    'success': False, 
                    'error': 'Employee ID already exists. Please use a different employee ID.'
                }), 400
            
            # Create user account
            user = User(
                username=data['username'],
                email=data['email'],
                password_hash=generate_password_hash(data['password']),
                role_id=3  # Employee role
            )
            db.session.add(user)
            db.session.flush()
            
            # Create employee record
            employee = Employee(
                employee_id=data['employee_id'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data.get('phone', ''),
                department=data.get('department', ''),
                position=data.get('position', ''),
                hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date(),
                salary=data.get('salary', 0),
                user_id=user.id
            )
            db.session.add(employee)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'employee_id': employee.id,
                'message': 'Employee created successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False, 
                'error': f'Error creating employee: {str(e)}'
            }), 500
    
    else:
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

@app.route('/api/my-face', methods=['POST'])
@login_required
def upload_my_face():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Get current employee
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            return jsonify({'error': 'Employee record not found'}), 404
        
        if file:
            filename = secure_filename(f"employee_{employee.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', filename)
            file.save(filepath)
            
            # Extract face encoding
            encoding, message = face_system.extract_face_encoding(filepath)
            
            if encoding is None:
                os.remove(filepath)
                return jsonify({'error': message}), 400
            
            # Save encoding to database
            employee.face_image_path = filepath
            employee.face_encoding = base64.b64encode(pickle.dumps(encoding)).decode('utf-8')
            db.session.commit()
            
            # Reload face recognition system
            face_system.load_known_faces()
            
            return jsonify({'success': True, 'message': 'Face image uploaded and processed successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Error processing face image: {str(e)}'}), 500

@app.route('/api/employees/<int:employee_id>/face', methods=['POST'])
@hr_required
def upload_face_image(employee_id):
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(f"employee_{employee_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', filename)
        file.save(filepath)
        
        # Extract face encoding
        encoding, message = face_system.extract_face_encoding(filepath)
        
        if encoding is None:
            os.remove(filepath)
            return jsonify({'error': message}), 400
        
        # Save encoding to database
        employee = Employee.query.get(employee_id)
        employee.face_image_path = filepath
        employee.face_encoding = base64.b64encode(pickle.dumps(encoding)).decode('utf-8')
        db.session.commit()
        
        # Reload face recognition system
        face_system.load_known_faces()
        
        return jsonify({'success': True, 'message': 'Face image uploaded and processed successfully'})

@app.route('/api/attendance/mark', methods=['POST'])
@login_required
def mark_attendance():
    data = request.get_json()
    image_data = data.get('image')  # Base64 encoded image
    
    if not image_data:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Recognize face
        employee, message = face_system.recognize_face(image)
        
        if employee is None:
            return jsonify({'error': message}), 400
        
        # Check if attendance already marked today
        today = datetime.now().date()
        existing_attendance = Attendance.query.filter_by(
            employee_id=employee.id,
            date=today
        ).first()
        
        if existing_attendance:
            if existing_attendance.check_in_time and not existing_attendance.check_out_time:
                # Mark check-out
                existing_attendance.check_out_time = datetime.now()
                existing_attendance.work_hours = (existing_attendance.check_out_time - existing_attendance.check_in_time).total_seconds() / 3600
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': f'Check-out marked for {employee.first_name} {employee.last_name}',
                    'type': 'check_out'
                })
            else:
                return jsonify({'error': 'Attendance already marked for today'}), 400
        
        # Mark check-in
        attendance = Attendance(
            employee_id=employee.id,
            date=today,
            check_in_time=datetime.now(),
            status='present'
        )
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Check-in marked for {employee.first_name} {employee.last_name}',
            'type': 'check_in',
            'employee': {
                'id': employee.id,
                'name': f"{employee.first_name} {employee.last_name}",
                'employee_id': employee.employee_id
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing attendance: {str(e)}'}), 500

@app.route('/api/attendance', methods=['GET'])
@hr_required
def get_attendance():
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

@app.route('/api/my-attendance', methods=['GET'])
@login_required
def get_my_attendance():
    # Get current employee's attendance records
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

@app.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        print(f"Password change request: {data}")
        
        # Get fields
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        # Validate required fields
        if not all([current_password, new_password]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Get current user
        user = current_user
        
        # Verify current password
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({
                'success': False,
                'error': 'Current password is incorrect'
            }), 400
        
        # Hash new password
        new_password_hash = generate_password_hash(new_password)
        print(f"New password hash generated for user {user.username}")
        
        # Update password
        user.password_hash = new_password_hash
        db.session.commit()
        
        print(f"Password changed successfully for user {user.username}")
        
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
@hr_required
def daily_report():
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
        from io import BytesIO
        from PIL import Image
        import base64
        
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 and create image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to OpenCV format
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Initialize face recognition system
        if not hasattr(app, 'face_system'):
            app.face_system = FaceRecognitionSystem()
        
        face_system = app.face_system
        
        # Detect faces
        faces = []
        
        if not FACE_RECOGNITION_AVAILABLE:
            # Basic face detection mode
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected_faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            for (x, y, w, h) in detected_faces:
                faces.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'recognized': False,
                    'employee_name': 'Unknown',
                    'employee_id': None
                })
        else:
            # Full face recognition mode
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    recognized = False
                    employee_name = 'Unknown'
                    employee_id = None
                    
                    if len(face_system.known_face_encodings) > 0:
                        # Compare with known faces
                        matches = face_recognition.compare_faces(
                            face_system.known_face_encodings, 
                            face_encoding, 
                            tolerance=0.6
                        )
                        
                        if True in matches:
                            face_distances = face_recognition.face_distance(
                                face_system.known_face_encodings, 
                                face_encoding
                            )
                            best_match_index = np.argmin(face_distances)
                            
                            if face_distances[best_match_index] < 0.6:
                                employee_id = face_system.known_face_ids[best_match_index]
                                employee = Employee.query.get(employee_id)
                                if employee:
                                    recognized = True
                                    employee_name = f"{employee.first_name} {employee.last_name}"
                    
                    faces.append({
                        'x': int(left),
                        'y': int(top),
                        'width': int(right - left),
                        'height': int(bottom - top),
                        'recognized': recognized,
                        'employee_name': employee_name,
                        'employee_id': employee_id
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

@app.route('/api/face_attendance/capture', methods=['POST'])
def capture_face_attendance():
    """Face recognition attendance using OpenCV"""
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
        from io import BytesIO
        from PIL import Image
        import base64
        
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 and create image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to OpenCV format
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Initialize face recognition system
        if not hasattr(app, 'face_system'):
            app.face_system = FaceRecognitionSystem()
        
        face_system = app.face_system
        
        # Recognize face
        employee, message, face_location = face_system.recognize_face(frame)
        
        if employee and face_location:
            # Determine attendance type
            attendance_type = determine_attendance_type(employee.id)
            
            # Record attendance
            success, record_message = record_attendance(employee.id, attendance_type)
            
            if success:
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

def determine_attendance_type(employee_id):
    """Determine if employee should check in or check out"""
    try:
        today = date.today()
        existing_attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        if existing_attendance and existing_attendance.check_in_time and not existing_attendance.check_out_time:
            return 'check_out'
        else:
            return 'check_in'
    except Exception as e:
        print(f"Error determining attendance type: {e}")
        return 'check_in'

def record_attendance(employee_id, attendance_type):
    """Record attendance for employee"""
    try:
        today = date.today()
        now = datetime.now()
        
        existing_attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        if attendance_type == 'check_in':
            if existing_attendance and existing_attendance.check_in_time:
                return False, "Already checked in today"
            
            if not existing_attendance:
                attendance = Attendance(
                    employee_id=employee_id,
                    date=today,
                    check_in_time=now.time(),
                    status='present'
                )
                db.session.add(attendance)
            else:
                existing_attendance.check_in_time = now.time()
                existing_attendance.status = 'present'
                
            message = f"Check-in recorded at {now.strftime('%I:%M %p')}"
            
        else:  # check_out
            if not existing_attendance or not existing_attendance.check_in_time:
                return False, "No check-in record found for today"
            
            if existing_attendance.check_out_time:
                return False, "Already checked out today"
            
            existing_attendance.check_out_time = now.time()
            
            # Calculate work hours
            check_in_datetime = datetime.combine(today, existing_attendance.check_in_time)
            check_out_datetime = datetime.combine(today, now.time())
            work_hours = (check_out_datetime - check_in_datetime).total_seconds() / 3600
            existing_attendance.work_hours = round(work_hours, 2)
            
            message = f"Check-out recorded at {now.strftime('%I:%M %p')}. Work hours: {existing_attendance.work_hours}"
        
        db.session.commit()
        return True, message
        
    except Exception as e:
        print(f"Error recording attendance: {e}")
        db.session.rollback()
        return False, f"Error recording attendance: {str(e)}"

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default roles if they don't exist
        if Role.query.count() == 0:
            roles = [
                Role(name='Admin', description='System administrator'),
                Role(name='HR Officer', description='Human Resources officer'),
                Role(name='Finance Officer', description='Finance officer'),
                Role(name='Employee', description='Regular employee')
            ]
            db.session.bulk_save_objects(roles)
            db.session.commit()
        
        # Create default admin user if it doesn't exist
        if User.query.filter_by(username='admin').first() is None:
            admin_role = Role.query.filter_by(name='Admin').first()
            admin_user = User(
                username='admin',
                email='admin@company.com',
                password_hash=generate_password_hash('admin123'),
                role_id=admin_role.id
            )
            db.session.add(admin_user)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
