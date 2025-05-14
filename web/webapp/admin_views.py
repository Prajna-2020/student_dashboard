from datetime import timezone
from itertools import count
import os
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from .models import Student, Faculty, Department, Course, Scheme, CourseScheme, Enrollment
from .forms import DepartmentForm,BulkUserCreationForm,BulkFacultyUploadForm,BulkStudentUploadForm,SchemeForm,CourseForm,CourseSchemeForm,EnrollmentForm,CourseCSVImportForm, StudentForm
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import TextIOWrapper
import csv
from django.db.models import Count, Value
from django.db.models.functions import Concat
from django.contrib.auth.decorators import login_required ,user_passes_test
from django.utils import timezone 

def is_admin(user):
    return user.is_staff or user.is_superuser

# create multiple users by csv file
@login_required
@user_passes_test(is_admin)
def add_by_file(request):
    if request.method == 'POST':
        form = BulkUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data.get('file')
            # Process the file
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith(('.xlsx', '.xls')):
                # Add Excel support if needed
                df = pd.read_excel(file)
            else:
                messages.error(request, 'Unsupported file format. Please upload a CSV or Excel file.')
                return render(request, 'admin/add_by_file.html', {'form': form})
                
            # Track success and failures
            success_count = 0
            error_count = 0
            errors = []
            
            # Iterate over rows and create users
            for index, row in df.iterrows():
                try:
                    # Create the user
                    user = User.objects.create_user(
                        username=row['username'],
                        first_name=row.get('first_name', ''),
                        last_name=row.get('last_name', ''),
                        email=row.get('email', ''),
                        password=row['password'],
                    )
                    
                    # Assign groups
                    if 'groups' in row and row['groups']:
                        groups = Group.objects.filter(name__in=row['groups'].split(','))
                        user.groups.set(groups)
                    
                    # Assign department (if applicable)
                    if 'department' in row and row['department']:
                        department = Department.objects.get(name=row['department'])
                    
                    # Create a Student or Faculty record
                    if 'groups' in row and row['groups']:
                        if 'Students' in row['groups'].lower():
                            Student.objects.create(
                                user=user,
                            )
                        elif 'Faculty' in row['groups'].lower():
                            Faculty.objects.create(
                                user=user,
                            )
                    success_count += 1
                except Exception as e:
                    # Collect error information
                    error_count += 1
                    errors.append(f"Row {index+1} ({row.get('username', 'Unknown')}): {str(e)}")
                    
            # Display appropriate messages
            if success_count > 0:
                messages.success(request, f'Successfully created {success_count} user(s).')
            
            if error_count > 0:
                messages.error(request, f'Failed to create {error_count} user(s). See admin logs for details.')
                # Log the detailed errors
                for error in errors:
                    print(error)
                    
            return redirect('add_by_file')  # Redirect to the same page to show the messages
    else:
        form = BulkUserCreationForm()
    return render(request, 'admin/add_by_file.html', {'form': form})

