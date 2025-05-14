from collections import defaultdict
from django.shortcuts import get_object_or_404, redirect, render
from webapp.models import Assignments, Course, CourseScheme, Enrollment, ExternalMarks, InternalMarks, Quizzes, Regular_Projects, Student
from django.contrib.auth.decorators import login_required,user_passes_test
from django.shortcuts import render
from django.db.models import Count, Q
from django.contrib import messages
from .models import CGPA, Announcement, CourseResult, SemesterResult, Student, Attendance, Enrollment, Course
from collections import defaultdict
from .forms import ProfilePictureForm
from django.shortcuts import render
from .models import CGPA, Student
from django.shortcuts import render
import json
from .models import Student, CGPA, SemesterResult

def student_required(view_func):
    decorated_view = login_required(
        user_passes_test(
            lambda u: u.groups.filter(name='Students').exists(),
            login_url='/signin'
        )(view_func)
    )
    return decorated_view

@student_required
def student_dashboard(request):
    context = {
        'cgpa': 'N/A',
        'total_credits': 0,
        'performance_available': False,
        'current_semester': 'N/A',
        'department': 'N/A',
        'attendance_chart_data': None,
        'attendance_available': False
    }

    if request.user.is_authenticated:
        try:
            # Get student profile (keep existing)
            student_profile = Student.objects.get(user=request.user)
            current_semester = student_profile.current_semester
            context['current_semester'] = current_semester
            context['department'] = student_profile.department

            # Get CGPA data (keep existing)
            try:
                cgpa_obj = CGPA.objects.get(student=student_profile)
                context.update({
                    'cgpa': round(cgpa_obj.cgpa, 2),
                    'total_credits': cgpa_obj.total_credits,
                    'total_credit_points': round(cgpa_obj.total_credit_points, 2)
                })
            except CGPA.DoesNotExist:
                context['warning'] = "CGPA record not available"

            # Get semester performance data for graph (keep existing)
            results = SemesterResult.objects.filter(student=student_profile).order_by('semester')
            if results.exists():
                semesters = [f"Sem {res.semester}" for res in results]
                sgpas = [float(res.sgpa) for res in results]
                
                context.update({
                    'sgpa_data': json.dumps({
                        'labels': semesters,
                        'data': sgpas,
                    }),
                    'performance_available': True,
                    'latest_sgpa': results.last().sgpa,
                    'results': results
                })

            # NEW: Get attendance data for doughnut chart
            enrollments = Enrollment.objects.filter(
                student=student_profile,
                semester=current_semester
            ).select_related('course')
            
            if enrollments.exists():
                attendance_data = []
                colors = []
                color_palette = [
                    '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', 
                    '#e74a3b', '#858796', '#5a5c69', '#00cc99',
                    '#9966ff', '#ff9933'
                ]
                
                for i, enrollment in enumerate(enrollments):
                    course = enrollment.course
                    total_days = Attendance.objects.filter(
                        student=student_profile,
                        course=course
                    ).count()
                    
                    days_present = Attendance.objects.filter(
                        student=student_profile,
                        course=course,
                        status='Present'
                    ).count()
                    
                    attendance_percentage = round((days_present / total_days * 100), 2) if total_days > 0 else 0
                    
                    attendance_data.append({
                        'course': course.course_name,
                        'percentage': attendance_percentage,
                        'color': color_palette[i % len(color_palette)]
                    })
                
                context.update({
                    'attendance_chart_data': json.dumps({
                        'labels': [d['course'] for d in attendance_data],
                        'data': [d['percentage'] for d in attendance_data],
                        'colors': [d['color'] for d in attendance_data],
                        'total_courses': len(enrollments)
                    }),
                    'attendance_available': True,
                    'attendance_details': attendance_data
                })

        except Student.DoesNotExist:
            context['error'] = "Student profile not found"

    return render(request, 'student/student_home.html', context)

@login_required
@student_required
def profile_details(request):
    try:
        # Get the student profile of the logged-in user
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found!")
            return redirect('home')  # Redirect to appropriate page if profile doesn't exist
        
        if request.method == 'POST':
            form = ProfilePictureForm(request.POST, request.FILES, instance=student)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile picture updated successfully!")
                return redirect('profile_details')
        else:
            form = ProfilePictureForm(instance=student)
        
        context = {
            'student': student,
            'form': form
        }
        
        return render(request, 'student/profile_details.html', context)

    except Student.DoesNotExist:
        return redirect('/signin')
    
