from django.contrib.auth.models import User, Group
from django.contrib.auth import login, logout, authenticate, get_user_model,update_session_auth_hash
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import UserCreationForm
from .models import Student, Faculty, Department
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.http import JsonResponse
from .models import Event
import json
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers
from .forms import AdminProfileForm, CustomPasswordChangeForm, GroupCreationForm, UniversalPasswordChangeForm

# Dictionary to store reset tokens
reset_tokens = {}

# Home View
def home(request):
    if request.user.is_authenticated:
        # Redirect based on user role
        if request.user.is_superuser:  # Check if the user is a superuser
            return redirect('admin_home')
        elif request.user.groups.filter(name='Students').exists():
            return redirect('student_home')
        elif request.user.groups.filter(name='Faculty').exists():
            return redirect('faculty_home')
    
    # Check for "Remember Me" cookie
    username = request.COOKIES.get('username')
    if username:
        user = User.objects.filter(username=username).first()
        if user:
            login(request, user)
            if user.is_superuser:  # Check if the user is a superuser
                return redirect('admin_home')
            elif user.groups.filter(name='Students').exists():
                return redirect('student_home')
            else:
                return redirect('faculty_home')
    
    return redirect('/signin')

# Signin View
def signin(request):
    if request.user.is_authenticated:
        return redirect('/home')
    
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        remember_me = request.POST.get('remember_me', False)

        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)

            # Redirect based on user role
            if user.is_superuser:  # Check if the user is a superuser
                response = redirect('admin_home')
            elif user.groups.filter(name='Students').exists():
                response = redirect('student_home')
            elif user.groups.filter(name='Faculty').exists():
                response = redirect('faculty_home')
            else:
                messages.error(request, "User does not belong to any group.")
                return redirect('/signin')

            # Set cookie if "Remember Me" is checked
            if remember_me:
                response.set_cookie('username', username, max_age=1209600)  # 2 weeks
            else:
                response.delete_cookie('username')  # Delete the cookie if "Remember Me" is not checked

            return response  # Return the response object
        else:
            messages.error(request, "Invalid username or password")
            return redirect('/signin')

    return render(request, "login.html")

# Signout View
def signout(request):
    logout(request)
    response = redirect('/signin')
    response.delete_cookie('username')  # Delete the "Remember Me" cookie
    return response

def admin_home(request):
    if not request.user.is_authenticated or not request.user.is_superuser:  # Check if the user is a superuser
        return redirect('/signin')
    return render(request, "admin/admin_home.html")

# Student Home View
def student_home(request):
    if not request.user.is_authenticated or not request.user.groups.filter(name='Students').exists():
        return redirect('/signin')
    return render(request, "student/student_home.html")

# Faculty Home View
def faculty_home(request):
    if not request.user.is_authenticated or not request.user.groups.filter(name='Faculty').exists():
        return redirect('/signin')
    return render(request, "faculty/faculty_home.html")

# Forgot Password View
reset_tokens = {}  # Dictionary to store tokens temporarily

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)  # Check if email exists in User model
            
        except User.DoesNotExist:
            student = Student.objects.filter(user__email=email).first()
            faculty = Faculty.objects.filter(user__email=email).first()

            if student:
                user = student.user  # Get Student user object
            elif faculty:
                user = faculty.user  # Get Faculty user object
            else:
                messages.error(request, "Email not found.")
                return render(request, "forgot_password.html")

        # Generate token
        token = get_random_string(50)
        reset_tokens[token] = user.username  # Store token with username
        reset_link = f"http://127.0.0.1:8000/reset-password/{token}/"

        # Send reset link to the user's email
        send_mail(
            "Password Reset Request",
            f"Click the link below to reset your password:\n{reset_link}",
            "noreply@yourdomain.com",
            [user.email],  # Send to fetched email
            fail_silently=False,
        )

        messages.success(request, "A password reset link has been sent to your email.")
        return redirect('signin')

    return render(request, "forgot_password.html")

# Reset Password View
def reset_password(request, token):
    if token not in reset_tokens:
        messages.error(request, "Invalid or expired token.")
        return redirect('signin')

    if request.method == "POST":
        password = request.POST.get('password')
        conf_password = request.POST.get('confirmpassword')

        if password == conf_password:
            username = reset_tokens.pop(token)  # Get username from token
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            messages.success(request, "Password reset successful! You can now login.")
            return redirect('signin')
        else:
            messages.error(request, "Passwords do not match.")
    
    return render(request, "reset_password.html", {"token": token})

