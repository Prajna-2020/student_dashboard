# faculty_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse,Http404
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group

from webapp.Student_views import calculate_grade
from .models import (
    Faculty, Course, Enrollment, Attendance,
    InternalMarks, ExternalMarks, Assignments,
    Quizzes, Regular_Projects, Student, Scheme,CourseScheme
)
import pandas as pd
from datetime import date
from django.conf import settings
import os
import csv
from io import StringIO
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Case, When
import json
from django.db.models import Count
import json
from django.db.models import Q
from django.db.models import Q, Count, Case, When
from .models import Faculty, Student, Course, Attendance, InternalMarks
from django.core.exceptions import ObjectDoesNotExist
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from .models import Faculty, Student, Course, Attendance, InternalMarks, Department,Event
from django.contrib.auth.decorators import login_required,user_passes_test
from django.utils import timezone
from .models import Course, Announcement
from django.core.files.storage import FileSystemStorage
from calendar import month_name, monthrange
from datetime import datetime
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.shortcuts import redirect, render
from django.conf import settings
import os

def faculty_required(view_func):
    decorated_view = login_required(
        user_passes_test(
            lambda u: u.groups.filter(name='Faculty').exists(),
            login_url='/signin'
        )(view_func)
    )
    return decorated_view

def documentation_view(request):
    return render(request, 'faculty/documentation.html')

@login_required
@faculty_required
def faculty_profile(request):
    if not hasattr(request.user, 'faculty'):
        messages.error(request, 'Faculty profile not found')
        return redirect('home')
    
    faculty = request.user.faculty
    
    if request.method == 'POST':
        try:
            # Update basic information
            faculty.first_name = request.POST.get('first_name', faculty.first_name)
            faculty.last_name = request.POST.get('last_name', faculty.last_name)
            faculty.email = request.POST.get('email', faculty.email)
            faculty.phone_number = request.POST.get('phone', faculty.phone_number)
            
            # Update personal details
            dob = request.POST.get('date_of_birth')
            if dob:
                faculty.date_of_birth = dob
            faculty.gender = request.POST.get('gender', faculty.gender)
            faculty.nationality = request.POST.get('nationality', faculty.nationality)
            faculty.blood_group = request.POST.get('blood_group', faculty.blood_group)
            faculty.address = request.POST.get('address', faculty.address)
            
            # Update emergency contact
            faculty.emergency_name = request.POST.get('emergency_name', faculty.emergency_name)
            faculty.emergency_contact = request.POST.get('emergency_contact', faculty.emergency_contact)
            faculty.emergency_relation = request.POST.get('emergency_relation', faculty.emergency_relation)
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                profile_pic = request.FILES['profile_picture']
                if profile_pic.size > 2 * 1024 * 1024:  # 2MB limit
                    messages.error(request, 'Profile picture size should be less than 2MB')
                else:
                    # Delete old profile picture if exists
                    if faculty.profile_picture:
                        old_pic_path = os.path.join(settings.MEDIA_ROOT, str(faculty.profile_picture))
                        if os.path.exists(old_pic_path):
                            os.remove(old_pic_path)
                    
                    # Save new profile picture
                    fs = FileSystemStorage()
                    filename = fs.save(f'faculty_profiles/{request.user.username}_{profile_pic.name}', profile_pic)
                    faculty.profile_picture = filename
            
            faculty.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('faculty_profile')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    context = {
        'faculty': faculty,
        'user': request.user
    }
    return render(request, 'faculty/fac_profile.html', context)