@login_required
@student_required
def student_enrollments(request):
    try:
        # Get the current student
        student = Student.objects.get(user=request.user)
        
        # Get all enrollments for this student with related course and faculty data
        enrollments = Enrollment.objects.filter(student=student).select_related(
            'course', 'faculty', 'faculty__user'
        ).order_by('course__semester', 'course__course_name')
        
        # Organize courses by semester
        courses_by_semester = defaultdict(list)
        
        for enrollment in enrollments:
            semester = enrollment.course.semester
            courses_by_semester[semester].append(enrollment)
        
        # Convert to a list of (semester, courses) tuples, sorted by semester
        semester_courses = sorted(courses_by_semester.items())
        
        # Get current semester (the highest semester with enrollments)
        current_semester = max(courses_by_semester.keys()) if courses_by_semester else 1
        
        context = {
            'semester_courses': semester_courses,
            'current_semester': current_semester,
        }
        
        return render(request, 'student/student_enrollments.html', context)
    except Student.DoesNotExist:
        # Redirect to login if the user isn't associated with a student profile
        return redirect('/signin')
    
# Grade calculation
def calculate_grade(percentage, min_cie=None, min_see=None, min_final=None, cie_scaled=None, see_scaled=None):
    if percentage is None:
        return 'N/A', 0.0  # Return default values if percentage is None
    
    percentage = float(percentage)  # Ensure it's a number

    # Strict passing criteria check - fails if any component is below minimum
    if (cie_scaled is not None and cie_scaled < min_cie) or \
       (see_scaled is not None and see_scaled < min_see) or \
       percentage < min_final:
        return 'F', 0.0
    
    if 90 <= percentage <= 100:
        return 'S', 10.0
    elif 80 <= percentage < 90:
        return 'A', 9.0
    elif 70 <= percentage < 80:
        return 'B', 8.0
    elif 60 <= percentage < 70:
        return 'C', 7.0
    elif 45 <= percentage < 60:
        return 'D', 6.0
    elif 40 <= percentage < 45:
        return 'E', 4.0
    else:
        return 'F', 0.0


