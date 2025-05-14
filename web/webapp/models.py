from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

# Department Model
class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length=255)

    def __str__(self):
        return self.department_name

# Course Model
class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    course_name = models.CharField(max_length=255)
    course_code = models.CharField(max_length=10, default='')
    department = models.ManyToManyField(Department)
    credits = models.IntegerField()
    semester = models.IntegerField(
        choices=[(1, 'Semester 1'), (2, 'Semester 2'), 
                 (3, 'Semester 3'), (4, 'Semester 4'),
                 (5, 'Semester 5'), (6, 'Semester 6'),
                 (7, 'Semester 7'), (8, 'Semester 8')],
        help_text="Which semester this course belongs to"
    )
    internal_count = models.IntegerField(default=3)  
    assignment_count = models.IntegerField(default=2)  
    quiz_count = models.IntegerField(default=0)
    project_count = models.IntegerField(default=0)

    # Total marks allocation (sum should be 100 for internal components)
    internal_total_marks = models.IntegerField(default=60)
    assignment_total_marks = models.IntegerField(default=20)
    quiz_total_marks = models.IntegerField(default=20)
    project_total_marks = models.IntegerField(default=0)  # Optional if projects exist

    def __str__(self):
        return self.course_name

    def clean(self):
        # Validate that internal components sum to 100 marks
        internal_sum = (
            self.internal_total_marks +
            self.assignment_total_marks +
            self.quiz_total_marks +
            self.project_total_marks
        )
        if internal_sum != 100:
            raise ValidationError("Internal components must sum to 100 marks")

# Scheme Model
class Scheme(models.Model):
    scheme_id = models.AutoField(primary_key=True)
    scheme_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.scheme_name

# CourseScheme Model
class CourseScheme(models.Model):
    course_scheme_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    
    # Weightage distribution (should sum to 100)
    internal_weightage = models.FloatField(default=50)
    external_weightage = models.FloatField(default=50)
    
    scheme_year = models.IntegerField()

    class Meta:
        unique_together = ('course', 'scheme', 'scheme_year')

    def __str__(self):
        return f"{self.course} - {self.scheme} ({self.scheme_year})"

    def clean(self):
        if self.internal_weightage + self.external_weightage != 100:
            raise ValidationError("Internal and external weightage must sum to 100")

class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Personal Details
    first_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)
    usn = models.CharField(max_length=10, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, 
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], 
        null=True, 
        blank=True
    )
    nationality = models.CharField(max_length=50, null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    # Address Details
    address = models.TextField(null=True, blank=True)
    # Guardian Details
    guardian_name = models.CharField(max_length=50, null=True, blank=True)
    guardian_contact = models.CharField(max_length=15, null=True, blank=True)
    guardian_address = models.TextField(null=True, blank=True)
    # parent details
    mother_name = models.CharField(max_length=50, null=True, blank=True)
    father_name = models.CharField(max_length=50, null=True, blank=True)
    father_contact = models.CharField(max_length=15, null=True, blank=True) 
    mother_contact = models.CharField(max_length=15, null=True, blank=True)
    parent_address = models.TextField(null=True, blank=True)
                                               
    # Academic Details
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    current_semester = models.IntegerField()
    enrollment_date = models.DateField(auto_now_add=True)
    admission_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    scheme = models.ForeignKey(Scheme, on_delete=models.SET_NULL, null=True)
    
    # Additional Information
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)
    
    def __str__(self):
        return self.user.username

class Faculty(models.Model):
    faculty_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=30, default='')             
    last_name = models.CharField(max_length=30, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, 
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], 
        null=True, 
        blank=True
    )
    nationality = models.CharField(max_length=50, null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    employee_position = models.CharField(
        max_length=50, 
        choices=[('Hod', 'Hod'), ('Associate Professor', 'Associate Professor'), ('Assistant Professor', 'Assistant Professor')],
        null=True, 
        blank=True)

    # emergency contact
    emergency_contact = models.CharField(max_length=15, null=True, blank=True)
    emergency_name = models.CharField(max_length=50, null=True, blank=True)
    emergency_relation = models.CharField(max_length=20, null=True, blank=True)

    # Store Faculty profile pictures in 'media/faculty_profiles/'
    profile_picture = models.ImageField(upload_to='faculty_profiles/', null=True, blank=True)

    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.user.username

# Enrollment Model (Student-Course Mapping)
class Enrollment(models.Model):
    enrollment_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    faculty=models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True)
    semester = models.IntegerField()
    enrollment_date = models.DateField(auto_now_add=True)
    scheme = models.ForeignKey(Scheme, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('student', 'course', 'semester')

    def __str__(self):
        return f"{self.student} in {self.course} (Sem {self.semester})"

# Attendance Model
class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[('Present', 'Present'), ('Absent', 'Absent')])

    class Meta:
        unique_together = ('student', 'course', 'date')

    def __str__(self):
        return f"{self.student.user.username} - {self.course.course_name} - {self.date}"

