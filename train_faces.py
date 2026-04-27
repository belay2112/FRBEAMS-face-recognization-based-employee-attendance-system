#!/usr/bin/env python3
"""
FRBEAMS Face Training Script
Train the face recognition system with employee photos
"""

import cv2
import face_recognition
import numpy as np
import os
import pickle
from app import app, db, Employee
from dotenv import load_dotenv

load_dotenv()

class FaceTrainer:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_ids = []
        self.dataset_path = 'dataset'
        self.encodings_path = 'encodings/face_encodings.pkl'
        
        # Create directories
        os.makedirs(self.dataset_path, exist_ok=True)
        os.makedirs('encodings', exist_ok=True)
    
    def create_dataset(self, employee_id, num_images=20):
        """Create dataset for an employee by capturing images from webcam"""
        print(f"📸 Creating dataset for employee {employee_id}")
        
        # Create employee directory
        employee_dir = os.path.join(self.dataset_path, str(employee_id))
        os.makedirs(employee_dir, exist_ok=True)
        
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open webcam")
            return False
        
        # Load face detector
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        count = 0
        while count < num_images:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Draw rectangle around face and save
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                face_img = frame[y:y+h, x:x+w]
                
                # Save face image
                img_path = os.path.join(employee_dir, f'{count}.jpg')
                cv2.imwrite(img_path, face_img)
                count += 1
                print(f"✅ Captured image {count}/{num_images}")
            
            # Display the frame
            cv2.imshow('Face Training - Press ESC to cancel', frame)
            
            # Break on ESC key
            if cv2.waitKey(100) & 0xFF == 27:
                break
        
        cap.release()
        cv2.destroyAllWindows()
        print(f"✅ Dataset created for employee {employee_id}")
        return True
    
    def train_model(self):
        """Train the face recognition model from dataset"""
        print("🧠 Training face recognition model...")
        
        # Get all employee directories
        employee_dirs = [d for d in os.listdir(self.dataset_path) 
                      if os.path.isdir(os.path.join(self.dataset_path, d))]
        
        if not employee_dirs:
            print("❌ No dataset found. Run create_dataset first.")
            return False
        
        # Process each employee
        for employee_id in employee_dirs:
            employee_path = os.path.join(self.dataset_path, employee_id)
            image_files = [f for f in os.listdir(employee_path) 
                         if f.endswith(('.jpg', '.jpeg', '.png'))]
            
            if not image_files:
                continue
            
            print(f"📚 Processing employee {employee_id}...")
            
            # Process all images for this employee
            for image_file in image_files:
                image_path = os.path.join(employee_path, image_file)
                
                # Load image and find face locations
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                
                if face_locations:
                    # Get face encodings
                    face_encodings = face_recognition.face_encodings(image, face_locations)
                    
                    if face_encodings:
                        encoding = face_encodings[0]
                        self.known_face_encodings.append(encoding)
                        self.known_face_ids.append(int(employee_id))
        
        # Save encodings to file
        if self.known_face_encodings:
            data = {
                'encodings': self.known_face_encodings,
                'ids': self.known_face_ids
            }
            with open(self.encodings_path, 'wb') as f:
                pickle.dump(data, f)
            
            print(f"✅ Training complete! {len(self.known_face_encodings)} faces trained")
            return True
        else:
            print("❌ No faces found for training")
            return False
    
    def update_database_encodings(self):
        """Update face encodings in database"""
        print("💾 Updating database with face encodings...")
        
        # Load encodings
        if os.path.exists(self.encodings_path):
            with open(self.encodings_path, 'rb') as f:
                data = pickle.load(f)
                encodings = data['encodings']
                ids = data['ids']
        else:
            print("❌ No encodings found. Run training first.")
            return
        
        with app.app_context():
            # Update each employee's face encoding
            for i, employee_id in enumerate(ids):
                if i < len(encodings):
                    employee = Employee.query.get(employee_id)
                    if employee:
                        # Convert encoding to base64 for database storage
                        encoding_str = base64.b64encode(pickle.dumps(encodings[i])).decode('utf-8')
                        employee.face_encoding = encoding_str
                        db.session.commit()
                        print(f"✅ Updated face encoding for employee {employee_id}")
        
        print("✅ Database updated successfully!")

def main():
    print("🎯 FRBEAMS Face Training System")
    print("=" * 50)
    
    trainer = FaceTrainer()
    
    while True:
        print("\n📋 Menu:")
        print("1. Create dataset for employee")
        print("2. Train face recognition model")
        print("3. Update database with encodings")
        print("4. Exit")
        
        choice = input("Enter your choice (1-4): ")
        
        if choice == '1':
            employee_id = input("Enter employee ID: ")
            trainer.create_dataset(employee_id)
        
        elif choice == '2':
            trainer.train_model()
        
        elif choice == '3':
            trainer.update_database_encodings()
        
        elif choice == '4':
            print("👋 Exiting...")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == '__main__':
    import base64
    main()
