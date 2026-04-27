# FRBEAMS - Facial Recognition Based Employee Attendance Management System

A comprehensive web-based attendance management system that uses facial recognition technology to automate employee attendance tracking.

## Features
DB:-  http://localhost/phpmyadmin
Web:-  http://localhost:5000

### Core Features
- **Facial Recognition**: Real-time face detection and recognition using OpenCV and face_recognition library
- **Role-Based Access Control**: Admin, HR Officer, Finance Officer, and Employee roles
- **Automated Attendance**: Check-in/check-out with face recognition
- **Employee Management**: Add, update, and manage employee profiles
- **Real-time Dashboard**: Live attendance statistics and monitoring
- **Comprehensive Reports**: Daily, weekly, and monthly attendance reports
- **Secure System**: Password encryption, role-based permissions, and data security

### Technical Features
- **Backend**: Python Flask with SQLAlchemy ORM
- **Frontend**: Responsive HTML5, CSS3, JavaScript with Bootstrap 5
- **Database**: MySQL with optimized queries and stored procedures
- **AI/ML**: OpenCV for face detection, face_recognition library for recognition
- **Security**: JWT authentication, bcrypt password hashing, CORS protection
- **Performance**: Optimized database queries, efficient face encoding storage

## System Requirements

### Software Requirements
- Python 3.8+
- MySQL 5.7+ or MySQL 8.0+
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Webcam access for face recognition

### Hardware Requirements
- Minimum 4GB RAM
- 2GHz+ processor
- Webcam or camera device
- 10GB+ free disk space

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd FRBEAMS
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up Database
```bash
# Create MySQL database
mysql -u root -p
CREATE DATABASE frbeams;

# Import database schema
mysql -u root -p frbeams < database_setup.sql
```

### 4. Configure Environment Variables
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
# DATABASE_URL=mysql+pymysql://username:password@localhost/frbeams
# SECRET_KEY=your-secret-key-here
```

### 5. Initialize the Application
```bash
# Initialize database and create default admin user
python app.py
```

### 6. Run the Application
```bash
# Development server
python app.py

# Production server
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Usage

### Default Login Credentials
- **Admin**: username: `admin`, password: `admin123`
- **HR**: username: `hr`, password: `hr123`
- **Finance**: username: `finance`, password: `finance123`

### Getting Started

1. **Admin Setup**:
   - Log in as admin
   - Add employees through the dashboard
   - Register employee faces using the camera
   - Configure system settings

2. **Employee Registration**:
   - Add new employee details
   - Capture and register face images
   - Assign appropriate roles and permissions

3. **Daily Attendance**:
   - Employees use facial recognition to mark attendance
   - System automatically records check-in/check-out times
   - Real-time monitoring of attendance status

4. **Report Generation**:
   - Generate daily, weekly, monthly reports
   - Export reports to Excel/PDF
   - Analyze attendance patterns and trends

## API Endpoints

### Authentication
- `POST /login` - User login
- `GET /logout` - User logout

### Employee Management
- `GET /api/employees` - List all employees
- `POST /api/employees` - Add new employee
- `POST /api/employees/<id>/face` - Upload face image

### Attendance
- `POST /api/attendance/mark` - Mark attendance with face recognition
- `GET /api/attendance` - Get attendance records
- `GET /api/attendance?date=YYYY-MM-DD` - Get attendance for specific date

### Reports
- `GET /api/reports/daily` - Daily attendance report
- `GET /api/reports/weekly` - Weekly attendance report
- `GET /api/reports/monthly` - Monthly attendance report

## Database Schema

### Tables
- **roles**: User roles and permissions
- **users**: User accounts and authentication
- **employees**: Employee profiles and information
- **attendance**: Attendance records and timestamps

### Key Relationships
- Users belong to roles (many-to-one)
- Employees have user accounts (one-to-one)
- Attendance records belong to employees (many-to-one)

## Face Recognition Process

1. **Face Detection**: OpenCV detects faces in camera feed
2. **Feature Extraction**: Extract 128-dimensional face encodings
3. **Face Matching**: Compare with stored encodings using Euclidean distance
4. **Threshold Matching**: Use configurable tolerance (default: 0.6)
5. **Attendance Logging**: Record attendance upon successful recognition

## Security Features

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- Password hashing with bcrypt
- Session management

### Data Protection
- Encrypted password storage
- Secure face encoding storage
- CORS protection
- SQL injection prevention

### System Security
- Input validation and sanitization
- Rate limiting on API endpoints
- Secure file upload handling
- Environment variable configuration

## Performance Optimization

### Database Optimization
- Indexed columns for fast queries
- Stored procedures for complex operations
- Connection pooling
- Query optimization

### Face Recognition Optimization
- Efficient face encoding storage
- Cached face recognition models
- Optimized image processing
- Parallel processing capabilities

## Troubleshooting

### Common Issues

1. **Camera Access Denied**:
   - Ensure browser has camera permissions
   - Check if camera is not being used by another application
   - Verify camera drivers are installed

2. **Face Recognition Not Working**:
   - Ensure proper lighting conditions
   - Check face image quality and resolution
   - Verify face encodings are properly stored
   - Adjust recognition tolerance in config

3. **Database Connection Issues**:
   - Verify MySQL service is running
   - Check database credentials in .env file
   - Ensure database exists and is accessible

4. **Performance Issues**:
   - Optimize database queries
   - Increase server resources
   - Check network connectivity
   - Monitor system resources

### Logs and Debugging
- Application logs: Check console output
- Database logs: MySQL error logs
- Browser logs: Developer console
- Face recognition logs: Recognition confidence scores

## Development

### Project Structure
```
FRBEAMS/
|-- app.py                 # Main Flask application
|-- config.py             # Configuration settings
|-- requirements.txt      # Python dependencies
|-- database_setup.sql   # Database schema
|-- templates/           # HTML templates
|-- uploads/             # File uploads directory
|-- static/              # Static assets (CSS, JS, images)
|-- tests/               # Unit tests
|-- docs/                # Documentation
```

### Adding New Features
1. Update database schema if needed
2. Add new API endpoints in app.py
3. Create/update frontend templates
4. Add appropriate tests
5. Update documentation

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=app tests/
```

## Deployment

### Production Deployment
1. Set up production database
2. Configure environment variables
3. Use production web server (Gunicorn/uWSGI)
4. Set up reverse proxy (Nginx)
5. Configure SSL/TLS
6. Set up monitoring and logging

### Docker Deployment
```bash
# Build Docker image
docker build -t frbeams .

# Run container
docker run -p 5000:5000 frbeams
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes and test
4. Submit pull request
5. Follow code style guidelines

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check documentation and FAQs

## Changelog

### Version 1.0.0
- Initial release
- Basic face recognition attendance system
- User management and role-based access
- Dashboard and reporting features
- Database integration
- Security implementation

---

**Note**: This system requires proper hardware setup and configuration for optimal face recognition performance. Ensure adequate lighting and camera quality for best results.
