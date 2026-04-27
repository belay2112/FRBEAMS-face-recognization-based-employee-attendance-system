# FRBEAMS - Face Recognition Based Employee Attendance Management System

A modern web application for managing employee attendance using facial recognition technology, designed specifically for educational institutions.

## 🚀 Features

- **Real-time Face Detection** - Live camera feed with colored recognition boxes
- **Facial Recognition** - Automatic employee identification
- **Attendance Tracking** - Check-in/check-out with time stamps
- **Management Dashboard** - Comprehensive admin interface
- **Multi-role System** - Admin, HR, Finance, Employee access levels
- **Modern UI** - Responsive design with Bootstrap 5

## 🛠️ Technology Stack

- **Backend**: Python Flask, MySQL
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Face Recognition**: OpenCV, face_recognition library
- **Database**: MySQL with SQLAlchemy ORM

## 📋 Prerequisites

- Python 3.8+
- MySQL 5.7+
- OpenCV
- face_recognition library

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/belay2112/FRBEAMS-face-recognization-based-employee-attendance-system.git
   cd FRBEAMS-face-recognization-based-employee-attendance-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database setup**
   ```bash
   mysql -u root -p < database_setup.sql
   ```

4. **Run the application**
   ```bash
   python3 app_working.py
   ```

5. **Access the application**
   - Open browser: http://localhost:5000
   - Default login: admin / admin123

## 👥 User Roles

- **Admin**: Full system access and user management
- **HR Officer**: Employee management and attendance reports
- **Finance Officer**: Salary and financial reports
- **Employee**: Mark attendance and view personal records

## 📸 How to Use

1. **Login** with your credentials
2. **Click "Mark Attendance"** to open face recognition
3. **Allow camera access** when prompted
4. **Face detection** shows colored boxes:
   - 🟢 Green = Recognized employee
   - 🔴 Red = Unknown person
5. **Click "Capture Attendance"** to register

## 🏗️ Project Structure

```
FRBEAMS/
├── app_working.py          # Main Flask application
├── database_setup.sql      # Database schema
├── requirements.txt        # Python dependencies
├── templates/             # HTML templates
│   ├── index_modern.html  # Main page with face recognition
│   └── dashboard*.html    # Dashboard pages
├── static/               # CSS, JS, images
└── uploads/              # Face images and encodings
```

## 🔧 Configuration

- Database connection in `.env` file
- Face recognition tolerance: 0.6
- Detection interval: 500ms
- Supported image formats: JPEG, PNG

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License.

## 👨‍💻 Author

**Belay Mengie**  
Jinka University  
Full-stack Developer specializing in facial recognition systems

## 📞 Contact

- **Email**: frbeams@jinkauniversity.edu.et
- **Phone**: +251 900 900 900
- **GitHub**: https://github.com/belay2112/FRBEAMS-face-recognization-based-employee-attendance-system

---

⭐ **Star this repository if you find it helpful!**
