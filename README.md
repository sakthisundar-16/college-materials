<<<<<<< HEAD
# College Academic Materials Management System

## Description
A comprehensive web-based application designed to streamline the management and sharing of academic materials in a college environment. Built using Python Flask and MySQL, this system enables efficient organization, upload, and retrieval of educational resources categorized by Department, Semester, and Subject. It provides a secure platform for students to access learning materials while allowing faculty and administrators to maintain and update content.

## Features
- **User Authentication & Roles**: Supports three user types - Admin, Faculty, and Student with role-based access control
- **Material Management**: Upload, organize, and download academic materials (PDF, DOCX, PPTX, etc.) by department/semester/subject hierarchy
- **Events Management**: Create and display college events with department-specific organization
- **Achievements Tracking**: Showcase department achievements with images and descriptions
- **Q&A System**: Encrypted messaging system for students to ask questions about materials and faculty to respond
- **Dashboards**: Role-specific dashboards for admins, faculty, and students
- **File Security**: Secure file handling with size limits and type validation
- **Responsive Design**: Modern, user-friendly interface with intuitive navigation

## Technology Stack
=======
College Academic Materials Management System (CAMPUS CONNECT - NSCET)
Description
A comprehensive web-based application designed to streamline the management and sharing of academic materials in a college environment. Built using Python Flask and MySQL, this system enables efficient organization, upload, and retrieval of educational resources categorized by Department, Semester, and Subject. It provides a secure platform for students to access learning materials while allowing faculty and administrators to maintain and update content.
**Features**:

  **User Authentication & Roles**: Supports three user types - Admin, Faculty, and Student with role-based access control
  **Material Management**: Upload, organize, and download academic materials (PDF, DOCX, PPTX, etc.) by department/semester/subject hierarchy
  **Events Management**: Create and display college events with department-specific organization
  **Achievements Tracking**: Showcase department achievements with images and descriptions
  **Q&A System**: Encrypted messaging system for students to ask questions about materials and faculty to respond
  **Dashboards**: Role-specific dashboards for admins, faculty, and students
  **File Security**: Secure file handling with size limits and type validation
  **Responsive Design**: Modern, user-friendly interface with intuitive navigation
 
  **Technology Stack**:
>>>>>>> 693186998fea459f0f77cdfb021a86d9e44855fd
- **Backend**: Python Flask
- **Database**: MySQL
- **Frontend**: HTML5, CSS3, Jinja2 Templates
- **Authentication**: Flask-Login, Werkzeug Security
- **Encryption**: Cryptography library for secure messaging
- **CORS Support**: Flask-CORS for cross-origin requests
- **File Handling**: Werkzeug for secure file uploads
<<<<<<< HEAD

## Prerequisites
- Python 3.7 or higher
- MySQL Server (version 5.7+ recommended)
- pip package manager
- Web browser for accessing the application

## Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd college-blog
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Configuration**
   - Ensure MySQL server is running on localhost
   - Default configuration uses:
     - Host: localhost
     - User: root
     - Password: 2005
     - Database: college_db
   - Update `database_config.py` if your MySQL credentials differ

## Database Setup
The application automatically:
- Creates the `college_db` database if it doesn't exist
- Sets up all required tables (users, departments, semesters, subjects, materials, events, achievements, messages)
- Populates initial data for departments and their curriculum structure
- Creates sample users for testing

## Running the Application

1. **Start the Flask Server**
   ```bash
   python college_app.py
   ```

2. **Access the Application**
   - Open your web browser
   - Navigate to: `http://localhost:5000`
   - Register a new account or use sample login credentials

## Usage

### For Students
- Browse materials by department → semester → subject
- Download academic resources
- Ask questions about specific materials
- View recent uploads and events
- Access GPA/CGPA calculator

### For Faculty
- Upload materials to specific subjects
- View and respond to student questions
- Manage their uploaded materials
- Access faculty-specific dashboard

### For Administrators
- Manage users (add/edit/delete students and faculty)
- Upload materials across all departments
- Create and manage events
- Add department achievements
- Access comprehensive admin dashboard

## Sample Users
The system creates sample users on first run:
- **Admin**: admin@college.local / adminpass
- **Faculty**: faculty@college.local / facultypass
- **Student**: student@college.local / studentpass

## Project Structure
```
college-blog/
├── college_app.py              # Main Flask application
├── database_config.py          # Database configuration
├── requirements.txt            # Python dependencies
├── static/                     # CSS and static files
│   ├── custom.css
│   └── design.css
├── templates/                  # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── admin_dashboard.html
│   ├── faculty_dashboard.html
│   ├── student_dashboard.html
│   └── ... (other templates)
├── uploads/                    # Uploaded files directory
└── README.md                   # This file
```

## API Endpoints
The application provides RESTful API endpoints for:
- Department, semester, and subject management
- Material upload/download
- User management
- Events and achievements

## Security Features
- Password hashing using Werkzeug
- Role-based access control
- File type and size validation
- Encrypted messaging for Q&A system
- Secure file storage

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Future Enhancements
- Email notifications for new materials and responses
- Advanced search and filtering capabilities
- Mobile application development
- Integration with learning management systems
- Analytics and reporting features

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Support
For support or questions, please open an issue in the repository or contact the development team.

---
**Note**: This system is designed for educational purposes and should be deployed with appropriate security measures in production environments.
=======
>>>>>>> 693186998fea459f0f77cdfb021a86d9e44855fd
