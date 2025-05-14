from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin
from .models import Student, Faculty, Department, Course, Scheme, CourseScheme, Enrollment

# Unregister the default Group admin
admin.site.unregister(Group)

# Create a custom Group admin
class CustomGroupAdmin(admin.ModelAdmin):
    exclude = ('permissions',)  # Hide the permissions field

# Register the custom Group admin
admin.site.register(Group, CustomGroupAdmin)

# Unregister the default UserAdmin
admin.site.unregister(User)

# Register Department model
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('department_id', 'department_name')
    search_fields = ('department_name',)

# Register Student model
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'user', 'department', 'current_semester','email')
    search_fields = ('user_username', 'department_department_name')
    list_filter = ('department', 'current_semester')

# Register Faculty model
@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('faculty_id', 'user', 'department', 'email')
    search_fields = ('user_username', 'department_department_name')
    list_filter = ('department',)