# to download the user csv file format
@login_required
@user_passes_test(is_admin)
def download_user_template(request):
    # Path to the template file
    file_path = os.path.join(settings.BASE_DIR, 'template', 'user_template.csv')
    
    # Debugging: Print the file path
    print(f"Looking for file at: {file_path}")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return HttpResponse("Template file not found. Please contact the administrator.", status=404)
    
    # Open the file and serve it as a response
    with open(file_path, 'rb') as file:
        response = HttpResponse(file.read(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=user_template.csv'
        return response

# Add Department View
@login_required
@user_passes_test(is_admin)
def add_department(request):
    departments = Department.objects.all()
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department added successfully!')
            return redirect('add_department')
    else:
        form = DepartmentForm()
    return render(request, 'admin/add_department.html', {'form': form, 'departments': departments})

# Update Department View
@login_required
@user_passes_test(is_admin)
def update_department(request, department_id):
    department = get_object_or_404(Department, department_id=department_id)
    if request.method == 'POST':
        department_name = request.POST.get('department_name')
        department.department_name = department_name
        department.save()
        messages.success(request, 'Department updated successfully!')
    return redirect('add_department')

# Delete Department View
@login_required
@user_passes_test(is_admin)
@require_POST
def delete_department(request, department_id):
    department = get_object_or_404(Department, department_id=department_id)
    try:
        department.delete()
        messages.success(request, 'Department deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting department: {str(e)}')
    return redirect('add_department')

@login_required
@user_passes_test(is_admin)
def download_faculty_template(request):
    faculty_group = Group.objects.get(name='Faculty')
    existing_faculty = Faculty.objects.all().values_list('user__username', flat=True)
    users = User.objects.filter(groups=faculty_group).exclude(username__in=existing_faculty)
    
    data = {
        'user_id': [user.id for user in users],
        'username': [user.username for user in users],
        'first_name': [user.first_name for user in users],
        'last_name': [user.last_name for user in users],
        'email': [user.email for user in users],
    }
    df = pd.DataFrame(data)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="faculty.csv"'
    df.to_csv(response, index=False)
    return response

#to download the faculty csv file format
@login_required
@user_passes_test(is_admin)
def download_faculty_formate(request):
    # Path to the template file
    file_path = os.path.join(settings.BASE_DIR, 'template', 'faculty_template.csv')
    
    # Debugging: Print the file path
    print(f"Looking for file at: {file_path}")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return HttpResponse("Template file not found. Please contact the administrator.", status=404)
    
    # Open the file and serve it as a response
    with open(file_path, 'rb') as file:
        response = HttpResponse(file.read(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=faculty_template.csv'
        return response
    
# Bulk Upload Faculty
@login_required
@user_passes_test(is_admin)
def bulk_upload_faculty(request):
    if request.method == 'POST':
        form = BulkFacultyUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            try:
                # Read the file
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:
                    messages.error(request, 'Unsupported file format. Please upload a CSV or Excel file.')
                    return redirect('bulk_upload_faculty')

                success_count = 0
                errors = []
                
                with transaction.atomic():
                    for _, row in df.iterrows():
                        try:
                            # Validate required fields
                            if not row.get('user_id'):
                                raise ValueError("User ID is required")
                            if not row.get('department'):
                                raise ValueError("Department is required")
                            
                            user_id = int(row['user_id'])
                            department = Department.objects.get(department_name=row['department'])
                            user = User.objects.get(id=user_id)
                            
                            # Helper function to safely clean values
                            def clean_value(value, field_type=str):
                                if pd.isna(value):
                                    return None
                                try:
                                    if field_type == str:
                                        return str(value).strip()
                                    return field_type(value)
                                except (ValueError, AttributeError):
                                    return None
                            
                            faculty_data = {
                                'user_id': user_id,
                                'department': department,
                                'first_name': clean_value(row.get('first_name', user.first_name)),
                                'last_name': clean_value(row.get('last_name', user.last_name)),
                                'email': clean_value(row.get('email', user.email)),
                                'phone_number': clean_value(row.get('phone_number')),
                                'date_of_birth': clean_value(row.get('date_of_birth')),
                                'gender': clean_value(row.get('gender')) if clean_value(row.get('gender')) in ['Male', 'Female', 'Other'] else None,
                                'nationality': clean_value(row.get('nationality')),
                                'blood_group': clean_value(row.get('blood_group')),
                                'address': clean_value(row.get('address')),
                                'employee_position': clean_value(row.get('employee_position')) if clean_value(row.get('employee_position')) in ['Hod', 'Associate Professor', 'Assistant Professor'] else None,
                                'emergency_contact': clean_value(row.get('emergency_contact')),
                                'emergency_name': clean_value(row.get('emergency_name')),
                                'emergency_relation': clean_value(row.get('emergency_relation')),
                            }
                            
                            Faculty.objects.update_or_create(
                                user_id=user_id,
                                defaults=faculty_data
                            )
                            success_count += 1
                            
                        except User.DoesNotExist:
                            errors.append(f"User with ID {row.get('user_id', '')} does not exist")
                        except Department.DoesNotExist:
                            errors.append(f"Department {row.get('department', '')} does not exist")
                        except ValueError as ve:
                            errors.append(f"Validation error for user ID {row.get('user_id', '')}: {str(ve)}")
                        except Exception as e:
                            errors.append(f"Error creating faculty: {str(e)}")

                if success_count > 0:
                    messages.success(request, f'Successfully processed {success_count} faculty records')
                if errors:
                    messages.warning(request, f'Completed with {len(errors)} errors')
                    for error in errors[:10]:
                        messages.error(request, error)
                        
                return redirect('bulk_upload_faculty')  # Changed from 'list_faculty'
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
        else:
            messages.error(request, "Invalid form submission")
    
    else:
        form = BulkFacultyUploadForm()
    
    return render(request, 'admin/bulk_upload_faculty.html', {'form': form})

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from .models import Faculty, Department
from .forms import FacultyForm

@login_required
@user_passes_test(is_admin)
def list_faculty(request):
    # Filter by department if specified
    department_id = request.GET.get('department')
    if department_id:
        faculties = Faculty.objects.filter(department__department_id=department_id)
    else:
        faculties = Faculty.objects.all()
    
    departments = Department.objects.all()
    
    return render(request, 'admin/list_faculty.html', {
        'faculties': faculties,
        'departments': departments
    })

@login_required
@user_passes_test(is_admin)
def edit_faculty(request, faculty_id):
    faculty = get_object_or_404(Faculty, faculty_id=faculty_id)
    departments = Department.objects.all()
    
    if request.method == 'POST':
        form = FacultyForm(request.POST, request.FILES, instance=faculty)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'message': 'Faculty updated successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json(),
                'form_html': render_to_string('admin/edit_faculty_modal.html', {
                    'form': form,
                    'faculty': faculty,
                    'departments': departments
                }, request=request)
            }, status=400)
    
    # GET request
    form = FacultyForm(instance=faculty)
    return render(request, 'admin/edit_faculty_modal.html', {
        'form': form,
        'faculty': faculty,
        'departments': departments
    })

@login_required
@user_passes_test(is_admin)
def delete_faculty(request, faculty_id):
    faculty = get_object_or_404(Faculty, faculty_id=faculty_id)
    
    if request.method == 'POST':
        faculty.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('list_faculty')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    return redirect('list_faculty')

#students
@login_required
@user_passes_test(is_admin)
def download_student_template(request):
    student_group = Group.objects.get(name='Students')  #  Assuming 'Students' is the group name
    existing_students = Student.objects.all().values_list('user__username', flat=True)
    users = User.objects.filter(groups=student_group).exclude(username__in=existing_students)
    
    data = {
        'user_id': [user.id for user in users],
        'username': [user.username for user in users],
        'first_name': [user.first_name for user in users],
        'last_name': [user.last_name for user in users],    
        'email': [user.email for user in users],
    }
    df = pd.DataFrame(data)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student.csv"'
    df.to_csv(response, index=False)
    return response

@login_required
@user_passes_test(is_admin)
def download_student_format(request):
    # Path to the template file
    file_path = os.path.join(settings.BASE_DIR, 'template', 'student_template.csv')
    
    # Debugging: Print the file path
    print(f"Looking for file at: {file_path}")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return HttpResponse("Template file not found. Please contact the administrator.", status=404)
    
    # Open the file and serve it as a response
    with open(file_path, 'rb') as file:
        response = HttpResponse(file.read(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=student_template.csv'
        return response

@login_required
@user_passes_test(is_admin)
def bulk_upload_student(request):
    if request.method == 'POST':
        form = BulkStudentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            try:
                # Read the file
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:
                    messages.error(request, 'Unsupported file format. Please upload a CSV or Excel file.')
                    return redirect('bulk_upload_student')

                success_count = 0
                errors = []
                
                with transaction.atomic():
                    for _, row in df.iterrows():
                        try:
                            # Validate required fields
                            if not row.get('user_id'):
                                raise ValueError("User ID is required")
                            if not row.get('department'):
                                raise ValueError("Department is required")
                            if not row.get('current_semester'):
                                raise ValueError("Current semester is required")
                            
                            user_id = int(row['user_id'])
                            department = Department.objects.get(department_name=row['department'])
                            user = User.objects.get(id=user_id)
                            scheme= Scheme.objects.get(scheme_name=row['scheme'])
                            scheme_id = scheme.scheme_id if scheme else None
                            
                            # Helper function to safely clean values
                            def clean_value(value, field_type=str):
                                if pd.isna(value):
                                    return None
                                try:
                                    if field_type == str:
                                        return str(value).strip()
                                    return field_type(value)
                                except (ValueError, AttributeError):
                                    return None
                            
                            student_data = {
                                'user_id': user_id,
                                'department': department,
                                'scheme': scheme,
                                'first_name': clean_value(row.get('first_name', user.first_name)),
                                'last_name': clean_value(row.get('last_name', user.last_name)),
                                'email': clean_value(row.get('email', user.email)),
                                'phone_number': clean_value(row.get('phone_number')),
                                'date_of_birth': clean_value(row.get('date_of_birth')),
                                'gender': clean_value(row.get('gender')) if clean_value(row.get('gender')) in ['Male', 'Female', 'Other'] else None,
                                'nationality': clean_value(row.get('nationality')),
                                'blood_group': clean_value(row.get('blood_group')),
                                'address': clean_value(row.get('address')),
                                'guardian_name': clean_value(row.get('guardian_name')),
                                'guardian_contact': clean_value(row.get('guardian_contact')),
                                'guardian_address': clean_value(row.get('guardian_address')),  # Changed from relationship_with_guardian
                                'mother_name': clean_value(row.get('mother_name')),
                                'father_name': clean_value(row.get('father_name')),
                                'father_contact': clean_value(row.get('father_contact')),
                                'mother_contact': clean_value(row.get('mother_contact')),
                                'parent_address': clean_value(row.get('parent_address')),
                                'current_semester': clean_value(row.get('current_semester'), int),
                                'admission_number': clean_value(row.get('admission_number')),
                            }
                            
                            Student.objects.update_or_create(
                                user_id=user_id,
                                defaults=student_data
                            )
                            success_count += 1
                            
                        except User.DoesNotExist:
                            errors.append(f"User with ID {row.get('user_id', '')} does not exist")
                        except Department.DoesNotExist:
                            errors.append(f"Department {row.get('department', '')} does not exist")
                        except ValueError as ve:
                            errors.append(f"Validation error for user ID {row.get('user_id', '')}: {str(ve)}")
                        except Exception as e:
                            errors.append(f"Error creating student: {str(e)}")

                if success_count > 0:
                    messages.success(request, f'Successfully processed {success_count} student records')
                if errors:
                    messages.warning(request, f'Completed with {len(errors)} errors')
                    for error in errors[:10]:
                        messages.error(request, error)
                        
                return redirect('bulk_upload_student')
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
        else:
            messages.error(request, "Invalid form submission")
    
    else:
        form = BulkStudentUploadForm()
    
    return render(request, 'admin/bulk_upload_student.html', {'form': form})

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from .models import Student, Department, Scheme
from .forms import StudentForm
from django.db.models import Q
@login_required
@user_passes_test(is_admin)

def list_students(request):
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
    return render(request, 'admin/list_students.html', context)

@login_required
@user_passes_test(is_admin)
def edit_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    departments = Department.objects.all()
    schemes = Scheme.objects.all()
    
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'message': 'Student updated successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json(),
                'form_html': render_to_string('admin/edit_student_modal.html', {
                    'form': form,
                    'student': student,
                    'departments': departments,
                    'schemes': schemes
                }, request=request)
            }, status=400)
    
    # GET request
    form = StudentForm(instance=student)
    return render(request, 'admin/edit_student_modal.html', {
        'form': form,
        'student': student,
        'departments': departments,
        'schemes': schemes
    })

@login_required
@user_passes_test(is_admin)
def delete_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    
    if request.method == 'POST':
        student.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('list_students')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    return redirect('list_students')

#Scheme Management
@login_required
@user_passes_test(is_admin)
def manage_schemes(request):
    schemes = Scheme.objects.all().order_by('-is_active', 'scheme_name')
    if request.method == 'POST' and 'add_scheme' in request.POST:
        form = SchemeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Scheme added successfully!')
            return redirect('manage_schemes')
    else:
        form = SchemeForm()
    return render(request, 'admin/scheme_management.html', {'form': form, 'schemes': schemes})

@login_required
@user_passes_test(is_admin)
def update_scheme(request, scheme_id):
    scheme = get_object_or_404(Scheme, pk=scheme_id)
    if request.method == 'POST':
        form = SchemeForm(request.POST, instance=scheme)
        if form.is_valid():
            form.save()
            messages.success(request, 'Scheme updated successfully!')
    return redirect('manage_schemes')

@login_required
@user_passes_test(is_admin)
@require_POST
def toggle_scheme_status(request, scheme_id):
    scheme = get_object_or_404(Scheme, pk=scheme_id)
    scheme.is_active = not scheme.is_active
    scheme.save()
    status = "activated" if scheme.is_active else "deactivated"
    messages.success(request, f"Scheme '{scheme.scheme_name}' {status} successfully")
    return redirect('manage_schemes')

@login_required
@user_passes_test(is_admin)
@require_POST
def delete_scheme(request, scheme_id):
    scheme = get_object_or_404(Scheme, pk=scheme_id)
    try:
        scheme.delete()
        messages.success(request, 'Scheme deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting scheme: {str(e)}')
    return redirect('manage_schemes')

# Enrollment Management
@login_required
@user_passes_test(is_admin)
def manage_enrollments(request):
    enrollments = Enrollment.objects.all().order_by('-enrollment_date')
    all_students = Student.objects.all().order_by('user__first_name')
    all_courses = Course.objects.all().order_by('course_name')
    all_faculty = Faculty.objects.all().order_by('user__first_name')
    all_schemes = Scheme.objects.all().order_by('scheme_name')
    all_departments = Department.objects.all().order_by('department_name')
    semester_choices = range(1, 9)
    
    filtered_students = None
    selected_scheme = None
    selected_department = None
    selected_semester = None
    
    if request.method == 'POST':
        if 'filter_students' in request.POST:
            # Handle student filtering
            selected_scheme = request.POST.get('filter_scheme')
            selected_department = request.POST.get('filter_department')
            selected_semester = request.POST.get('filter_semester')
            
            filtered_students = Student.objects.all()
            
            if selected_scheme:
                filtered_students = filtered_students.filter(scheme_id=selected_scheme)
            if selected_department:
                filtered_students = filtered_students.filter(department_id=selected_department)
            if selected_semester:
                filtered_students = filtered_students.filter(current_semester=selected_semester)
                
        elif 'bulk_enroll' in request.POST:
            # Handle bulk enrollment
            scheme_id = request.POST.get('bulk_scheme')
            semester = request.POST.get('bulk_semester')
            course_id = request.POST.get('bulk_course')
            faculty_id = request.POST.get('bulk_faculty')
            student_ids = request.POST.getlist('bulk_students')
            enrollment_date = request.POST.get('bulk_enrollment_date')
            
            try:
                 # Get the course to access its semester
                course = Course.objects.get(pk=course_id)
                semester = course.semester
                
                with transaction.atomic():
                    for student_id in student_ids:
                        Enrollment.objects.create(
                            student_id=student_id,
                            course_id=course_id,
                            faculty_id=faculty_id,
                            semester=semester,
                            scheme_id=scheme_id,
                            enrollment_date=enrollment_date
                        )
                messages.success(request, f'Successfully enrolled {len(student_ids)} students!')
            except Exception as e:
                messages.error(request, f'Error in bulk enrollment: {str(e)}')
                
    return render(request, 'admin/enrollment_management.html', {
        'enrollments': enrollments,
        'all_students': all_students,
        'filtered_students': filtered_students,
        'all_courses': all_courses,
        'all_faculty': all_faculty,
        'all_schemes': all_schemes,
        'all_departments': all_departments,
        'semester_choices': semester_choices,
        'selected_scheme': selected_scheme,
        'selected_department': selected_department,
        'selected_semester': selected_semester,
    })

@login_required
@user_passes_test(is_admin)
def view_course_enrollments(request):
    # Group enrollments by course, semester, and scheme
    course_groups = Enrollment.objects.values(
        'course__course_id', 
        'course__course_name',
        'semester',
        'scheme__scheme_id',
        'scheme__scheme_name',
        'faculty__user__first_name',
        'faculty__user__last_name'
    ).annotate(
        student_count=Count('enrollment_id')  # Changed from 'id' to 'enrollment_id'
    ).order_by('course__course_name', 'semester', 'scheme__scheme_name')
    
    return render(request, 'admin/course_enrollments.html', {
        'course_groups': course_groups,
    })


@login_required
@user_passes_test(is_admin)
def enrollment_detail(request, course_id, semester, scheme_id):
    course = get_object_or_404(Course, course_id=course_id)
    scheme = get_object_or_404(Scheme, scheme_id=scheme_id)
    
    # Get all enrollments for this course group
    enrollments = Enrollment.objects.filter(
        course=course,
        semester=semester,
        scheme=scheme
    ).select_related('student', 'faculty', 'student__user', 'faculty__user','student__department')
    
    # Get distinct departments from current enrollments
    enrolled_departments = Department.objects.filter(
        student__enrollment__in=enrollments
    ).distinct()

    # Get all students not enrolled in this course
    enrolled_student_ids = enrollments.values_list('student__student_id', flat=True)
    available_students = Student.objects.filter(
        department__in=enrolled_departments  
    ).exclude(
        student_id__in=enrolled_student_ids
    ).order_by('user__first_name').select_related('user', 'department').only(
    'usn', 'user__first_name', 'user__last_name', 'department__department_name'
    )
    
    # Get all faculty for the dropdown
    all_faculty = Faculty.objects.all().order_by('user__first_name').select_related('user', 'department')
    
    if request.method == 'POST':
        if 'add_student' in request.POST:
            student_id = request.POST.get('student_to_add')
            faculty_id = enrollments.first().faculty_id if enrollments.exists() else None
            
            try:
                student = Student.objects.get(student_id=student_id)
                with transaction.atomic():
                    Enrollment.objects.create(
                        student=student,
                        course=course,
                        faculty_id=faculty_id,
                        semester=semester,
                        scheme=scheme,
                        enrollment_date=timezone.now().date()  # Fixed timezone usage
                    )
                messages.success(request, f'Successfully enrolled {student.user.get_full_name()}!')
                return redirect('enrollment_detail', course_id=course_id, semester=semester, scheme_id=scheme_id)
            except Exception as e:
                messages.error(request, f'Error adding student: {str(e)}')
                
        elif 'update_faculty' in request.POST:
            faculty_id = request.POST.get('faculty')
            try:
                faculty = Faculty.objects.get(faculty_id=faculty_id) if faculty_id else None
                enrollments.update(faculty=faculty)
                messages.success(request, 'Faculty updated successfully!')
                return redirect('enrollment_detail', course_id=course_id, semester=semester, scheme_id=scheme_id)
            except Exception as e:
                messages.error(request, f'Error updating faculty: {str(e)}')
            
        elif 'remove_student' in request.POST:
            student_id = request.POST.get('student_to_remove')
            try:
                student = Student.objects.get(student_id=student_id)
                enrollments.filter(student=student).delete()
                messages.success(request, f'Successfully removed {student.user.get_full_name()}!')
                return redirect('enrollment_detail', course_id=course_id, semester=semester, scheme_id=scheme_id)
            except Exception as e:
                messages.error(request, f'Error removing student: {str(e)}')
    
    return render(request, 'admin/enrollment_group_detail.html', {
        'course': course,
        'semester': semester,
        'scheme': scheme,
        'enrollments': enrollments,
        'available_students': available_students,
        'all_faculty': all_faculty,
        'enrolled_departments': enrolled_departments,
    })

@login_required
@user_passes_test(is_admin)
def update_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Enrollment updated successfully!')
            except Exception as e:
                messages.error(request, f'Error updating enrollment: {str(e)}')
    return redirect('manage_enrollments')

@login_required
@user_passes_test(is_admin)
def delete_enrollment(request, course_id, semester, scheme_id):
    # Get all enrollments for this course-semester-scheme combination
    enrollments = Enrollment.objects.filter(
        course_id=course_id,
        semester=semester,
        scheme_id=scheme_id
    )
    
    if request.method == 'POST':
        # Delete all these enrollments
        count = enrollments.count()
        enrollments.delete()
        messages.success(request, f'Successfully deleted {count} enrollment(s) for this course group.')
        return redirect('view_course_enrollments')
    
    # For GET requests, you might want to show a confirmation page
    course = get_object_or_404(Course, pk=course_id)
    scheme = get_object_or_404(Scheme, pk=scheme_id)
    
    context = {
        'course': course,
        'semester': semester,
        'scheme': scheme,
        'enrollment_count': enrollments.count()
    }
    return redirect('view_course_enrollments')

#Course-Scheme Management
@login_required
@user_passes_test(is_admin)
def manage_courses_and_schemes(request):
    # Handle CSV import
    if request.method == 'POST' and 'import_csv' in request.POST:
        form = CourseCSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            scheme = form.cleaned_data['scheme']
            department = form.cleaned_data['department']
            csv_file = TextIOWrapper(request.FILES['csv_file'].file, encoding=request.encoding)
            
            try:
                reader = csv.DictReader(csv_file)
                created_count = 0
                updated_count = 0
                
                for row in reader:
                    # Create or update course
                    course, created = Course.objects.get_or_create(
                        course_name=row['course_name'],
                        course_code=row['course_code'],
                        defaults={
                            'credits': row.get('credits', 0),
                            'semester': row.get('semester', 1),
                            'internal_count': row.get('internal_count', 3),
                            'assignment_count': row.get('assignment_count', 2),
                            'quiz_count': row.get('quiz_count', 0),
                            'project_count': row.get('project_count', 0),
                            'internal_total_marks': row.get('internal_total_marks', 60),
                            'assignment_total_marks': row.get('assignment_total_marks', 20),
                            'quiz_total_marks': row.get('quiz_total_marks', 20),
                            'project_total_marks': row.get('project_total_marks', 0),
                        }
                    )
                    
                    # Add department to course
                    course.department.add(department)
                    
                    # Create course-scheme mapping
                    CourseScheme.objects.update_or_create(
                        course=course,
                        scheme=scheme,
                        scheme_year=row.get('scheme_year', 2023),
                        defaults={
                            'internal_weightage': row.get('internal_weightage', 50),
                            'external_weightage': row.get('external_weightage', 50),
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                messages.success(request, f'Successfully imported {created_count} new courses and updated {updated_count} existing ones.')
                return redirect('manage_courses_and_schemes')
            
            except Exception as e:
                messages.error(request, f'Error importing CSV: {str(e)}')
    
    # Handle course creation
    elif request.method == 'POST' and 'add_course' in request.POST:
        form = CourseForm(request.POST)
        if form.is_valid():
            try:
                course = form.save()
                departments = form.cleaned_data['departments']
                course.department.set(departments)
                messages.success(request, 'Course added successfully!')
                return redirect('manage_courses_and_schemes')
            except Exception as e:
                messages.error(request, f'Error adding course: {str(e)}')
    
    
    # Handle course-scheme mapping
    elif request.method == 'POST' and 'add_mapping' in request.POST:
        form = CourseSchemeForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Course-Scheme mapping added successfully!')
                return redirect('manage_courses_and_schemes')
            except Exception as e:
                messages.error(request, f'Error adding mapping: {str(e)}')
    
    else:
        form = CourseForm()
    
    # Prepare context for template
    courses = Course.objects.all().order_by('course_name')
    course_schemes = CourseScheme.objects.all().order_by('-scheme_year', 'course__course_name')
    all_departments = Department.objects.all()
    all_schemes = Scheme.objects.all()
    import_form = CourseCSVImportForm()
    
    semester_choices = [
        (1, 'Semester 1'), (2, 'Semester 2'), 
        (3, 'Semester 3'), (4, 'Semester 4'),
        (5, 'Semester 5'), (6, 'Semester 6'),
        (7, 'Semester 7'), (8, 'Semester 8')
    ]
    
    return render(request, 'admin/course_management.html', {
        'courses': courses,
        'course_schemes': course_schemes,
        'all_departments': all_departments,
        'all_schemes': all_schemes,
        'semester_choices': semester_choices,
        'form': CourseForm(),
        'mapping_form': CourseSchemeForm(),
        'import_form': import_form
    })

@login_required
@user_passes_test(is_admin)
def export_courses_csv(request):
    if request.method == 'POST':
        scheme_id = request.POST.get('scheme')
        department_id = request.POST.get('department')
        
        try:
            scheme = Scheme.objects.get(pk=scheme_id)
            department = Department.objects.get(pk=department_id)
            
            # Get courses for this department and their scheme mappings
            courses = Course.objects.filter(department=department)
            course_schemes = CourseScheme.objects.filter(
                scheme=scheme,
                course__in=courses
            ).select_related('course')
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{scheme.scheme_name}_{department.department_name}_courses.csv"'
            
            writer = csv.writer(response)
            # Write header row
            writer.writerow([
                'course_code',
                'course_name', 'credits', 'semester', 'internal_count',
                'assignment_count', 'quiz_count', 'project_count',
                'internal_total_marks', 'assignment_total_marks',
                'quiz_total_marks', 'project_total_marks',
                'scheme_year', 'internal_weightage', 'external_weightage',
            ])
            
            # Write data rows
            for cs in course_schemes:
                course = cs.course
                writer.writerow([
                    course.course_code,  
                    course.course_name, course.credits, course.semester,
                    course.internal_count, course.assignment_count,
                    course.quiz_count, course.project_count,
                    course.internal_total_marks, course.assignment_total_marks,
                    course.quiz_total_marks, course.project_total_marks,
                    cs.scheme_year, cs.internal_weightage, cs.external_weightage
                ])
            
            return response
        
        except Exception as e:
            messages.error(request, f'Error exporting CSV: {str(e)}')
            return redirect('manage_courses_and_schemes')
    
    return redirect('manage_courses_and_schemes')

@login_required
@user_passes_test(is_admin)
def download_course_template(request):
    try:
        # Create the HttpResponse object with CSV header
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="course_import_template.csv"'},
        )
        
        writer = csv.writer(response)
        
        # Write CSV header
        writer.writerow([
            'course_code',
            'course_name', 
            'credits', 
            'semester', 
            'internal_count',
            'internal_total_marks',
            'assignment_count',
            'assignment_total_marks',
            'quiz_count',
            'quiz_total_marks',
            'project_count',
            'project_total_marks'
        ])
        
        return response
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error generating CSV template: {str(e)}")
        return HttpResponse("Error generating template", status=500)

@login_required
@user_passes_test(is_admin)
def update_scheme_mapping(request, mapping_id):
    course_scheme = get_object_or_404(CourseScheme, course_scheme_id=mapping_id)
    
    if request.method == 'POST':
        try:
            course_scheme.internal_weightage = float(request.POST.get('internal_weightage'))
            course_scheme.external_weightage = float(request.POST.get('external_weightage'))
            course_scheme.scheme_year = request.POST.get('scheme_year')
            
            # Validate weightage sum
            if course_scheme.internal_weightage + course_scheme.external_weightage != 100:
                messages.error(request, "Internal and external weightage must sum to 100")
                return redirect('manage_courses_and_schemes')
            
            course_scheme.save()
            messages.success(request, 'Scheme mapping updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating scheme mapping: {str(e)}')
        
        return redirect('manage_courses_and_schemes')
    
# Course Views
@login_required
@user_passes_test(is_admin)
def update_course(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    if request.method == 'POST':
        course.course_name = request.POST.get('course_name')
        course.credits = request.POST.get('credits')
        course.semester = request.POST.get('semester')
        course.internal_count = request.POST.get('internal_count')
        course.assignment_count = request.POST.get('assignment_count')
        course.quiz_count = request.POST.get('quiz_count')
        course.project_count = request.POST.get('project_count')
        course.internal_total_marks = request.POST.get('internal_total_marks')
        course.assignment_total_marks = request.POST.get('assignment_total_marks')
        course.quiz_total_marks = request.POST.get('quiz_total_marks')
        course.project_total_marks = request.POST.get('project_total_marks')
        course.course_code = request.POST.get('course_code')
        course.department.clear()
        departments = request.POST.getlist('departments')
        course.save()
        messages.success(request, 'Course updated successfully!')
    return redirect('manage_courses_and_schemes')

@login_required
@user_passes_test(is_admin)
@require_POST
def delete_course(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    try:
        course.delete()
        messages.success(request, 'Course deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting course: {str(e)}')
    return redirect('manage_courses_and_schemes')



#admin home
def admin_dashboard(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('/signin')
    
    # Count all departments
    dept_count = Department.objects.count()
    student_count = Student.objects.count()
    faculty_count = Faculty.objects.count()
    active_schemes_count = Scheme.objects.filter(is_active=True).count()

    # Get student counts by department
    departments = Department.objects.annotate(
        student_count=Count('student')
    ).values('department_name', 'student_count').order_by('department_name')
    
    # Get faculty counts by department
    departments_with_faculty = Department.objects.annotate(
        faculty_count=Count('faculty')
    ).order_by('department_name')

    # Prepare data for chart
    dept_names = [dept['department_name'] for dept in departments]
    student_counts = [dept['student_count'] for dept in departments]
    schemes = Scheme.objects.filter(is_active=True).order_by('scheme_name')

# Prepare data structure
    departments = Department.objects.all()
    chart_data = {
        'schemes': [scheme.scheme_name for scheme in schemes],
        'datasets': []
    }
    
    # Get student counts for each department by scheme
    colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b']  # Different colors for departments
    
    for i, department in enumerate(departments):
        counts = []
        for scheme in schemes:
            count = Student.objects.filter(
                department=department,
                scheme=scheme
            ).count()
            counts.append(count)
        
        chart_data['datasets'].append({
            'label': department.department_name,
            'data': counts,
            'borderColor': colors[i % len(colors)],
            'backgroundColor': colors[i % len(colors)] + '33',  # Add transparency
            'tension': 0.3
        })

    
    context = {
        'department_count': dept_count, 
        'student_count': student_count,
        'faculty_count': faculty_count,  
        'active_schemes_count': active_schemes_count,
        'dept_names': dept_names,
        'student_counts': student_counts,
        'chart_data': chart_data,
        'departments_with_faculty': departments_with_faculty, 
    }
    
    return render(request, 'admin/admin_home.html', context)