def student_results(request):
    try:
        student = Student.objects.get(user=request.user)
        enrollments = Enrollment.objects.filter(student=student).select_related(
            'course', 'faculty', 'scheme'
        ).order_by('course__semester', 'course__course_name')
        
        enrollments_by_sem = {}
        
        for enrollment in enrollments:
            course_semester = enrollment.course.semester
            
            if course_semester not in enrollments_by_sem:
                enrollments_by_sem[course_semester] = []
            
            grade = None
            grade_point = None

            # Fetch all assessment components
            internal_marks = InternalMarks.objects.filter(
                student=student,
                course=enrollment.course,
                scheme=enrollment.scheme
            ).order_by('internal_number')
            
            assignments = Assignments.objects.filter(
                student=student,
                course=enrollment.course,
                scheme=enrollment.scheme
            ).order_by('assignment_number')
            
            quizzes = []
            if enrollment.course.quiz_count > 0:
                quizzes = Quizzes.objects.filter(
                    student=student,
                    course=enrollment.course,
                    scheme=enrollment.scheme
                ).order_by('quiz_number')
            
            projects = []
            if enrollment.course.project_count > 0:
                projects = Regular_Projects.objects.filter(
                    student=student,
                    course=enrollment.course,
                    scheme=enrollment.scheme
                )
            
            # External marks
            try:
                external_marks = ExternalMarks.objects.get(
                    student=student,
                    course=enrollment.course,
                    scheme=enrollment.scheme,
                    semester=enrollment.course.semester
                )
            except ExternalMarks.DoesNotExist:
                external_marks = None
            
            # Course scheme
            try:
                course_scheme = CourseScheme.objects.get(
                    course=enrollment.course,
                    scheme=enrollment.scheme
                )
            except CourseScheme.DoesNotExist:
                course_scheme = None
            
            # Calculate component totals
            internal_total_marks = sum(internal.marks for internal in internal_marks)
            internal_total_max = sum(internal.max_marks for internal in internal_marks)
            
            assignment_total_marks = sum(assignment.marks for assignment in assignments)
            assignment_total_max = sum(assignment.max_marks for assignment in assignments)
            
            quiz_total_marks = sum(quiz.marks for quiz in quizzes)
            quiz_total_max = sum(quiz.max_marks for quiz in quizzes)
            
            project_total_marks = sum(project.marks for project in projects)
            project_total_max = sum(project.max_marks for project in projects)
            
            # Scale to allocated marks
            course = enrollment.course
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
            
            # Weighted calculations
            internal_weighted = None
            external_weighted = None
            final_marks = None
            
            if course_scheme:
                internal_weighted = (total_internal_marks * course_scheme.internal_weightage) / 100
                
                if external_marks and external_marks.max_marks > 0:
                    external_percentage = (external_marks.marks / external_marks.max_marks) * 100
                    external_weighted = (external_percentage * course_scheme.external_weightage) / 100
                
                if internal_weighted is not None and external_weighted is not None:
                    final_marks = int(round(internal_weighted + external_weighted, 0))
                    
                    # Calculate minimum requirements
                    min_cie = 0.4 * course_scheme.internal_weightage
                    min_see = 0.35 * course_scheme.external_weightage
                    min_final = 40
                    
                    # Get grade with strict enforcement
                    grade, grade_point = calculate_grade(
                        final_marks,
                        min_cie,
                        min_see,
                        min_final,
                        internal_weighted,
                        external_weighted
                    )
            
            # Prepare course result data
            enrollment_data = {
                'enrollment_id': enrollment.enrollment_id,
                'course': enrollment.course,
                'faculty': enrollment.faculty,
                'semester': enrollment.semester,
                'internal_marks': [{
                    'internal_number': m.internal_number,
                    'marks': m.marks,
                    'max_marks': m.max_marks
                } for m in internal_marks],
                'assignments': [{
                    'assignment_number': a.assignment_number,
                    'marks': a.marks,
                    'max_marks': a.max_marks
                } for a in assignments],
                'quizzes': [{
                    'quiz_number': q.quiz_number,
                    'marks': q.marks,
                    'max_marks': q.max_marks
                } for q in quizzes],
                'projects': [{
                    'title': p.title,
                    'marks': p.marks,
                    'max_marks': p.max_marks
                } for p in projects],
                'external_marks': external_marks,
                'course_scheme': course_scheme,
                'component_marks': {
                    'internal': {
                        'obtained': internal_total_marks,
                        'max': internal_total_max,
                        'scaled': round(scaled_internal, 2),
                        'allocated': course.internal_total_marks
                    },
                    'assignment': {
                        'obtained': assignment_total_marks,
                        'max': assignment_total_max,
                        'scaled': round(scaled_assignment, 2),
                        'allocated': course.assignment_total_marks
                    },
                    'quiz': {
                        'obtained': quiz_total_marks,
                        'max': quiz_total_max,
                        'scaled': round(scaled_quiz, 2),
                        'allocated': course.quiz_total_marks
                    },
                    'project': {
                        'obtained': project_total_marks,
                        'max': project_total_max,
                        'scaled': round(scaled_project, 2),
                        'allocated': course.project_total_marks
                    },
                    'total_internal': total_internal_marks,
                },
                'weighted_marks': {
                    'internal': round(internal_weighted, 2) if internal_weighted is not None else None,
                    'external': round(external_weighted, 2) if external_weighted is not None else None,
                    'final': final_marks
                },
                'grade': grade,
                'grade_point': grade_point,
                'min_requirements': {
                    'min_cie': round(0.4 * course_scheme.internal_weightage, 2) if course_scheme else None,
                    'min_see': round(0.35 * course_scheme.external_weightage, 2) if course_scheme else None,
                    'min_final': 40
                }
            }
            
            enrollments_by_sem[course_semester].append(enrollment_data)
        
        # Sort semesters
        enrollments_by_sem = {k: enrollments_by_sem[k] for k in sorted(enrollments_by_sem.keys())}
        
        context = {
            'student': student,
            'enrollments_by_sem': enrollments_by_sem
        }
        
        return render(request, 'student/student_results.html', context)
    
    except Student.DoesNotExist:
        return redirect('login')
    