@login_required
@faculty_required
def faculty_dashboard(request):
    # Get the logged-in faculty
    faculty = request.user.faculty
    
    # Get statistics
    total_students = Student.objects.count()
    total_faculty = Faculty.objects.count()
    
    # Get courses taught by this faculty
    faculty_courses = Course.objects.filter(enrollment__faculty=faculty).distinct()
    faculty_courses_count = faculty_courses.count()
    
    # Get students enrolled in courses taught by this faculty
    faculty_students_count = Student.objects.filter(
        enrollment__faculty=faculty
    ).distinct().count()
    
    # Get recent attendance records (last 5)
    recent_attendance = Attendance.objects.filter(
        course__in=faculty_courses
    ).order_by('-date')[:5]

    
    
    # Get recent internal marks records (last 5)
    recent_results = InternalMarks.objects.filter(
        course__in=faculty_courses
    ).order_by('-date')[:5]


    
    # Get today's attendance summary
    today = timezone.now().date()
    today_attendance = {
        'present': Attendance.objects.filter(
            course__in=faculty_courses,
            date=today,
            status='Present'
        ).count(),
        'absent': Attendance.objects.filter(
            course__in=faculty_courses,
            date=today,
            status='Absent'
        ).count(),
    }
    today = timezone.now().date()
    today_activities = []
    today_attendance_entries = Attendance.objects.filter(
        course__in=faculty_courses,
        date=today
    ).select_related('course', 'student__user')[:5]
    
    for att in today_attendance_entries:
        today_activities.append({
            'type': 'attendance',
            'object': att,
            'date': att.date,
            'description': f"Marked attendance for {att.course.course_code}",
            'details': f"{att.student.user.get_full_name()} - {att.status}"
        })
    
    # Internal Marks
    today_internal_marks = InternalMarks.objects.filter(
        course__in=faculty_courses,
        date=today
    ).select_related('course', 'student__user')[:5]
    
    for mark in today_internal_marks:
        today_activities.append({
            'type': 'internal',
            'object': mark,
            'date': mark.date,
            'description': f"Entered internal {mark.internal_number} marks for {mark.course.course_code}",
            'details': f"{mark.student.user.get_full_name()} - {mark.marks}/{mark.max_marks}"
        })
    
    # External Marks (add similar queries for other types)
    today_external_marks = ExternalMarks.objects.filter(
        course__in=faculty_courses,
        date=today
    ).select_related('course', 'student__user')[:5]
    
    for ext in today_external_marks:
        today_activities.append({
            'type': 'external',
            'object': ext,
            'date': ext.date,
            'description': f"Entered external marks for {ext.course.course_code}",
            'details': f"{ext.student.user.get_full_name()} - {ext.marks}/{ext.max_marks}"
        })
    
    # Projects (add similar queries)
    today_projects = Regular_Projects.objects.filter(
        course__in=faculty_courses,
        submission_date=today
    ).select_related('course', 'student__user')[:5]
    
    for proj in today_projects:
        today_activities.append({
            'type': 'project',
            'object': proj,
            'date': proj.submission_date,
            'description': f"Graded project for {proj.course.course_code}",
            'details': f"{proj.student.user.get_full_name()} - {proj.marks}/{proj.max_marks}"
        })
    
    # Sort all today's activities by time (if you have time fields)
    today_activities.sort(key=lambda x: x['date'], reverse=True)
    
    # Get older activities (last 5)
    older_activities = []
    
    # Attendance
    older_attendance = Attendance.objects.filter(
        course__in=faculty_courses,
        date__lt=today
    ).order_by('-date')[:5]
    
    # ... [similar queries for other types] ...
    
    # Combine today's and older activities
    recent_activities = today_activities[:10]  # Show max 5 today's activities
    
    # Handle search functionality
    search_query = request.GET.get('search', '')
    students = None
    if search_query:
        students = Student.objects.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        ).distinct()
    
    context = {
        'total_students': total_students,
        'total_faculty': total_faculty,
        'faculty_courses_count': faculty_courses_count,
        'faculty_students_count': faculty_students_count,
        'faculty_courses': faculty_courses,
        'recent_attendance': recent_attendance,
        'recent_results': recent_results,
        'today_attendance': today_attendance,
        'search_query': search_query,
        'students': students,
        'recent_activities': recent_activities,
        'today_activities_count': len(today_activities),
    }
    
    return render(request, 'faculty/dashboard.html', context)