#Custom  group creation views.py
@login_required
@permission_required('auth.add_group', raise_exception=True)
def create_group(request):
    if request.method == 'POST':
        group_type = request.POST.get('group_type')
        if group_type in ['students', 'faculty']:
            group_name = "Students" if group_type == 'students' else "Faculty"
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                messages.success(request, f'"{group_name}" group created successfully!')
            else:
                messages.info(request, f'"{group_name}" group already exists')
            return redirect('create_group')
    
    # Get ALL groups (not just the user's groups)
    all_groups = Group.objects.all()
    return render(request, 'admin/create_group.html', {'groups': all_groups})

# Change Admin Password View
@login_required
@user_passes_test(lambda u: u.is_superuser)
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep user logged in
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('change_password')  # Redirect to admin dashboard
    else:
        form = CustomPasswordChangeForm(user=request.user)
    
    return render(request, 'admin/change_password.html', {'form': form})

#student and faculty password change view
@login_required
def student_change_password(request):
    if not hasattr(request.user, 'student'):
        return redirect('access_denied')
    
    if request.method == 'POST':
        form = UniversalPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password updated successfully!')
            return redirect('student_change_password')
    else:
        form = UniversalPasswordChangeForm(user=request.user)
    
    return render(request, 'accounts/student_change_password.html', {
        'form': form,
        'user': request.user
    })

@login_required
def faculty_change_password(request):
    if not hasattr(request.user, 'faculty'):
        return redirect('access_denied')
    
    if request.method == 'POST':
        form = UniversalPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password updated successfully!')
            return redirect('faculty_home')
    else:
        form = UniversalPasswordChangeForm(user=request.user)
    
    return render(request, 'accounts/faculty_change_password.html', {
        'form': form,
        'user': request.user
    })

#Admin Profile Edit View
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_admin_profile(request):
    if request.method == 'POST':
        form = AdminProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('edit_admin_profile')
    else:
        form = AdminProfileForm(instance=request.user)
    
    return render(request, 'admin/edit_admin_profile.html', {'form': form})

#Event Calendar
def is_admin(user):
    return user.is_staff or user.is_superuser

def student_required(view_func):
    decorated_view = login_required(
        user_passes_test(
            lambda u: u.groups.filter(name='Students').exists(),
            login_url='/signin'
        )(view_func)
    )
    return decorated_view

@login_required
@user_passes_test(is_admin)
def admin_calendar(request):
    """View for admin calendar interface"""
    return render(request, 'admin/admin_calendar.html')

@student_required
def student_calendar(request):
    """View for student calendar interface"""
    return render(request, 'student/student_calendar.html')

# API endpoints for AJAX requests
@login_required
def get_events(request):
    """API to get events"""
    events = Event.objects.all()
    events_json = serializers.serialize('json', events)
    return JsonResponse(events_json, safe=False)


@login_required
@user_passes_test(is_admin)
@csrf_exempt
def create_event(request):
    """API to create new event (admin only)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            event = Event(
                title=data['title'],
                description=data['description'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                event_type=data['event_type'],
                location=data['location'],
                created_by=request.user
            )
            event.save()
            
            return JsonResponse({
                'success': True, 
                'event_id': event.event_id
            })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=400)
    return JsonResponse({'success': False}, status=400)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
def update_event(request, event_id):
    """API to update event (admin only)"""
    if request.method == 'POST':
        try:
            event = Event.objects.get(event_id=event_id)
            data = json.loads(request.body)
            
            # Update basic fields
            event.title = data.get('title', event.title)
            event.description = data.get('description', event.description)
            event.start_date = data.get('start_date', event.start_date)
            event.end_date = data.get('end_date', event.end_date)
            event.event_type = data.get('event_type', event.event_type)
            event.location = data.get('location', event.location)
            event.save()
            
            return JsonResponse({
                'success': True,
                'event_id': event.event_id
            })
        except Event.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Event not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=400)
    return JsonResponse({'success': False}, status=400)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
def delete_event(request, event_id):
    """API to delete event (admin only)"""
    if request.method == 'POST':
        try:
            event = Event.objects.get(event_id=event_id)
            event.delete()
            return JsonResponse({'success': True})
        except Event.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Event not found'}, status=404)
    return JsonResponse({'success': False}, status=400)


def icon_view(request):
    return render(request, 'themify.html')