@student_required
def student_attendance_view(request):
    try:
        # Get the current student
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return render(request, 'error.html', {'error': 'Student profile not found'})
        
        # Get all courses the student is enrolled in, organized by semester
        enrollments = Enrollment.objects.filter(student=student)
        
        # Create a dictionary to organize courses by semester
        semesters_data = defaultdict(list)
        
        for enrollment in enrollments:
            course = enrollment.course
            semester = course.semester
            
            # Count total attendance records for this course
            total_days = Attendance.objects.filter(
                student=student,
                course=course
            ).count()
            
            # Count days present
            days_present = Attendance.objects.filter(
                student=student,
                course=course,
                status='Present'
            ).count()
            
            # Calculate days absent
            days_absent = total_days - days_present
            
            # Calculate attendance percentage
            attendance_percentage = (days_present / total_days * 100) if total_days > 0 else 0
            
            # Round to 2 decimal places
            attendance_percentage = round(attendance_percentage, 2)
            
            # Determine the color class for the progress bar
            if attendance_percentage >= 85:
                status_class = "bg-success"
            elif attendance_percentage >= 75:
                status_class = "bg-warning"
            else:
                status_class = "bg-danger"
            
            # Add data to the semester dictionary
            semesters_data[semester].append({
                'course_name': course.course_name,
                'course_code': course.course_code,
                'total_days': total_days,
                'days_present': days_present,
                'days_absent': days_absent,
                'attendance_percentage': attendance_percentage,
                'status_class': status_class,
            })
        
        # Convert the defaultdict to a regular dict for the template
        semesters = dict(semesters_data)
        
        context = {
            'student': student,
            'semesters': semesters,
        }
        
        return render(request, 'student/student_attendance.html', context)

    except Student.DoesNotExist:
        return redirect('/signin')


@login_required
def store_course_results(request):
    try:
        student = Student.objects.get(user=request.user)
        enrollments = Enrollment.objects.filter(student=student).select_related(
            'course', 'faculty', 'scheme'
        ).order_by('course__semester', 'course__course_name')
        
        for enrollment in enrollments:
            # Get all assessment data (same as in student_results)
            internal_marks = InternalMarks.objects.filter(
                student=student,
                course=enrollment.course,
                scheme=enrollment.scheme
            ).order_by('internal_number')
            
            assignments = Assignments.objects.filter(
                student=student,
                course=enrollment.course,
                scheme=enrollment.scheme
            ).order_by('assignment_number')
            
            quizzes = []
            if enrollment.course.quiz_count > 0:
                quizzes = Quizzes.objects.filter(
                    student=student,
                    course=enrollment.course,
                    scheme=enrollment.scheme
                ).order_by('quiz_number')
            
            projects = []
            if enrollment.course.project_count > 0:
                projects = Regular_Projects.objects.filter(
                    student=student,
                    course=enrollment.course,
                    scheme=enrollment.scheme
                )
            
            # Get external marks
            try:
                external_marks = ExternalMarks.objects.get(
                    student=student,
                    course=enrollment.course,
                    scheme=enrollment.scheme,
                    semester=enrollment.course.semester
                )
            except ExternalMarks.DoesNotExist:
                external_marks = None
            
            # Get course scheme
            try:
                course_scheme = CourseScheme.objects.get(
                    course=enrollment.course,
                    scheme=enrollment.scheme
                )
            except CourseScheme.DoesNotExist:
                course_scheme = None
            
            # Calculate marks (same as in student_results)
            internal_total_marks = sum(internal.marks for internal in internal_marks)
            internal_total_max = sum(internal.max_marks for internal in internal_marks)
            
            assignment_total_marks = sum(assignment.marks for assignment in assignments)
            assignment_total_max = sum(assignment.max_marks for assignment in assignments)
            
            quiz_total_marks = sum(quiz.marks for quiz in quizzes)
            quiz_total_max = sum(quiz.max_marks for quiz in quizzes)
            
            project_total_marks = sum(project.marks for project in projects)
            project_total_max = sum(project.max_marks for project in projects)
            
            # Calculate scaled marks
            course = enrollment.course
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
                    # Define minimum passing criteria
                    min_cie = 0.4 * course_scheme.internal_weightage if course_scheme else None
                    min_see = 0.35 * course_scheme.external_weightage if course_scheme else None
                    min_final = 40
                    # Pass all parameters to calculate_grade
                    grade, grade_point = calculate_grade(
                        final_marks,
                        min_cie,
                        min_see,
                        min_final,
                        internal_weighted,
                        external_weighted
                    )
            
            # Create or update CourseResult
            CourseResult.objects.update_or_create(
                student=student,
                course=enrollment.course,
                semester=enrollment.course.semester,
                defaults={
                    'credits': enrollment.course.credits,
                    'internal_marks': total_internal_marks,
                    'external_marks': external_marks.marks if external_marks else 0,
                    'total_marks': final_marks if final_marks else 0,
                    'percentage': final_marks if final_marks else 0,
                    'grade': grade,
                    'grade_point': grade_point,
                    'credit_points': grade_point * enrollment.course.credits,
                    'is_reappearance': False  
                }
            )
        
        messages.success(request, "Course results have been updated successfully.")
        return redirect('student_results')
    
    except Exception as e:
        messages.error(request, f"An error occurred while updating results: {str(e)}")
        return redirect('student_results')
    
