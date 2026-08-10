# SNAP CLASS – AI Attendance System

An AI-powered attendance management system that automates student attendance using **face recognition and voice recognition**, reducing manual effort and improving accuracy.

## Overview

**SNAP CLASS** is an intelligent attendance management application designed for educational institutions. Teachers can create and manage classes, enroll students, and automatically record attendance using AI-based recognition.

The system uses a **group photograph** to identify enrolled students and mark their attendance automatically. It also provides authentication, attendance tracking, and a user-friendly dashboard for teachers and students.

## Key Features

* **AI Face Recognition** – Automatically identifies students from classroom/group photographs.
* **Voice Recognition** – Supports voice-based student identification.
* **Automated Attendance** – Marks attendance without manual roll calls.
* **Teacher & Student Authentication** – Secure login-based access.
* **Subject Management** – Teachers can manage subjects and enrolled students.
* **Attendance Dashboard** – View and track attendance records.
* **Database Integration** – Stores student, subject, and attendance information.
* **Responsive Interface** – Designed for convenient use across devices.
* **AI-Based Automation** – Reduces repetitive manual attendance work.

## AI & Technical Concepts

The project integrates several AI and software engineering concepts:

* Face Recognition
* Voice/Speaker Recognition
* Computer Vision
* Feature Extraction
* Machine Learning
* Image Processing
* Authentication & Authorization
* Database Management
* Web Application Development

## Tech Stack

| Category             | Technologies                        |
| -------------------- | ----------------------------------- |
| Programming Language | Python                              |
| Frontend             | Streamlit, HTML, CSS                |
| Backend              | Flask                               |
| AI / ML              | Face Recognition, Voice Recognition |
| Database             | SQL / Connected Database            |
| Libraries            | NumPy, Pandas, OpenCV               |
| Deployment           | Vercel / Streamlit                  |
| Development          | VS Code, Git, GitHub                |

## How It Works

```text
Teacher Login
     ↓
Create / Select Subject
     ↓
Enroll Students
     ↓
Upload Classroom / Group Photo
     ↓
Face Detection & Recognition
     ↓
Match With Registered Students
     ↓
Attendance Automatically Marked
     ↓
Store Attendance in Database
     ↓
View Attendance Dashboard
```

## Project Structure

```text
SNAP-CLASS/
│
├── app.py
├── requirements.txt
├── README.md
│
├── pages/
│   ├── teacher.py
│   └── student.py
│
├── models/
│   └── ...
│
├── database/
│   └── ...
│
├── assets/
│   └── ...
│
└── utils/
    └── ...
```

> The exact structure may vary depending on the final project implementation.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd SNAP-CLASS
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

If the main application uses Streamlit:

```bash
streamlit run app.py
```

##  Environment Variables

If the project uses API keys or other credentials, create a `.env` file:

```text
API_KEY=your_api_key
DATABASE_URL=your_database_url
```

**Do not upload `.env` or private API keys to GitHub.**

Add the following to `.gitignore`:

```text
.env
venv/
__pycache__/
*.pyc
```

## Use Cases

SNAP CLASS can be used in:

* Colleges and universities
* Schools
* Training institutes
* Coaching centers
* Workshops and classrooms
* Automated classroom management systems

## Future Improvements

* Real-time attendance using classroom cameras
* Liveness detection to prevent photo-based spoofing
* Advanced voice authentication
* Attendance analytics and visualization
* Automated attendance reports
* Email notifications for low attendance
* Cloud-based student and attendance management
* Mobile application integration

## Author

**Rati Kumari Akela**

Computer Science Engineering Student
Interested in **Artificial Intelligence, Machine Learning and Software Development**

