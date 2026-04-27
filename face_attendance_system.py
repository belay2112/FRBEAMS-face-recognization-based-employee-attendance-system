"""
Complete Face Recognition Attendance System for FRBEAMS
Captures face, checks against registered employees, records attendance
"""

import cv2
import face_recognition
import numpy as np
import pickle
import base64
import os
from datetime import datetime, date
from app import app, db, Employee, Attendance, User
from dotenv import load_dotenv

load_dotenv()

class FaceAttendanceSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        self.tolerance = 0.6
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known faces from database"""
        print("Loading face encodings from database...")
        
        try:
            with app.app_context():
                employees = Employee.query.filter(
                    Employee.is_active == True,
                    Employee.face_encoding.isnot(None)
                ).all()
                
                self.known_face_encodings = []
                self.known_face_ids = []
                self.known_face_names = []
                
                for employee in employees:
                    try:
                        # Decode face encoding from database
                        encoding = pickle.loads(base64.b64decode(employee.face_encoding))
                        self.known_face_encodings.append(encoding)
                        self.known_face_ids.append(employee.id)
                        self.known_face_names.append(f"{employee.first_name} {employee.last_name}")
                        print(f"Loaded face for {employee.first_name} {employee.last_name}")
                    except Exception as e:
                        print(f"Error loading face for {employee.first_name}: {e}")
                
                print(f"Loaded {len(self.known_face_encodings)} face encodings")
                
        except Exception as e:
            print(f"Error loading faces: {e}")
    
    def capture_and_recognize(self, camera_index=0):
        """Capture from camera and recognize face"""
        print("Starting face recognition attendance system...")
        
        # Initialize webcam
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return False, "Cannot open camera", None, None
        
        print("Camera opened successfully")
        print("Press 'c' to capture attendance, 'q' to quit")
        
        employee_found = None
        face_location = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert BGR to RGB for face recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find all face locations and encodings
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            # Process each face found
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding, 
                    tolerance=self.tolerance
                )
                
                name = "Unknown"
                employee_id = None
                
                if len(self.known_face_encodings) > 0:
                    # Use the known face with the smallest distance to the new face
                    face_distances = face_recognition.face_distance(
                        self.known_face_encodings, 
                        face_encoding
                    )
                    
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        employee_id = self.known_face_ids[best_match_index]
                        employee_found = employee_id
                        face_location = (top, right, bottom, left)
                
                # Draw a box around the face
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                # Draw a label with a name below the face
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
                
                # Show confidence score
                if name != "Unknown" and len(self.known_face_encodings) > 0:
                    confidence = (1 - face_distances[best_match_index]) * 100
                    cv2.putText(frame, f"{confidence:.1f}%", (left + 6, bottom - 26), 
                               font, 0.5, (255, 255, 255), 1)
            
            # Display instructions
            cv2.putText(frame, "Press 'c' to capture attendance, 'q' to quit", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show the frame
            cv2.imshow('Face Recognition Attendance', frame)
            
            # Check for key presses
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("Quitting...")
                break
            elif key == ord('c'):
                if employee_found:
                    print(f"Face recognized: {name}")
                    cap.release()
                    cv2.destroyAllWindows()
                    return True, f"Face recognized: {name}", employee_found, face_location
                else:
                    print("No matching face found!")
                    # Show warning message on screen
                    cv2.putText(frame, "No matching face found!", 
                               (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                    cv2.imshow('Face Recognition Attendance', frame)
                    cv2.waitKey(2000)  # Show message for 2 seconds
        
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        return False, "No face captured", None, None
    
    def record_attendance(self, employee_id, attendance_type='check_in'):
        """Record attendance for recognized employee"""
        try:
            with app.app_context():
                employee = Employee.query.get(employee_id)
                if not employee:
                    return False, "Employee not found"
                
                today = date.today()
                
                # Check if employee already has attendance record for today
                existing_attendance = Attendance.query.filter_by(
                    employee_id=employee_id,
                    date=today
                ).first()
                
                if existing_attendance:
                    if attendance_type == 'check_in' and existing_attendance.check_in_time:
                        return False, f"{employee.first_name} already checked in today at {existing_attendance.check_in_time.strftime('%H:%M')}"
                    elif attendance_type == 'check_out' and existing_attendance.check_out_time:
                        return False, f"{employee.first_name} already checked out today at {existing_attendance.check_out_time.strftime('%H:%M')}"
                
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
            return False, f"Error recording attendance: {str(e)}"
    
    def determine_attendance_type(self, employee_id):
        """Determine if employee should check in or check out"""
        try:
            with app.app_context():
                today = date.today()
                existing_attendance = Attendance.query.filter_by(
                    employee_id=employee_id,
                    date=today
                ).first()
                
                if existing_attendance and existing_attendance.check_in_time:
                    if existing_attendance.check_out_time:
                        return 'check_in'  # Already checked out, new check-in
                    else:
                        return 'check_out'  # Checked in but not out, check-out
                else:
                    return 'check_in'  # No record today, check-in
                    
        except Exception as e:
            return 'check_in'  # Default to check-in
    
    def run_attendance_system(self):
        """Run the complete face recognition attendance system"""
        if len(self.known_face_encodings) == 0:
            print("No registered faces found. Please register employee faces first.")
            return False, "No registered faces"
        
        success, message, employee_id, face_location = self.capture_and_recognize()
        
        if success and employee_id:
            attendance_type = self.determine_attendance_type(employee_id)
            record_success, record_message = self.record_attendance(employee_id, attendance_type)
            
            if record_success:
                return True, record_message
            else:
                return False, record_message
        else:
            return False, message

# Flask API endpoints for face recognition
def setup_face_recognition_endpoints(app):
    
    @app.route('/api/face_attendance/capture', methods=['POST'])
    def capture_face_attendance():
        """API endpoint for face recognition attendance"""
        try:
            face_system = FaceAttendanceSystem()
            success, message, employee_id, _ = face_system.capture_and_recognize()
            
            if success and employee_id:
                attendance_type = face_system.determine_attendance_type(employee_id)
                record_success, record_message = face_system.record_attendance(employee_id, attendance_type)
                
                if record_success:
                    with app.app_context():
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
                'error': str(e)
            }), 500
    
    @app.route('/api/face_attendance/status', methods=['GET'])
    def get_face_attendance_status():
        """Get face recognition system status"""
        try:
            face_system = FaceAttendanceSystem()
            with app.app_context():
                employees_with_faces = Employee.query.filter(
                    Employee.is_active == True,
                    Employee.face_encoding.isnot(None)
                ).count()
                
            return jsonify({
                'success': True,
                'status': 'active' if len(face_system.known_face_encodings) > 0 else 'inactive',
                'registered_faces': len(face_system.known_face_encodings),
                'employees_with_faces': employees_with_faces
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

# Initialize face recognition endpoints
if __name__ != '__main__':
    setup_face_recognition_endpoints(app)