# Regular Courses
# InternalMarks Model 
class InternalMarks(models.Model):
    internal_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    internal_number = models.IntegerField()
    marks = models.FloatField()
    max_marks = models.FloatField(null=True, blank=True)
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course', 'scheme', 'internal_number')

    def save(self, *args, **kwargs):
        if not self.max_marks:
            # Auto-calculate max marks based on course totals
            self.max_marks = self.course.internal_total_marks / self.course.internal_count
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.course} - Internal {self.internal_number}"

    def clean(self):
        if self.marks > self.max_marks:
            raise ValidationError(f"Marks cannot exceed maximum marks ({self.max_marks})")

# Assignments Model with auto-calculation
class Assignments(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    assignment_number = models.IntegerField()
    marks = models.FloatField()
    max_marks = models.FloatField(null=True, blank=True)
    submission_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'course', 'scheme', 'assignment_number')

    def save(self, *args, **kwargs):
        if not self.max_marks:
            # Auto-calculate max marks based on course totals
            self.max_marks = self.course.assignment_total_marks / self.course.assignment_count
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.course} - Assignment {self.assignment_number}"

    def clean(self):
        if self.marks > self.max_marks:
            raise ValidationError(f"Marks cannot exceed maximum marks ({self.max_marks})")

# Quizzes Model with auto-calculation
class Quizzes(models.Model):
    quiz_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    quiz_number = models.IntegerField()
    marks = models.FloatField()
    max_marks = models.FloatField(null=True, blank=True)
    date = models.DateField()

    class Meta:
        unique_together = ('student', 'course', 'scheme', 'quiz_number')

    def save(self, *args, **kwargs):
        if not self.max_marks:
            # Auto-calculate max marks based on course totals
            self.max_marks = self.course.quiz_total_marks / (self.course.quiz_count or 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.course} - Quiz {self.quiz_number}"

    def clean(self):
        if self.marks > self.max_marks:
            raise ValidationError(f"Marks cannot exceed maximum marks ({self.max_marks})")

# Projects Model
class Regular_Projects(models.Model):
    project_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    marks = models.FloatField()
    max_marks = models.FloatField(default=100)
    submission_date = models.DateField()
    comments = models.TextField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.course} - Project"

    def clean(self):
        if self.marks > self.max_marks:
            raise ValidationError(f"Marks cannot exceed maximum marks ({self.max_marks})")

# ExternalMarks Model
class ExternalMarks(models.Model):
    external_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)
    semester = models.IntegerField()
    marks = models.FloatField()
    max_marks = models.FloatField(default=100)
    date = models.DateField()
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'course', 'scheme', 'semester')

    def __str__(self):
        return f"{self.student} - {self.course} - External"

    def clean(self):
        if self.marks > self.max_marks:
            raise ValidationError(f"Marks cannot exceed maximum marks ({self.max_marks})")

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.course.course_name}"
    
# Event Calender
class Event(models.Model):
    event_id = models.AutoField(primary_key=True)
    EVENT_TYPES = [
        ('academic', 'Academic'),
        ('cultural', 'Cultural'),
        ('sports', 'Sports'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='other')
    location = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date']

    def _str_(self):
        return f"{self.title} ({self.start_date.strftime('%Y-%m-%d')})"
    
# marks calculation
class CourseResult(models.Model):
    """Model to store course results for each student"""
    result_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.IntegerField()
    credits = models.IntegerField(default=0)
    
    # Marks and grades
    internal_marks = models.FloatField(default=0)
    external_marks = models.FloatField(default=0)
    total_marks = models.FloatField(default=0)
    percentage = models.FloatField(default=0)
    grade = models.CharField(max_length=2)
    grade_point = models.FloatField(default=0)
    credit_points = models.FloatField(default=0)  # grade_point * credits
    is_reappearance = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('student', 'course', 'semester', 'is_reappearance')
    
    def __str__(self):
        return f"{self.student} - {self.course} - {self.grade}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate credit points
        self.credit_points = self.grade_point * self.credits
        super().save(*args, **kwargs)


class SemesterResult(models.Model):
    """Model to store semester-wise results"""
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    semester = models.IntegerField()
    total_credits = models.IntegerField(default=0)
    earned_credits = models.IntegerField(default=0)  # Excludes F grades
    total_credit_points = models.FloatField(default=0)
    sgpa = models.FloatField(default=0)
    
    class Meta:
        unique_together = ('student', 'semester')
    
    def __str__(self):
        return f"{self.student} - Semester {self.semester} - SGPA: {self.sgpa}"


class CGPA(models.Model):
    """Model to store cumulative GPA for students"""
    id = models.AutoField(primary_key=True)
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    total_credits = models.IntegerField(default=0)
    total_credit_points = models.FloatField(default=0)
    cgpa = models.FloatField(default=0)
    
    def __str__(self):
        return f"{self.student} - CGPA: {self.cgpa}"