@login_required
@faculty_required
def student_detail(request, student_id):
    try:
        student = Student.objects.get(pk=student_id)
        enrollments = Enrollment.objects.filter(
            student=student
        ).select_related('course', 'scheme').order_by('course__semester', 'course__course_name')
        
        # Attendance Data
        attendance_data = []
        for enrollment in enrollments:
            total_classes = Attendance.objects.filter(
                course=enrollment.course,
                date__gte=enrollment.enrollment_date
            ).count()
            
            present_classes = Attendance.objects.filter(
                course=enrollment.course,
                student=student,
                status='Present',
                date__gte=enrollment.enrollment_date
            ).count()
            
            attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
            
            attendance_data.append({
                'course': enrollment.course,
                'total_classes': total_classes,
                'present_classes': present_classes,
                'attendance_percentage': attendance_percentage,
                'status': 'Good' if attendance_percentage >= 75 else 'Low'
            })
        
        # Assessment Data - using the improved logic from store_course_results
        assessment_data = []
        semester_assessments = {}
        
        for enrollment in enrollments:
            course = enrollment.course
            scheme = enrollment.scheme
            
            # Get all assessment data
            internal_marks = InternalMarks.objects.filter(
                student=student,
                course=course,
                scheme=scheme
            ).order_by('internal_number')
            
            assignments = Assignments.objects.filter(
                student=student,
                course=course,
                scheme=scheme
            ).order_by('assignment_number')
            
            quizzes = []
            if course.quiz_count > 0:
                quizzes = Quizzes.objects.filter(
                    student=student,
                    course=course,
                    scheme=scheme
                ).order_by('quiz_number')
            
            projects = []
            if course.project_count > 0:
                projects = Regular_Projects.objects.filter(
                    student=student,
                    course=course,
                    scheme=scheme
                )
            
            # Get external marks
            try:
                external_marks = ExternalMarks.objects.get(
                    student=student,
                    course=course,
                    scheme=scheme,
                    semester=course.semester
                )
            except ExternalMarks.DoesNotExist:
                external_marks = None
            
            # Get course scheme
            try:
                course_scheme = CourseScheme.objects.get(
                    course=course,
                    scheme=scheme
                )
            except CourseScheme.DoesNotExist:
                course_scheme = None
            
            # Calculate marks
            internal_total_marks = sum(internal.marks for internal in internal_marks)
            internal_total_max = sum(internal.max_marks for internal in internal_marks)
            
            assignment_total_marks = sum(assignment.marks for assignment in assignments)
            assignment_total_max = sum(assignment.max_marks for assignment in assignments)
            
            quiz_total_marks = sum(quiz.marks for quiz in quizzes)
            quiz_total_max = sum(quiz.max_marks for quiz in quizzes)
            
            project_total_marks = sum(project.marks for project in projects)
            project_total_max = sum(project.max_marks for project in projects)
            
            # Calculate scaled marks
            scaled_internal = 0
            scaled_assignment = 0
            scaled_quiz = 0
            scaled_project = 0
            
            if internal_total_max > 0:
                scaled_internal = (internal_total_marks / internal_total_max) * course.internal_total_marks
            
            if assignment_total_max > 0:
                scaled_assignment = (assignment_total_marks / assignment_total_max) * course.assignment_total_marks
            
            if quiz_total_max > 0:
                scaled_quiz = (quiz_total_marks / quiz_total_max) * course.quiz_total_marks
            
            if project_total_max > 0:
                scaled_project = (project_total_marks / project_total_max) * course.project_total_marks
            
            total_internal_marks = round(scaled_internal + scaled_assignment + scaled_quiz + scaled_project, 2)
            
            # Calculate weighted marks and final grade
            internal_weighted = None
            external_weighted = None
            final_marks = None
            grade = 'N/A'
            grade_point = 0.0
            
            if course_scheme:
                internal_weighted = (total_internal_marks * course_scheme.internal_weightage) / 100
                
                if external_marks and external_marks.max_marks > 0:
                    external_percentage = (external_marks.marks / external_marks.max_marks) * 100
                    external_weighted = (external_percentage * course_scheme.external_weightage) / 100
                
                if internal_weighted is not None and external_weighted is not None:
                    final_marks = int(round(internal_weighted + external_weighted, 0))
                    # Set default values for min_cie, min_see, min_final
                    min_cie = 0.4 * course_scheme.internal_weightage if course_scheme else None
                    min_see = 0.35 * course_scheme.external_weightage if course_scheme else None
                    min_final = 40
                    # Pass these parameters to calculate_grade
                    grade, grade_point = calculate_grade(
                        final_marks,
                        min_cie,
                        min_see,
                        min_final,
                        internal_weighted,
                        external_weighted
                    )
            
            # Passing criteria
            min_cie = 0.4 * course_scheme.internal_weightage if course_scheme else 0
            min_see = 0.35 * course_scheme.external_weightage if course_scheme else 0
            is_passing = (
                (internal_weighted or 0) >= min_cie and
                (external_weighted or 0) >= min_see and
                (final_marks or 0) >= 40
            )
            
            # Process internals for display
            processed_internals = []
            for mark in internal_marks:
                percentage = (mark.marks / mark.max_marks * 100) if mark.max_marks else 0
                processed_internals.append({
                    'number': mark.internal_number,
                    'marks': mark.marks,
                    'max_marks': mark.max_marks,
                    'percentage': percentage,
                    'status': 'Good' if percentage >= 40 else 'Low'
                })
            
            # Process external marks for display
            processed_external = None
            if external_marks:
                percentage = (external_marks.marks / external_marks.max_marks * 100) if external_marks.max_marks else 0
                processed_external = {
                    'marks': external_marks.marks,
                    'max_marks': external_marks.max_marks,
                    'percentage': percentage,
                    'status': 'Good' if percentage >= 40 else 'Low'
                }
            
            assessment = {
                'course': course,
                'internals': processed_internals,
                'external': processed_external,
                'course_code': course.course_code,
                'cie_raw_total': total_internal_marks,
                'cie_scaled': internal_weighted or 0,
                'see_scaled': external_weighted or 0,
                'final_total': final_marks or 0,
                'grade': grade,
                'grade_point': grade_point,
                'is_passing': is_passing,
                'internal_weightage': course_scheme.internal_weightage if course_scheme else 0,
                'external_weightage': course_scheme.external_weightage if course_scheme else 0,
                'credits': course.credits
            }
            
            assessment_data.append(assessment)
            
            # Organize by semester for SGPA calculation
            semester = course.semester
            if semester not in semester_assessments:
                semester_assessments[semester] = []
            semester_assessments[semester].append(assessment)
        
        # Calculate SGPA for each semester
        sgpa_data = {}
        for semester, assessments in semester_assessments.items():
            total_credit_points = sum(a['grade_point'] * a['credits'] for a in assessments)
            total_credits = sum(a['credits'] for a in assessments)
            sgpa = round(total_credit_points / total_credits, 2) if total_credits > 0 else 0
            
            sgpa_data[semester] = {
                'sgpa': sgpa,
                'total_credits': total_credits,
                'earned_credits': sum(a['credits'] for a in assessments if a['grade'] not in ['F', 'N/A'])
            }
        
        # Calculate CGPA (similar to store_semester_results)
        all_passed_courses = [a for a in assessment_data if a['grade'] not in ['F', 'N/A']]
        total_credits_cgpa = sum(a['credits'] for a in all_passed_courses)
        total_credit_points_cgpa = sum(a['grade_point'] * a['credits'] for a in all_passed_courses)
        cgpa = round(total_credit_points_cgpa / total_credits_cgpa, 2) if total_credits_cgpa > 0 else 0
        
        context = {
            'student': student,
            'attendance_data': attendance_data,
            'assessment_data': assessment_data,
            'semester_assessments': semester_assessments,
            'sgpa_data': sgpa_data,
            'cgpa': cgpa,
        }
        return render(request, 'faculty/student_detail.html', context)
        
    except Student.DoesNotExist:
        raise Http404("Student not found")

