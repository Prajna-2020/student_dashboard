# 🎓 Student Dashboard

A **role-based student portal system** built using Django, designed to manage academic processes such as user access, course enrollment, marks & attendance upload, profile management, and student communication through announcements. This project simulates the core needs of an academic institution in a structured, scalable, and intuitive platform.

---

## 📂 Project Structure

```
student_dashboard/
│
├── web/
│   ├── media/                      # Uploaded files
│   ├── static/                     # Static files (CSS, JS, images)
│   ├── template/                   # All HTML templates
│   │   ├── accounts/               # Templates related to login, password reset
│   │   ├── admin/                  # Admin dashboard templates
│   │   ├── faculty/                # Faculty dashboard templates
│   │   ├── student/                # Student dashboard templates
│   │   ├── forgot_password.html
│   │   ├── login.html
│   │   ├── password_reset_form.html
│   │   ├── profile_update.html
│   │   ├── reset_password.html
│   │   ├── faculty_template.csv    # CSV for bulk faculty upload
│   │   ├── student_template.csv    # CSV for bulk student upload
│   │   └── user_template.csv       # CSV for unmapped user downloads
│   │
│   ├── webapp/                     # Core app (models, views, etc.)
│   ├── ec.txt                      # Supporting file (if used)
│   ├── manage.py                   # Django management script
│   ├── readme.txt                  # Project documentation draft
│   ├── student_results.txt         # Student result output or logs
│   └── urls.txt                    # URL routing details
```

---

## 🚀 Features

* 🔒 **Secure Authentication**: Login, forgot password, reset password with email link flow.
* 📂 **CSV Management**: Bulk user upload (students/faculty), downloadable templates.
* 👥 **Role-Based Dashboards**: Custom views for admin, faculty, and student.
* 📝 **Marks & Attendance**: Upload via CSV by faculty; visible to students.
* 📣 **Announcements**: Faculty can publish notices viewable by students.
* 📊 **Student Dashboard**: Performance summaries, attendance status, profile access.

---

## 🛠️ Tech Stack

* **Backend**: Django (Python)
* **Frontend**: HTML, CSS, JavaScript
* **Database**: SQLite / MariaDB
* **Tools**: Figma (design), Git, Django Admin

---

## 🔧 Setup Instructions

1. Clone the repository:

   ```bash
   git clone https://github.com/Prajna-2020/student_dashboard.git
   cd student_dashboard/web
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv env
   source env/bin/activate  # For Windows: env\Scripts\activate
   ```

3. Run migrations and create superuser:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. Start the server:

   ```bash
   python manage.py runserver
   ```

---

## 📌 Future Scope

* Add **classroom-style features**: upload lecture notes, assign and review assignments/projects.
* Support lab/internal/coursework result uploads.
* Integrate **notifications** (email/SMS).
* Student performance analytics using graphs/charts.

---

## 📄 License

This project is intended for educational use only. Feel free to explore, modify, and extend it.

