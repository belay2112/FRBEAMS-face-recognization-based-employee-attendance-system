"""
Complete Face Recognition Integration for FRBEAMS
"""

import cv2
import face_recognition
import numpy as np
import pickle
import base64
import os
from app import Employee

class FaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        self.tolerance = 0.6
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known faces from database"""
        print("📚 Loading face encodings from database...")
        
        try:
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
                    print(f"✅ Loaded face for {employee.first_name} {employee.last_name}")
                except Exception as e:
                    print(f"❌ Error loading face for {employee.first_name}: {e}")
            
            print(f"🎯 Loaded {len(self.known_face_encodings)} face encodings")
            
        except Exception as e:
            print(f"❌ Error loading faces: {e}")
    
    def recognize_face(self, frame):
        """Recognize face in given frame"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find all face locations and encodings
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            if not face_locations:
                return None, "No face detected", None
            
            # Loop through each face found
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding, 
                    tolerance=self.tolerance
                )
                
                name = "Unknown"
                employee_id = None
                
                # Use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(
                    self.known_face_encodings, 
                    face_encoding
                )
                
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        employee_id = self.known_face_ids[best_match_index]
                
                # Draw a box around the face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Draw a label with a name below the face
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
                
                if employee_id:
                    return employee_id, f"Face recognized: {name}", (top, right, bottom, left)
            
            return None, "No matching face found", None
            
        except Exception as e:
            return None, f"Error in face recognition: {str(e)}", None
    
    def get_employee_by_id(self, employee_id):
        """Get employee object by ID"""
        try:
            return Employee.query.get(employee_id)
        except:
            return None
    
    def add_face_encoding(self, employee_id, image_path):
        """Add face encoding for an employee"""
        try:
            # Load image and find face
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return False, "No face detected in image"
            
            # Get face encoding
            face_encodings = face_recognition.face_encodings(image, face_locations)
            if not face_encodings:
                return False, "Could not extract face encoding"
            
            encoding = face_encodings[0]
            
            # Save to database
            employee = Employee.query.get(employee_id)
            if employee:
                encoding_str = base64.b64encode(pickle.dumps(encoding)).decode('utf-8')
                employee.face_encoding = encoding_str
                db.session.commit()
                
                # Reload known faces
                self.load_known_faces()
                
                return True, "Face encoding added successfully"
            
            return False, "Employee not found"
            
        except Exception as e:
            return False, f"Error adding face encoding: {str(e)}"

# Global face recognition system instance
face_system = FaceRecognitionSystem()