@faculty_required
def post_announcement(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        course_id = request.POST.get('course')
        course = Course.objects.get(course_id=course_id)  # Changed from id to course_id
        
        Announcement.objects.create(
            title=title,
            content=content,
            course=course,
            faculty=request.user.faculty
        )
        return redirect('post_announcement')
        
    # Get courses taught by the faculty
    courses = Course.objects.filter(enrollment__faculty=request.user.faculty).distinct()
    return render(request, 'faculty/post_announcement.html', {'courses': courses})

@faculty_required
def course_actions(request, action_type):
    courses = Course.objects.filter(enrollment__faculty=request.user.faculty).distinct()
    return render(request, 'faculty/course_actions.html', {
        'courses': courses,
        'action_type': action_type
    })

@login_required
@faculty_required
def faculty_home(request):
    try:
        faculty = Faculty.objects.get(user=request.user)
        department = faculty.department
        
        
        # Get recent attendance (last 5 records)
        recent_attendance = Attendance.objects.filter(
            course__department=department
        ).select_related('course').order_by('-date')[:5]

        # Get performance data
        performance_data = InternalMarks.objects.filter(
            course__department=department
        ).values('course__course_name').annotate(
            avg_score=Avg('marks')
        ).order_by('-avg_score')[:5]

        # Department summary
        department_summary = {
            'total_courses': Course.objects.filter(department=department).count(),
            'student_distribution': Student.objects.filter(department=department)
                .values('current_semester')
                .annotate(count=Count('user'))
        }

        context = {
            # ... existing context ...
            'recent_attendance': recent_attendance,
            'performance_data': performance_data,
            'department_summary': department_summary,
            'department': department,
        }

    except Faculty.DoesNotExist:
        return redirect('login')

    return render(request, 'faculty/faculty_home.html', context)

@login_required
@faculty_required
def fac_course(request):
    try:
        faculty = Faculty.objects.get(user=request.user)
        faculty_courses = Course.objects.filter(enrollment__faculty=faculty).distinct()
        context = {'faculty_courses': faculty_courses}
        return render(request, 'faculty/fac_course.html', context)
    except Faculty.DoesNotExist:
        return redirect('login')

@login_required
@faculty_required
def attendance(request, course_name):
    try:
        faculty = Faculty.objects.get(user=request.user)
        course = get_object_or_404(Course, course_name=course_name)
        if not Enrollment.objects.filter(course=course, faculty=faculty).exists():
            return HttpResponse("You are not assigned to this course", status=403)
        enrollments = Enrollment.objects.filter(course=course, faculty=faculty)
        students = [e.student for e in enrollments]
        
        # Get existing attendance records
        attendance_records = Attendance.objects.filter(
            course=course,
            student__in=students
        ).order_by('-date')[:50]

        context = {
            'course_name': course.course_name,
            'attendance_records': attendance_records,
            'students': students,
            'today': date.today(),
        }
        return render(request, 'faculty/attendance.html', context)
        
    except Faculty.DoesNotExist:
        return redirect('login')

@login_required
@faculty_required
def results(request, course_name):
    try:
        faculty = Faculty.objects.get(user=request.user)
        course = get_object_or_404(Course, course_name=course_name)
        schemes = Scheme.objects.filter(coursescheme__course=course).distinct()
        enrollments = Enrollment.objects.filter(course=course, faculty=faculty)
        students = [e.student for e in enrollments]

        context = {
            'course': course,
            'schemes': schemes,
            'students': students,
        }
        return render(request, 'faculty/results.html', context)
        
    except Faculty.DoesNotExist:
        return redirect('login')

@login_required
@faculty_required
def download_attendance_template(request, course_name):
    try:
        faculty = Faculty.objects.get(user=request.user)
        course = get_object_or_404(Course, course_name=course_name)
        enrollments = Enrollment.objects.filter(course=course, faculty=faculty)
        students = [e.student for e in enrollments]

        data = {
            'usn': [s.user.username for s in students],
            'status': ['Present' for _ in students],
            'date': [date.today().strftime('%Y-%m-%d') for _ in students]
        }
        
        df = pd.DataFrame(data)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{course_name}_attendance_template.csv"'
        df.to_csv(response, index=False)
        return response
        
    except Exception as e:
        messages.error(request, f"Error generating template: {str(e)}")
        return redirect('attendance', course_name=course_name)

# Other views (profile, documentation_view, etc.)
@faculty_required
def profile(request):
    return render(request, 'faculty/profile.html')

@faculty_required
def documentation_view(request):
    return render(request, 'faculty/documentation.html')

@login_required
@faculty_required
def upload_attendance_csv(request, course_name):
    if request.method == 'POST':
        try:
            faculty = Faculty.objects.get(user=request.user)
            course = get_object_or_404(Course, course_name=course_name)
            attendance_date = request.POST.get('attendance_date')
            csv_file = request.FILES['csv_file']
            
            # Read CSV content
            decoded_file = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(decoded_file.splitlines())
            
            # Store CSV data for display
            csv_data = []
            for row in csv_reader:
                csv_data.append({
                    'usn': row.get('usn', ''),
                    'status': row.get('status', 'Absent')
                })
            
            context = {
                'course_name': course_name,
                'csv_data': csv_data,
                'attendance_date': attendance_date,
                'show_csv': True
            }
            return render(request, 'faculty/attendance.html', context)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return redirect('attendance', course_name=course_name)

@faculty_required
def results(request, course_name):
    try:
        course = Course.objects.get(course_name=course_name)
        return render(request, 'faculty/results.html', {
            'course_name': course_name,
            'course': course
        })
    except Course.DoesNotExist:
        messages.error(request, "Course not found")
        return redirect('fac_course')

@faculty_required
def download_results_template(request, course_name):
    try:
        faculty = Faculty.objects.get(user=request.user)
        course = Course.objects.get(course_name=course_name)
        enrollments = Enrollment.objects.filter(course=course, faculty=faculty)
        
        # Create a CSV in memory
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{course_name}_results_template.csv"'
        
        writer = csv.writer(response)
        
        # Write header row based on course scheme
        headers = ['usn']
        
        # Add internal exam columns
        for i in range(1, course.internal_count + 1):
            headers.append(f'internal_{i}')
        
        # Add assignment columns if applicable
        if course.assignment_count > 0:
            for i in range(1, course.assignment_count + 1):
                headers.append(f'assignment_{i}')
        
        # Add quiz columns if applicable
        if course.quiz_count > 0:
            for i in range(1, course.quiz_count + 1):
                headers.append(f'quiz_{i}')
        
        # Add project column if applicable
        if course.project_count > 0:
            headers.append('project')
        
        # Add external column
        headers.append('external')
        
        writer.writerow(headers)
        
        # Add student rows
        for enrollment in enrollments:
            row = [enrollment.student.user.username]
            # Add empty columns for all possible marks
            row.extend([''] * (len(headers) - 1))
            writer.writerow(row)
            
        return response
        
    except Course.DoesNotExist:
        messages.error(request, "Course not found")
        return redirect('fac_course')

@faculty_required
def upload_results_csv(request, course_name):
    if request.method == 'POST':
        try:
            course = Course.objects.get(course_name=course_name)
            assessment_type = request.POST.get('assessment_type')
            csv_file = request.FILES['csv_file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, "Please upload a CSV file")
                return redirect('results', course_name=course_name)
            
            # Read CSV file
            df = pd.read_csv(csv_file)
            
            # Validate required columns
            required_columns = ['usn']
            if assessment_type == 'internal':
                internal_number = int(request.POST.get('internal_number', 1))
                required_columns.append(f'internal_{internal_number}')
            elif assessment_type == 'assignment':
                assignment_number = int(request.POST.get('assignment_number', 1))
                required_columns.append(f'assignment_{assignment_number}')
            elif assessment_type == 'quiz':
                quiz_number = int(request.POST.get('quiz_number', 1))
                required_columns.append(f'quiz_{quiz_number}')
            elif assessment_type == 'project':
                required_columns.append('project')
            elif assessment_type == 'external':
                required_columns.append('external')
            
            if not all(col in df.columns for col in required_columns):
                messages.error(request, f"CSV must contain columns: {', '.join(required_columns)}")
                return redirect('results', course_name=course_name)
            
            success_count = 0
            error_count = 0
            
            for _, row in df.iterrows():
                try:
                    student = Student.objects.get(user__username=row['usn'])
                    enrollment = Enrollment.objects.get(student=student, course=course)
                    scheme = enrollment.scheme
                    semester = enrollment.semester
                    
                    if assessment_type == 'internal':
                        internal_number = int(request.POST.get('internal_number', 1))
                        max_marks = course.internal_total_marks / course.internal_count
                        
                        InternalMarks.objects.update_or_create(
                            student=student,
                            course=course,
                            scheme=scheme,
                            internal_number=internal_number,
                            defaults={
                                'marks': float(row[f'internal_{internal_number}']),
                                'max_marks': max_marks,
                                'date': timezone.now().date()
                            }
                        )
                        
                    elif assessment_type == 'assignment':
                        assignment_number = int(request.POST.get('assignment_number', 1))
                        max_marks = course.assignment_total_marks / course.assignment_count
                        
                        Assignments.objects.update_or_create(
                            student=student,
                            course=course,
                            scheme=scheme,
                            assignment_number=assignment_number,
                            defaults={
                                'marks': float(row[f'assignment_{assignment_number}']),
                                'max_marks': max_marks,
                                'submission_date': timezone.now().date()
                            }
                        )
                        
                    elif assessment_type == 'quiz':
                        quiz_number = int(request.POST.get('quiz_number', 1))
                        max_marks = course.quiz_total_marks / (course.quiz_count or 1)
                        
                        Quizzes.objects.update_or_create(
                            student=student,
                            course=course,
                            scheme=scheme,
                            quiz_number=quiz_number,
                            defaults={
                                'marks': float(row[f'quiz_{quiz_number}']),
                                'max_marks': max_marks,
                                'date': timezone.now().date()
                            }
                        )
                        
                    elif assessment_type == 'project':
                        Regular_Projects.objects.update_or_create(
                            student=student,
                            course=course,
                            scheme=scheme,
                            defaults={
                                'marks': float(row['project']),
                                'max_marks': course.project_total_marks,
                                'submission_date': timezone.now().date(),
                                'title': f"Project for {course.course_name}",
                                'comments': "Uploaded via CSV"
                            }
                        )
                    
                    elif assessment_type == 'external':
                        ExternalMarks.objects.update_or_create(
                            student=student,
                            course=course,
                            scheme=scheme,
                            semester=semester,
                            defaults={
                                'marks': float(row['external']),
                                'max_marks': 100,  # External typically out of 100
                                'date': timezone.now().date(),
                                'is_published': False
                            }
                        )
                    
                    success_count += 1
                    
                except Student.DoesNotExist:
                    error_count += 1
                    messages.error(request, f"Student with USN {row.get('usn', '')} not found")
                except Enrollment.DoesNotExist:
                    error_count += 1
                    messages.error(request, f"Student {row.get('usn', '')} not enrolled in this course")
                except Exception as e:
                    error_count += 1
                    messages.error(request, f"Error processing student {row.get('usn', '')}: {str(e)}")
            
            messages.success(request, f"Successfully processed {success_count} records")
            if error_count > 0:
                messages.warning(request, f"{error_count} records had errors")
            
        except Course.DoesNotExist:
            messages.error(request, "Course not found")
        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
        
        return redirect('results', course_name=course_name)
    
    return redirect('fac_course')

@login_required
@faculty_required
def confirm_attendance(request, course_name):
    if request.method == 'POST':
        try:
            faculty = Faculty.objects.get(user=request.user)
            course = get_object_or_404(Course, course_name=course_name)
            attendance_date = request.POST.get('attendance_date')
            
            total = 0
            success = 0
            errors = []
            
            # Process all rows from hidden inputs
            for key in request.POST:
                if key.startswith('usn_'):
                    counter = key.split('_')[1]
                    usn = request.POST.get(f'usn_{counter}')
                    status = request.POST.get(f'status_{counter}')
                    
                    try:
                        student = Student.objects.get(user__username=usn)
                        Attendance.objects.update_or_create(
                            student=student,
                            course=course,
                            date=attendance_date,
                            defaults={'status': status}
                        )
                        success += 1
                    except Exception as e:
                        errors.append(f"Error with {usn}: {str(e)}")
                    total += 1
            
            messages.success(request, f"Saved {success}/{total} records")
            if errors:
                messages.error(request, "Errors: " + ", ".join(errors[:3]))
            
            return redirect('attendance', course_name=course_name)
        
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return redirect('attendance', course_name=course_name)

@faculty_required
def faculty_list_students(request):
    departments = Department.objects.all()
    department_id = request.GET.get('department')
    search_query = request.GET.get('search')

    # Start with all students
    students = Student.objects.all().select_related('department', 'scheme')

    # Apply search if query exists (case-insensitive)
    if search_query:
        students = students.filter(
            Q(usn__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(admission_number__icontains=search_query)
        )

    # Apply department filter if selected (works AFTER search)
    if department_id:
        students = students.filter(department_id=department_id)

    context = {
        'students': students,
        'departments': departments,
    }
    return render(request, 'faculty/list_students.html', context)

@login_required
@faculty_required
def course_students(request, course_id):
    try:
        faculty = Faculty.objects.get(user=request.user)
        course = get_object_or_404(Course, pk=course_id)
        
        if not Enrollment.objects.filter(course=course, faculty=faculty).exists():
            raise PermissionDenied
        
        students = Student.objects.filter(
            enrollment__course=course,
            enrollment__faculty=faculty
        ).distinct().select_related('department')
        
        # Calculate max marks for each component
        internal_max = course.internal_total_marks / course.internal_count if course.internal_count else 0
        assignment_max = course.assignment_total_marks / course.assignment_count if course.assignment_count else 0
        quiz_max = course.quiz_total_marks / course.quiz_count if course.quiz_count else 0
        
        context = {
            'course': course,
            'students': students,
            'internal_max': internal_max,
            'assignment_max': assignment_max,
            'quiz_max': quiz_max,
            'project_max': course.project_total_marks,
        }
        return render(request, 'faculty/course_students.html', context)
    except Faculty.DoesNotExist:
        return redirect('login')
    
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
@login_required
@faculty_required
def get_student_results(request, course_id, student_id):
    try:
        faculty = Faculty.objects.get(user=request.user)
        course = get_object_or_404(Course, pk=course_id)
        student = get_object_or_404(Student, pk=student_id)
        
        enrollment = get_object_or_404(Enrollment, course=course, student=student, faculty=faculty)
        scheme = enrollment.scheme
        
        data = {
            'internals': list(InternalMarks.objects.filter(
                student=student, 
                course=course,
                scheme=scheme
            ).values('internal_number', 'marks')),
            
            'assignments': list(Assignments.objects.filter(
                student=student, 
                course=course,
                scheme=scheme
            ).values('assignment_number', 'marks')),
            
            'quizzes': list(Quizzes.objects.filter(
                student=student, 
                course=course,
                scheme=scheme
            ).values('quiz_number', 'marks')),
            
            'project': Regular_Projects.objects.filter(
                student=student, 
                course=course,
                scheme=scheme
            ).first(),
            
            'external': ExternalMarks.objects.filter(
                student=student, 
                course=course,
                scheme=scheme
            ).first(),
        }
        
        # Serialize project and external if they exist
        if data['project']:
            data['project'] = {'marks': data['project'].marks}
        else:
            data['project'] = None
            
        if data['external']:
            data['external'] = {'marks': data['external'].marks}
        else:
            data['external'] = None
            
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
from django.http import JsonResponse

@login_required
@faculty_required
def save_student_results(request):
    if request.method == 'POST':
        try:
            faculty = Faculty.objects.get(user=request.user)
            course_id = request.POST.get('course_id')
            student_id = request.POST.get('student_id')
            
            course = get_object_or_404(Course, pk=course_id)
            student = get_object_or_404(Student, pk=student_id)
            
            enrollment = get_object_or_404(Enrollment, course=course, student=student, faculty=faculty)
            scheme = enrollment.scheme
            
            # Process Internals
            for i in range(1, course.internal_count + 1):
                marks_key = f'internal_{i}'
                if marks_key in request.POST and request.POST[marks_key]:
                    marks = float(request.POST[marks_key])
                    max_marks = course.internal_total_marks / course.internal_count
                    
                    internal, created = InternalMarks.objects.get_or_create(
                        student=student,
                        course=course,
                        scheme=scheme,
                        internal_number=i,
                        defaults={
                            'marks': marks,
                            'max_marks': max_marks
                        }
                    )
                    if not created:
                        internal.marks = marks
                        internal.save()
            
            # Process Assignments
            for i in range(1, course.assignment_count + 1):
                marks_key = f'assignment_{i}'
                if marks_key in request.POST and request.POST[marks_key]:
                    marks = float(request.POST[marks_key])
                    max_marks = course.assignment_total_marks / course.assignment_count
                    
                    assignment, created = Assignments.objects.get_or_create(
                        student=student,
                        course=course,
                        scheme=scheme,
                        assignment_number=i,
                        defaults={
                            'marks': marks,
                            'max_marks': max_marks
                        }
                    )
                    if not created:
                        assignment.marks = marks
                        assignment.save()
            
            # Process Quizzes
            for i in range(1, (course.quiz_count or 0) + 1):
                marks_key = f'quiz_{i}'
                if marks_key in request.POST and request.POST[marks_key]:
                    marks = float(request.POST[marks_key])
                    max_marks = course.quiz_total_marks / (course.quiz_count or 1)
                    
                    quiz, created = Quizzes.objects.get_or_create(
                        student=student,
                        course=course,
                        scheme=scheme,
                        quiz_number=i,
                        defaults={
                            'marks': marks,
                            'max_marks': max_marks,
                            'date': timezone.now().date()
                        }
                    )
                    if not created:
                        quiz.marks = marks
                        quiz.save()
            
            # Process Project
            if course.project_total_marks > 0 and 'project' in request.POST and request.POST['project']:
                marks = float(request.POST['project'])
                project, created = Regular_Projects.objects.get_or_create(
                    student=student,
                    course=course,
                    scheme=scheme,
                    defaults={
                        'marks': marks,
                        'max_marks': course.project_total_marks,
                        'submission_date': timezone.now().date(),
                        'title': f"{course.course_code} Project"
                    }
                )
                if not created:
                    project.marks = marks
                    project.save()
            
            # Process External
            if 'external' in request.POST and request.POST['external']:
                marks = float(request.POST['external'])
                external, created = ExternalMarks.objects.get_or_create(
                    student=student,
                    course=course,
                    scheme=scheme,
                    semester=enrollment.semester,
                    defaults={
                        'marks': marks,
                        'max_marks': 100,
                        'date': timezone.now().date()
                    }
                )
                if not created:
                    external.marks = marks
                    external.save()
            
            return JsonResponse({'success': True})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)