@login_required
def store_semester_results(request):
    try:
        student = Student.objects.get(user=request.user)
        
        # Get all course results for the student, grouped by semester
        course_results = CourseResult.objects.filter(student=student).order_by('semester')
        
        semesters = set(cr.semester for cr in course_results)
        all_passed_courses = course_results.exclude(grade__in=['F', 'N/A'])
        
        # Calculate CGPA components (all semesters combined)
        total_credits_cgpa = sum(cr.credits for cr in all_passed_courses)
        total_credit_points_cgpa = sum(cr.credit_points for cr in all_passed_courses)
        
        # Calculate CGPA
        cgpa = total_credit_points_cgpa / total_credits_cgpa if total_credits_cgpa > 0 else 0
        
        # Update or create CGPA record
        CGPA.objects.update_or_create(
            student=student,
            defaults={
                'total_credits': total_credits_cgpa,
                'total_credit_points': total_credit_points_cgpa,
                'cgpa': round(cgpa, 2)
            }
        )
        
        # Process each semester for SGPA
        for semester in sorted(semesters):
            # Filter results for this semester
            semester_courses = course_results.filter(semester=semester)
            
            # Calculate semester totals
            total_credits = sum(cr.credits for cr in semester_courses)
            earned_credits = sum(cr.credits for cr in semester_courses if cr.grade not in ['F', 'N/A'])
            total_credit_points = sum(cr.credit_points for cr in semester_courses)
            
            # Calculate SGPA (including F grades in denominator as per formula)
            sgpa = total_credit_points / total_credits if total_credits > 0 else 0
            
            # Create or update SemesterResult
            SemesterResult.objects.update_or_create(
                student=student,
                semester=semester,
                defaults={
                    'total_credits': total_credits,
                    'earned_credits': earned_credits,
                    'total_credit_points': total_credit_points,
                    'sgpa': round(sgpa, 2)
                }
            )
        
        messages.success(request, "Semester results and CGPA have been updated successfully.")
        return redirect('student_results')
    
    except Exception as e:
        messages.error(request, f"An error occurred while updating results: {str(e)}")
        return redirect('student_results')
    
def update_all_results(request):
    # First store all results as before
    store_course_results(request)
    store_semester_results(request)
    
    try:
        student = request.user.student
        
        # Get all distinct semesters from enrollments for this student
        enrolled_semesters = Enrollment.objects.filter(
            student=student
        ).values_list('semester', flat=True).distinct()
        
        # Only proceed if current semester is in enrolled semesters
        if student.current_semester in enrolled_semesters:
            # Check if student has more than 4 F grades in current semester
            failed_courses = CourseResult.objects.filter(
                student=student,
                semester=student.current_semester,
                grade='F'
            ).count()
            
            # If 4 or fewer backlogs, update semester
            if failed_courses <= 4:
                student.current_semester += 1
                student.save()
                messages.success(request, f"Results stored and semester updated to {student.current_semester}!")
            else:
                messages.warning(request, f"Results stored but semester not updated - you have {failed_courses} backlogs (maximum 4 allowed)")
        else:
            messages.info(request, "Results stored but semester not updated - current semester doesn't match enrolled courses")
    
    except (Student.DoesNotExist, AttributeError) as e:
        messages.error(request, "Error updating semester information")
    
    return redirect('student_results')

# Announcements view
@student_required
def view_announcements(request):
    try:
        # Get all enrollments for the current student
        enrollments = Enrollment.objects.filter(student=request.user.student)
        
        # Get all courses the student is enrolled in
        enrolled_courses = [enrollment.course for enrollment in enrollments]
        
        # Get announcements for these courses, ordered by most recent first
        announcements = Announcement.objects.filter(
            course__in=enrolled_courses
        ).order_by('-created_at')
        
        # Group announcements by course
        announcements_by_course = {}
        for announcement in announcements:
            if announcement.course not in announcements_by_course:
                announcements_by_course[announcement.course] = []
            announcements_by_course[announcement.course].append(announcement)
        
        return render(request, 'student/view_announcements.html', {
            'announcements_by_course': announcements_by_course
        })
    except Student.DoesNotExist:
        return redirect('/signin')
